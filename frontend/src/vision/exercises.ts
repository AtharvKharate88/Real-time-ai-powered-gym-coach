import { RepTracker, SquatDetector, angle, roundEven, type Joint } from "./squat";
import type { Exercise } from "../services/api";

export function createDetector(exercise: Exercise, reps = 0, good = 0, warning = 0, incorrect = 0) {
  return exercise === "Squats" ? new SquatDetector(reps, good, warning, incorrect)
    : new MovementDetector(exercise, reps, good, warning, incorrect);
}

class MovementDetector extends RepTracker {
  constructor(private exercise: Exercise, reps: number, good: number, warning: number, incorrect: number) {
    super(reps, good, warning, incorrect);
  }

  process(j: Joint[]) {
    const lunge = this.exercise === "Lunges";
    const pushup = this.exercise === "Push-ups";
    const curl = this.exercise === "Biceps Curls (Dumbbell)";
    const indices = lunge ? [23,25,27] : pushup ? [11,13,15,23,27] : [11,13,15];
    const confidence = (side: number) => Math.min(...indices.map(i => j[i + side].visibility));
    const jointAngle = (i: number) => angle(j[i], j[i+2], j[i+4]);
    let side = confidence(0) >= confidence(1) ? 0 : 1;
    if (lunge && (confidence(0) > 0.7) === (confidence(1) > 0.7)) {
      side = jointAngle(23) <= jointAngle(24) ? 0 : 1;
    }
    const visible = confidence(side) > 0.7;
    const shoulder = j[11+side], hip = j[23+side], knee = j[25+side], ankle = j[27+side];
    const theta = jointAngle(indices[0]+side);
    const previous = this.reps;
    if (visible) {
      if (curl) this.updateStage(theta, 50, 160, "up", "down", "down");
      else this.updateStage(theta, lunge ? 100 : 90, 160, "down", "up", lunge || pushup ? "up" : "down");
    }
    const torsoVisible = [11,12,23,24].every(i => j[i].visibility > 0.7);
    const offsetX = (j[11].x+j[12].x-j[23].x-j[24].x)/2;
    const metrics: Record<string, string | number> = {};
    const issues: string[] = [];
    let incorrect = false;
    let feedbackValid = visible;
    if (lunge) {
      metrics.front_knee_angle = visible ? Math.trunc(theta) : "N/A";
      metrics.torso_angle = visible && shoulder.visibility > 0.7 ? Math.trunc(angle(shoulder, hip, knee)) : "N/A";
      metrics.balance_status = torsoVisible ? Math.abs(offsetX) <= 0.1 ? "BALANCED" : "OFF BALANCE" : "N/A";
      feedbackValid = visible && metrics.torso_angle !== "N/A" && torsoVisible;
      if (visible && metrics.balance_status === "OFF BALANCE") issues.push("Keep your balance and stance steady");
    } else {
      metrics.elbow_angle = visible ? Math.trunc(theta) : "N/A";
      if (pushup) {
        const body = angle(shoulder, hip, ankle);
        const deviation = hip.y - (shoulder.y + ankle.y)/2;
        metrics.body_alignment = !visible ? "N/A" : body > 160 ? "Straight" : body > 140 ? "Slight Bend" : "Poor Form";
        metrics.hip_status = !visible ? "N/A" : Math.abs(deviation) <= 0.08 ? "LEVEL" : deviation > 0 ? "SAGGING" : "PIKED UP";
        if (metrics.body_alignment === "Slight Bend") issues.push("Keep your body aligned");
        if (metrics.body_alignment === "Poor Form") { issues.push("Keep your body in a straight line"); incorrect = true; }
        if (visible && metrics.hip_status !== "LEVEL") { issues.push("Keep your hips level"); incorrect = true; }
      } else if (curl) {
        const offsetY = (j[11].y+j[12].y-j[23].y-j[24].y)/2;
        const tilt = Math.atan2(Math.abs(offsetX),Math.abs(offsetY))*180/Math.PI;
        metrics.shoulder_status = !visible ? "N/A" : Math.abs(j[13+side].x-shoulder.x) <= 0.06 ? "STABLE" : "ELBOW DRIFTING";
        metrics.swing_status = !torsoVisible ? "N/A" : tilt <= 15 ? "NO SWING" : "SWINGING";
        feedbackValid = visible && torsoVisible;
        if (visible && metrics.shoulder_status === "ELBOW DRIFTING") issues.push("Keep your elbow close to your side");
        if (visible && metrics.swing_status === "SWINGING") issues.push("Avoid swinging your torso");
      } else {
        const backVisible = [shoulder,hip,knee].every(p => p.visibility > 0.7);
        const back = angle(shoulder,hip,knee);
        metrics.extension_status = !visible ? "N/A" : theta >= 160 ? "FULL EXTENSION" : theta >= 130 ? "NEARLY EXTENDED" : theta >= 90 ? "PRESSING" : "START POSITION";
        metrics.back_arch_status = !backVisible ? "N/A" : back >= 160 ? "Neutral" : back >= 140 ? "Slight Arch" : "Excessive Arch";
        feedbackValid = visible && backVisible;
        if (visible && metrics.back_arch_status === "Slight Arch") issues.push("Brace your core to reduce back arch");
        if (visible && metrics.back_arch_status === "Excessive Arch") { issues.push("Avoid arching your lower back"); incorrect = true; }
      }
    }
    const status = issues.length ? incorrect ? "incorrect" : "warning" : feedbackValid ? "good" : "waiting";
    this.record(status);
    return { ...metrics, reps: this.reps, landmarks_visible: visible, exercise_stage: this.stage ?? "ready",
      rep_completed: this.reps !== previous, movement_valid: visible, pose_confidence: roundEven(confidence(side)*100),
      form_status: status, feedback_priority: status === "incorrect" ? "high" : status === "warning" ? "medium" : status === "good" ? "positive" : "waiting",
      form_issue: issues.join("; "), form_score: this.score() };
  }
}

