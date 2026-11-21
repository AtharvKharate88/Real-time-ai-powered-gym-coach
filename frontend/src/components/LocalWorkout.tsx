import { useEffect, useRef, useState } from "react";
import { sendCheckpoint, draftKey, ApiError, type AuthUser, type WorkoutDraft, type Progress, type Exercise } from "../services/api";
import { createDetector } from "../vision/exercises";
import { summarize, type Sample } from "../vision/benchmark";
import { type Joint } from "../vision/squat";
import { usePoseCamera } from "../vision/usePoseCamera";
import WorkoutFlowNav from "./WorkoutFlowNav";

type Phase = "ready" | "running" | "paused" | "pending" | "saved" | "empty";
function drawPose(canvas: HTMLCanvasElement, video: HTMLVideoElement, joints?: Joint[]) {
  if (!video.videoWidth || !video.videoHeight) return;
  if (canvas.width !== video.videoWidth || canvas.height !== video.videoHeight) {
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
  }
  const ctx = canvas.getContext("2d");
  if (!ctx) return;
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  if (!joints) return;
  const visible = (index: number) => joints[index] && joints[index].visibility >= 0.55;
  const bones = [[11,13],[13,15],[12,14],[14,16],[11,12],[11,23],[12,24],[23,24],[23,25],[25,27],[24,26],[26,28]];
  const lineWidth = Math.max(3, canvas.width / 180);
  ctx.lineCap = "round";
  ctx.lineJoin = "round";
  // A dark casing keeps the tracking line readable over both clothes and bright backgrounds.
  ctx.beginPath();
  for (const [a,b] of bones) {
    if (!visible(a) || !visible(b)) continue;
    ctx.moveTo(joints[a].x * canvas.width, joints[a].y * canvas.height);
    ctx.lineTo(joints[b].x * canvas.width, joints[b].y * canvas.height);
  }
  ctx.strokeStyle = "rgba(2, 6, 12, .9)";
  ctx.lineWidth = lineWidth * 2.8;
  ctx.stroke();
  ctx.strokeStyle = "#b6ff3b";
  ctx.lineWidth = lineWidth;
  ctx.stroke();
  for (let i = 11; i <= 28; i++) {
    if (!visible(i)) continue;
    const x = joints[i].x * canvas.width;
    const y = joints[i].y * canvas.height;
    const wrist = i === 15 || i === 16;
    const radius = Math.max(wrist ? 7 : 4, canvas.width / (wrist ? 95 : 170));
    ctx.beginPath(); ctx.arc(x, y, radius + lineWidth, 0, Math.PI * 2);
    ctx.fillStyle = "rgba(2, 6, 12, .92)"; ctx.fill();
    ctx.beginPath(); ctx.arc(x, y, radius, 0, Math.PI * 2);
    ctx.fillStyle = wrist ? "#fff" : "#b6ff3b"; ctx.fill();
    ctx.beginPath(); ctx.arc(x, y, Math.max(2, radius * .38), 0, Math.PI * 2);
    ctx.fillStyle = wrist ? "#8ce51b" : "#26330f"; ctx.fill();
  }
}

export default function LocalWorkout({ draft, exercise, user, stream, onBack, onHistory, onDashboard, onSignOut }: {
  draft: WorkoutDraft | null; exercise: Exercise; user: AuthUser; stream: MediaStream; onBack: () => void; onHistory: () => void;
  onDashboard: () => void; onSignOut: () => void;
}) {
  const initial = draft?.progress;
  const revision = useRef(initial?.revision ?? 0);
  const pendingFinal = useRef(initial?.finished ? initial : null);
  const [phase, setPhase] = useState<Phase>(initial ? initial.finished ? "pending" : "paused" : "ready");
  const state = useRef(phase);
  function transition(p: Phase) { state.current = p; setPhase(p); }
  const video = useRef<HTMLVideoElement>(null);
  const canvas = useRef<HTMLCanvasElement>(null);
  const id = useRef(draft?.id ?? "");
  const [detector] = useState(() => createDetector(exercise, initial?.reps, initial?.good_frames, initial?.warning_frames, initial?.incorrect_frames));
  const [sets, setSets] = useState(initial?.target_sets ?? 3);
  const [perSet, setPerSet] = useState(initial?.reps_per_set ?? 10);
  const [reps, setReps] = useState(initial?.reps ?? 0);
  const latestReps = useRef(reps);
  const elapsed = useRef((initial?.elapsed_seconds ?? 0) * 1000);
  const started = useRef<number | null>(null);
  const [seconds, setSeconds] = useState(initial?.elapsed_seconds ?? 0);
  const [feedback, setFeedback] = useState("");
  const [score, setScore] = useState(detector.score());
  const [saving, setSaving] = useState(false);
  const savingRef = useRef(false);
  const [error, setError] = useState("");
  const [voice, setVoice] = useState(() => {
    try { return localStorage.getItem("ai_gym_voice_coaching") !== "false"; } catch { return false; }
  });
  const lastCue = useRef({ text: "", when: 0 });
  const diagnostics = useRef(false);
  const recentFrames = useRef<Sample[]>([]);
  function clock() {
    return Math.min(86400, Math.floor((elapsed.current + (started.current === null ? 0 : performance.now() - started.current)) / 1000));
  }
  function freeze() {
    if (started.current !== null) elapsed.current += performance.now() - started.current;
    started.current = null;
    setSeconds(clock());
    detector.interruptMovement();
    window.speechSynthesis?.cancel();
  }
  function checkpoint(finished: boolean, sync = false): Progress {
    if (pendingFinal.current) return pendingFinal.current;
    const summary = { exercise, finished, revision: ++revision.current, incorrect_frames: detector.incorrectFrames, reps: latestReps.current, target_sets: sets, reps_per_set: perSet,
      elapsed_seconds: clock(), good_frames: detector.goodFrames, warning_frames: detector.warningFrames };
    if (finished) pendingFinal.current = summary;
    try { localStorage.setItem(draftKey(user.id,id.current), JSON.stringify({ id: id.current, progress: summary })); }
    catch { setError("This browser cannot keep a recovery copy. Keep this tab open until saving finishes."); }
    if (sync && !finished) {
      void sendCheckpoint(user.id,id.current,summary).catch(() => {
        if (state.current === "running" || state.current === "paused") setError("Server checkpoint pending. This device will retry on the next checkpoint or save.");
      });
    }
    return summary;
  }
  function pause() {
    if (state.current !== "running") return;
    freeze(); transition("paused"); checkpoint(false,true);
  }
  async function finish() {
    if (savingRef.current || ["saved","empty","ready"].includes(state.current)) return;
    freeze();
    stream.getTracks().forEach(track => track.stop());
    transition("pending"); setError("");
    const summary = checkpoint(true);
    savingRef.current = true; setSaving(true);
    try {
      await sendCheckpoint(user.id,id.current,summary);
      transition(summary.reps ? "saved" : "empty");
      try { localStorage.removeItem(draftKey(user.id,id.current)); } catch { /* The server acknowledged this workout. */ }
    } catch (e) { setError(e instanceof ApiError && e.statusCode === 409 ? "Another copy of this workout has newer progress. Return to camera setup to recover it." : "Your save has not been confirmed. Retry when the backend is available."); }
    finally { savingRef.current = false; setSaving(false); }
  }
  function start() {
    if (!stream.getVideoTracks().some(track => track.readyState === "live" && !track.muted)) {
      setError("Camera interrupted. Return to camera setup to reconnect."); return;
    }
    if (!id.current) id.current = crypto.randomUUID();
    setError(""); setFeedback("Finding your position…");
    started.current = performance.now(); transition("running"); checkpoint(false,true);
  }
  useEffect(() => {
    const el = video.current;
    if (el) el.srcObject = stream;
    return () => { if (el) el.srcObject = null; window.speechSynthesis?.cancel(); };
  }, [stream]);
  useEffect(() => {
    if (phase !== "running") return;
    const timer = window.setInterval(() => setSeconds(clock()), 500);
    const syncTimer = window.setInterval(() => { if (state.current === "running") checkpoint(false,true); },30000);
    const background = () => { if (document.hidden) pause(); };
    const track = stream.getVideoTracks()[0];
    document.addEventListener("visibilitychange", background);
    window.addEventListener("pagehide", pause);
    track?.addEventListener("ended", pause);
    track?.addEventListener("mute", pause);
    return () => {
      clearInterval(syncTimer); clearInterval(timer); document.removeEventListener("visibilitychange", background);
      window.removeEventListener("pagehide", pause);
      track?.removeEventListener("ended", pause); track?.removeEventListener("mute", pause);
    };
  }, [phase, stream]);
  usePoseCamera(video, phase === "running", pose => {
    if (state.current !== "running") return;
    if (canvas.current && video.current) drawPose(canvas.current, video.current, pose);
    if (!pose) { detector.interruptMovement(); setFeedback("Step back until your full body is visible."); return; }
    const m = detector.process(pose);
    if (!m.movement_valid) detector.interruptMovement();
    const cue = m.movement_valid ? m.form_issue : "Keep the working joints in view.";
    setFeedback(cue || (m.exercise_stage === "ready" ? "Ready to move" : m.exercise_stage));
    setScore(m.form_score);
    if (m.reps !== latestReps.current) { latestReps.current = m.reps; setReps(m.reps); checkpoint(false,m.reps % perSet === 0 && m.reps < sets*perSet); }
    if (m.reps >= sets * perSet) { void finish(); return; }
    if (voice && cue && window.speechSynthesis && !window.speechSynthesis.speaking) {
      const now = performance.now();
      if (now - lastCue.current.when > (cue === lastCue.current.text ? 16000 : 6000)) {
        window.speechSynthesis.speak(new SpeechSynthesisUtterance(cue)); lastCue.current = { text: cue, when: now };
      }
    }
  }, () => { pause(); setError("Local pose tracking could not run. Resume to retry, or finish this workout."); },
  (at,inference,media) => {
    if (!diagnostics.current) return;
    const sample: Sample = {at,inference,media,issue:false,visible:false};
    recentFrames.current.push(sample);
    if (recentFrames.current.length > 120) recentFrames.current.shift();
    requestAnimationFrame(() => { sample.paint = performance.now()-at; });
  }, undefined, "full");
  function leave(action: () => void) { if (!savingRef.current) { pause(); action(); } }
  const active = phase === "running" || phase === "paused";
  return <main className="workout-page">
    <WorkoutFlowNav user={user} step={3} onDashboard={() => leave(onDashboard)} onSignOut={() => leave(onSignOut)} />
    <section className="workout-panel">
      <h1>{exercise}</h1>
      <p>Full pose tracking runs on this device. The bright wrist markers show where arm tracking ends; individual fingers are not tracked. Progress is checkpointed during the workout.</p>
      <div className="workout-controls">
        <label>Sets <input type="number" min={1} max={50} value={sets} disabled={phase !== "ready"} onChange={e => setSets(Number(e.target.value))} /></label>
        <label>Reps per set <input type="number" min={1} max={50} value={perSet} disabled={phase !== "ready"} onChange={e => setPerSet(Number(e.target.value))} /></label>
        <label><input type="checkbox" checked={voice} onChange={e => { setVoice(e.target.checked); if (!e.target.checked) window.speechSynthesis?.cancel(); }} /> Spoken tips</label>
        {phase === "ready" || phase === "paused" ? <button className="btn-primary" disabled={![sets,perSet].every(n => Number.isInteger(n) && n >= 1 && n <= 50)} onClick={start}>{phase === "paused" ? "Resume" : "Start workout"}</button> : null}
        {phase === "running" && <button className="btn-ghost" onClick={pause}>Pause</button>}
        {(active || phase === "pending") && <button className="btn-ghost" disabled={saving} onClick={() => void finish()}>{saving ? "Saving…" : phase === "pending" ? "Retry save" : "Finish workout"}</button>}
      </div>
      <div className="workout-live-layout">
        <div className="local-squat-preview"><video ref={video} autoPlay muted playsInline aria-label="Live workout camera" /><canvas hidden={phase !== "running"} ref={canvas} aria-hidden="true" /></div>
        <div className="workout-kpis"><div><span>TIME</span><strong>{Math.floor(seconds / 60)}:{String(seconds % 60).padStart(2,"0")}</strong></div>
          <div><span>REPS</span><strong>{reps}</strong></div><div><span>SETS</span><strong>{Math.floor(reps / (perSet || 1))} / {sets}</strong></div>
          <div><span>FORM SCORE</span><strong>{score ?? "—"}</strong></div></div>
      </div>
      <p role="status">{phase === "saved" ? "Workout saved to history." : phase === "empty" ? "Workout ended with no recorded reps." : phase === "pending" ? "Workout is awaiting save." : phase === "paused" ? "Workout paused." : feedback}</p>
      {error && <p role="alert" className="workout-error">{error}</p>}
      <details onToggle={e=>{diagnostics.current=e.currentTarget.open;recentFrames.current=[];}}>
        <summary>Tracking performance</summary>
        {diagnostics.current && <p>{summarize(recentFrames.current).processedFps ?? "—"} processed FPS · {summarize(recentFrames.current).inferenceP95Ms ?? "—"} ms p95 inference</p>}
        <a href="?benchmark" target="_blank" rel="noreferrer">Open camera and recording benchmark</a>
      </details>
      {phase === "saved" && <button className="btn-primary" onClick={onHistory}>View workout history</button>}
      <button className="btn-ghost" disabled={saving} onClick={() => leave(onBack)}>Return to camera setup</button>
    </section>
  </main>;
}
