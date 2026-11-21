export interface Joint {
  x: number;
  y: number;
  visibility: number;
}

export function angle(a: Joint, b: Joint, c: Joint) {
  const ax = a.x - b.x, ay = a.y - b.y;
  const cx = c.x - b.x, cy = c.y - b.y;
  const magnitude = Math.sqrt(ax * ax + ay * ay) * Math.sqrt(cx * cx + cy * cy);
  if (!magnitude) return 0;
  return Math.acos(Math.max(-1, Math.min(1, (ax * cx + ay * cy) / magnitude))) * 180 / Math.PI;
}

export function roundEven(value: number) {
  const floor = Math.floor(value);
  return value - floor === 0.5 ? floor + floor % 2 : Math.round(value);
}

export class RepTracker {
  protected stage: "up" | "down" | null = null;
  private pending: "up" | "down" | null = null;
  private frames = 0;
  private filteredStageValue: number | null = null;
  private awaitingBaseline = true;
  private lockedSide: 0 | 1 | null = null;
  protected reps = 0;
  private totalScore = 0;
  private samples = 0;
  goodFrames = 0;
  warningFrames = 0;
  incorrectFrames = 0;

  constructor(reps = 0, good = 0, warnings = 0, incorrect = 0) {
    this.reps = reps;
    this.goodFrames = good;
    this.warningFrames = warnings;
    this.totalScore = 100 * good + 75 * warnings;
    this.incorrectFrames = incorrect;
    this.totalScore += 50 * incorrect;
    this.samples = good + warnings + incorrect;
  }

  score() { return this.samples >= 30 ? roundEven(this.totalScore / this.samples) : null; }

  interruptMovement() {
    this.stage = null;
    this.pending = null;
    this.frames = 0;
    this.filteredStageValue = null;
    this.awaitingBaseline = true;
  }

  protected selectStableSide(leftConfidence: number, rightConfidence: number, threshold = 0.7): 0 | 1 {
    if (this.lockedSide !== null) {
      const lockedConfidence = this.lockedSide === 0 ? leftConfidence : rightConfidence;
      if (lockedConfidence >= threshold * 0.8) return this.lockedSide;
    }

    const candidate: 0 | 1 = leftConfidence >= rightConfidence ? 0 : 1;
    const candidateConfidence = candidate === 0 ? leftConfidence : rightConfidence;
    if (candidateConfidence < threshold) return this.lockedSide ?? candidate;
    if (this.lockedSide !== null && candidate !== this.lockedSide) this.interruptMovement();
    this.lockedSide = candidate;
    return candidate;
  }

  protected updateStage(value: number, low: number, high: number, lowStage: "down" | "up",
    highStage: "down" | "up", countStage: "down" | "up") {
    this.filteredStageValue = this.filteredStageValue === null
      ? value
      : value * 0.7 + this.filteredStageValue * 0.3;
    const stableValue = this.filteredStageValue;
    const candidate = stableValue <= low ? lowStage : stableValue >= high ? highStage : null;
    if (!candidate || candidate === this.stage) {
      this.pending = null;
      this.frames = 0;
    } else {
      this.frames = this.pending === candidate ? this.frames + 1 : 1;
      this.pending = candidate;
      if (this.frames >= 2) {
        if (this.awaitingBaseline) {
          if (candidate === countStage) {
            this.stage = candidate;
            this.awaitingBaseline = false;
          }
        } else {
          if (this.stage !== null && candidate === countStage) this.reps++;
          this.stage = candidate;
        }
        this.frames = 0;
        this.pending = null;
      }
    }
  }

  protected record(status: string) {
    if (status === "waiting") return;
    if (status === "good") this.goodFrames++;
    else if (status === "warning") this.warningFrames++;
    else this.incorrectFrames++;
    this.samples++;
    this.totalScore += status === "good" ? 100 : status === "warning" ? 75 : 50;
  }
}

export class SquatDetector extends RepTracker {
  process(joints: Joint[]) {
    const confidence = (hip: number) => Math.min(...[hip, hip + 2, hip + 4].map(i => joints[i].visibility));
    const side = this.selectStableSide(confidence(23), confidence(24));
    const hip = side === 0 ? 23 : 24;
    const visible = confidence(hip) > 0.7;
    const knee = angle(joints[hip], joints[hip + 2], joints[hip + 4]);
    const back = visible && joints[hip - 12].visibility > 0.7
      ? Math.trunc(angle(joints[hip - 12], joints[hip], joints[hip + 2])) : null;
    const previous = this.reps;
    if (visible) this.updateStage(knee, 100, 160, "down", "up", "up");
    const depth = !visible ? "N/A" : this.stage === "down" ? (knee <= 100 ? "GOOD DEPTH" : "TOO HIGH")
      : this.stage === "up" ? "STANDING" : "N/A";
    const issues = [];
    if (depth === "TOO HIGH") issues.push("Increase squat depth");
    if (back !== null && back < 130) issues.push("Keep your torso more upright");
    const status = issues.length ? "warning" : back === null ? "waiting" : "good";
    this.record(status);
    return { reps: this.reps, knee_angle: visible ? Math.trunc(knee) : "N/A", back_angle: back ?? "N/A",
      depth_status: depth, landmarks_visible: visible, exercise_stage: this.stage ?? "ready",
      rep_completed: previous !== this.reps, movement_valid: visible, pose_confidence: roundEven(confidence(hip) * 100),
      form_status: status, feedback_priority: status === "warning" ? "medium" : status === "good" ? "positive" : "waiting",
      form_issue: issues.join("; "), form_score: this.score() };
  }
}
