import { useEffect, useRef, useState } from "react";
import type { AuthUser, Exercise, HistoryEntry } from "../services/api";
import { saveLocalWorkout } from "../services/api";
import { exerciseOptions } from "./exerciseOptions";
import WorkoutFlowNav from "./WorkoutFlowNav";

type Landmark = { x: number; y: number; z: number; visibility: number };
type Metrics = Record<string, number | string | boolean>;
type RepTracker = { stage: string | null; pending: string | null; pendingFrames: number; armed: boolean; reps: number };
type Props = { user: AuthUser; onBack: () => void; onDashboard: () => void; onHistory: () => void; onSignOut: () => void; initialExercise?: Exercise; preparedStream?: MediaStream };

const CONNECTIONS = [[11,12],[11,13],[13,15],[12,14],[14,16],[11,23],[12,24],[23,24],[23,25],[25,27],[24,26],[26,28],[27,31],[28,32]] as const;
const freshTracker = (): RepTracker => ({ stage: null, pending: null, pendingFrames: 0, armed: false, reps: 0 });
const point = (landmarks: Landmark[], index: number) => landmarks[index] ?? { x: 0, y: 0, z: 0, visibility: 0 };
const angle = (a: Landmark, b: Landmark, c: Landmark) => {
  const ax = a.x - b.x, ay = a.y - b.y, cx = c.x - b.x, cy = c.y - b.y;
  const denominator = Math.hypot(ax, ay) * Math.hypot(cx, cy);
  if (!denominator) return 0;
  return Math.acos(Math.max(-1, Math.min(1, (ax * cx + ay * cy) / denominator))) * 180 / Math.PI;
};
const visibility = (landmarks: Landmark[], indices: number[]) => Math.min(...indices.map((index) => point(landmarks, index).visibility));

function analyze(exercise: Exercise, landmarks: Landmark[], tracker: RepTracker): Metrics {
  let movementAngle = 0, low = 100, high = 160, countStage = "up", lowStage = "down", visible = false;
  let metrics: Metrics = {};
  let issue = "";
  if (exercise === "Squats" || exercise === "Lunges") {
    const sides = [[23,25,27,11],[24,26,28,12]];
    const side = sides.sort((a,b) => visibility(landmarks,[b[0],b[1],b[2]]) - visibility(landmarks,[a[0],a[1],a[2]]))[0];
    const [hip,knee,ankle,shoulder] = side;
    movementAngle = angle(point(landmarks,hip),point(landmarks,knee),point(landmarks,ankle));
    visible = visibility(landmarks,[hip,knee,ankle]) > .55;
    if (exercise === "Squats") {
      const backAngle = angle(point(landmarks,shoulder),point(landmarks,hip),point(landmarks,knee));
      metrics = { knee_angle: visible ? Math.round(movementAngle) : "N/A", back_angle: visible ? Math.round(backAngle) : "N/A", depth_status: !visible ? "N/A" : movementAngle <= 100 ? "GOOD DEPTH" : tracker.stage === "up" ? "STANDING" : "TOO HIGH", landmarks_visible: visible };
      if (visible && movementAngle > 100 && tracker.stage !== "up") issue = "Increase squat depth";
      if (visible && backAngle < 130) issue = "Keep your torso more upright";
    } else {
      const torsoAngle = angle(point(landmarks,shoulder),point(landmarks,hip),point(landmarks,knee));
      metrics = { front_knee_angle: visible ? Math.round(movementAngle) : "N/A", torso_angle: visible ? Math.round(torsoAngle) : "N/A", balance_status: "BALANCED", landmarks_visible: visible };
    }
  } else {
    const sides = [[11,13,15,23,27],[12,14,16,24,28]];
    const side = sides.sort((a,b) => visibility(landmarks,b) - visibility(landmarks,a))[0];
    const [shoulder,elbow,wrist,hip,ankle] = side;
    movementAngle = angle(point(landmarks,shoulder),point(landmarks,elbow),point(landmarks,wrist));
    visible = visibility(landmarks,side.slice(0,3)) > .55;
    if (exercise === "Push-ups") {
      low = 90;
      const bodyAngle = angle(point(landmarks,shoulder),point(landmarks,hip),point(landmarks,ankle));
      const deviation = point(landmarks,hip).y - (point(landmarks,shoulder).y + point(landmarks,ankle).y) / 2;
      const alignment = bodyAngle > 160 ? "Straight" : bodyAngle > 140 ? "Slight Bend" : "Poor Form";
      const hipStatus = Math.abs(deviation) <= .08 ? "LEVEL" : deviation > 0 ? "SAGGING" : "PIKED UP";
      metrics = { elbow_angle: visible ? Math.round(movementAngle) : "N/A", body_alignment: alignment, hip_status: hipStatus, landmarks_visible: visible };
      if (visible && alignment !== "Straight") issue = "Keep your body in a straight line";
      if (visible && hipStatus !== "LEVEL") issue = "Keep your hips level";
    } else if (exercise === "Biceps Curls (Dumbbell)") {
      low = 50; high = 160; countStage = "down"; lowStage = "up";
      const drift = Math.abs(point(landmarks,elbow).x - point(landmarks,shoulder).x);
      const torsoLean = Math.abs((point(landmarks,11).x + point(landmarks,12).x - point(landmarks,23).x - point(landmarks,24).x) / 2);
      metrics = { elbow_angle: visible ? Math.round(movementAngle) : "N/A", shoulder_status: drift <= .06 ? "STABLE" : "ELBOW DRIFTING", swing_status: torsoLean <= .08 ? "NO SWING" : "SWINGING", landmarks_visible: visible };
      if (visible && drift > .06) issue = "Keep your elbow close to your side";
      if (visible && torsoLean > .08) issue = "Avoid swinging your torso";
    } else {
      low = 90; high = 160; countStage = "down";
      const knee = side[4] === 27 ? 25 : 26;
      const backAngle = angle(point(landmarks,shoulder),point(landmarks,hip),point(landmarks,knee));
      const backStatus = backAngle >= 160 ? "Neutral" : backAngle >= 140 ? "Slight Arch" : "Excessive Arch";
      metrics = { elbow_angle: visible ? Math.round(movementAngle) : "N/A", extension_status: !visible ? "N/A" : movementAngle >= 160 ? "FULL EXTENSION" : movementAngle >= 130 ? "NEARLY EXTENDED" : "PRESSING", back_arch_status: backStatus, landmarks_visible: visible };
      if (visible && backStatus !== "Neutral") issue = "Brace your core and keep your back steady";
    }
  }

  if (exercise === "Biceps Curls (Dumbbell)") { /* thresholds set above */ }
  if (exercise === "Shoulder Press") high = 160;
  if (visible) {
    const candidate = movementAngle <= low ? lowStage : movementAngle >= high ? (exercise === "Biceps Curls (Dumbbell)" ? "down" : "up") : null;
    if (!candidate || candidate === tracker.stage) { tracker.pending = null; tracker.pendingFrames = 0; }
    else {
      if (candidate === tracker.pending) tracker.pendingFrames += 1;
      else { tracker.pending = candidate; tracker.pendingFrames = 1; }
      if (tracker.pendingFrames >= 2) {
        if (candidate === countStage) { if (tracker.armed) tracker.reps += 1; tracker.armed = false; }
        else tracker.armed = true;
        tracker.stage = candidate; tracker.pending = null; tracker.pendingFrames = 0;
      }
    }
  }
  const formStatus = !visible ? "waiting" : issue ? "warning" : "good";
  return { ...metrics, reps: tracker.reps, exercise_stage: tracker.stage ?? "ready", rep_completed: false, pose_detected: visible, pose_status: visible ? "detected" : "not_detected", pose_confidence: Math.round(visibility(landmarks, exercise === "Squats" || exercise === "Lunges" ? [23,25,27] : [11,13,15]) * 100), form_status: formStatus, form_issue: issue, movement_valid: visible };
}

function drawPose(canvas: HTMLCanvasElement, landmarks: Landmark[] | null) {
  const context = canvas.getContext("2d");
  if (!context) return;
  const { width, height } = canvas;
  context.clearRect(0, 0, width, height);
  if (!landmarks) return;
  context.lineWidth = Math.max(3, width / 180);
  context.strokeStyle = "#a5f332";
  context.fillStyle = "#f4f8e9";
  for (const [from,to] of CONNECTIONS) {
    const a = point(landmarks,from), b = point(landmarks,to);
    if (a.visibility < .45 || b.visibility < .45) continue;
    context.beginPath(); context.moveTo(a.x*width,a.y*height); context.lineTo(b.x*width,b.y*height); context.stroke();
  }
  for (const joint of landmarks) if (joint.visibility >= .45) {
    context.beginPath(); context.arc(joint.x*width,joint.y*height,Math.max(3,width/240),0,Math.PI*2); context.fill();
  }
}

export default function WorkoutPage({ user, onBack, onDashboard, onHistory, onSignOut, initialExercise = "Squats", preparedStream }: Props) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const workerRef = useRef<Worker | null>(null);
  const inFlightRef = useRef(false);
  const lastTimestampRef = useRef(0);
  const lastVideoTimeRef = useRef(-1);
  const frameLoopRef = useRef(0);
  const trackerRef = useRef(freshTracker());
  const metricsRef = useRef<Metrics | null>(null);
  const repsRef = useRef(0);
  const startedAtRef = useRef(0);
  const savedRef = useRef(false);
  const [exercise] = useState<Exercise>(initialExercise);
  const [status, setStatus] = useState<"loading" | "ready" | "running" | "paused" | "stopped" | "error">("loading");
  const [message, setMessage] = useState("Loading the on-device movement coach…");
  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const [targetSets, setTargetSets] = useState(3);
  const [repsPerSet, setRepsPerSet] = useState(10);
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    const stream = preparedStream;
    const video = videoRef.current;
    if (!stream || !video) { setStatus("error"); setMessage("Camera stream was lost. Go back and reconnect your camera."); return; }
    video.srcObject = stream;
    void video.play().catch(() => undefined);
    const worker = new Worker(new URL("../workers/pose.worker.ts", import.meta.url));
    workerRef.current = worker;
    worker.onmessage = (event: MessageEvent<{ type: string; landmarks?: Landmark[] | null; message?: string }>) => {
      inFlightRef.current = false;
      if (event.data.type === "ready") { setStatus("ready"); setMessage("Camera is ready. Start when you are."); }
      else if (event.data.type === "error") { setStatus("error"); setMessage(event.data.message ?? "Movement tracking failed to start."); }
      else if (event.data.type === "pose") {
        const landmarks = event.data.landmarks ?? null;
        const canvas = canvasRef.current;
        const video = videoRef.current;
        if (canvas && video && video.videoWidth > 0 && (canvas.width !== video.videoWidth || canvas.height !== video.videoHeight)) {
          canvas.width = video.videoWidth; canvas.height = video.videoHeight;
        }
        if (canvas) drawPose(canvas, landmarks);
        if (statusRef.current === "running" && landmarks) {
          const next = analyze(exercise, landmarks, trackerRef.current);
          metricsRef.current = next; repsRef.current = trackerRef.current.reps;
          setMetrics(next);
        } else if (statusRef.current === "running") {
          const next = { pose_detected: false, pose_status: "not_detected", form_status: "waiting", form_issue: "", reps: trackerRef.current.reps };
          metricsRef.current = next; setMetrics(next);
        }
      }
    };
    worker.onerror = () => { inFlightRef.current = false; setStatus("error"); setMessage("The movement model could not start in this browser."); };
    worker.postMessage({ type: "init" });
    return () => {
      cancelAnimationFrame(frameLoopRef.current);
      worker.postMessage({ type: "dispose" }); workerRef.current = null;
      inFlightRef.current = false;
      stream.getTracks().forEach((track) => track.stop());
    };
  }, [exercise, preparedStream]);

  const statusRef = useRef(status);
  useEffect(() => { statusRef.current = status; }, [status]);

  useEffect(() => {
    if (status !== "running") return;
    let active = true;
    const video = videoRef.current;
    const capture = (now: number) => {
      if (!active) return;
      if (video && video.readyState >= HTMLMediaElement.HAVE_CURRENT_DATA && !inFlightRef.current && video.currentTime > 0 && video.currentTime !== lastVideoTimeRef.current && now - lastTimestampRef.current >= 66) {
        inFlightRef.current = true;
        const timestamp = Math.max(now, lastTimestampRef.current + 1);
        lastTimestampRef.current = timestamp;
        lastVideoTimeRef.current = video.currentTime;
        try {
          const frame = new VideoFrame(video, { timestamp: Math.round(timestamp * 1000) });
          workerRef.current?.postMessage({ type: "frame", frame, timestamp }, [frame]);
        } catch { inFlightRef.current = false; }
      }
      frameLoopRef.current = requestAnimationFrame(capture);
    };
    frameLoopRef.current = requestAnimationFrame(capture);
    return () => { active = false; cancelAnimationFrame(frameLoopRef.current); };
  }, [status]);

  useEffect(() => {
    if (status !== "running") return;
    const timer = window.setInterval(() => setElapsed(Math.floor((Date.now() - startedAtRef.current) / 1000)), 250);
    return () => window.clearInterval(timer);
  }, [status]);

  function start() {
    trackerRef.current = freshTracker(); metricsRef.current = null; repsRef.current = 0; lastTimestampRef.current = 0;
    startedAtRef.current = Date.now() - elapsed * 1000; savedRef.current = false;
    setMetrics(null); setStatus("running"); setMessage("Move into view. Your camera preview stays live while tracking runs in the background.");
  }

  function finish(destination: "dashboard" | "history" | "back" | "signout") {
    setStatus("stopped");
    const totalReps = repsRef.current;
    if (totalReps > 0 && !savedRef.current) {
      const entry: HistoryEntry = { exercise_name: exercise, reps: totalReps, sets: Math.min(targetSets, Math.floor(totalReps / repsPerSet)), time: elapsed, form_score: null, set_breakdown: Array.from({ length: Math.ceil(totalReps / repsPerSet) }, (_, index) => Math.min(repsPerSet, totalReps - index * repsPerSet)), created_at: new Date().toISOString() };
      saveLocalWorkout(entry); savedRef.current = true;
    }
    if (destination === "dashboard") onDashboard();
    else if (destination === "history") onHistory();
    else if (destination === "back") onBack();
    else onSignOut();
  }

  const reps = Number(metrics?.reps ?? 0);
  const setsDone = Math.min(targetSets, Math.floor(reps / repsPerSet));
  const feedback = typeof metrics?.form_issue === "string" && metrics.form_issue ? metrics.form_issue : metrics?.pose_detected === true ? "Your movement looks good. Keep a steady pace." : "Move back until your full body is in the camera view.";
  const time = `${String(Math.floor(elapsed / 60)).padStart(2,"0")}:${String(elapsed % 60).padStart(2,"0")}`;

  return <main className="workout-page">
    <WorkoutFlowNav user={user} step={3} onDashboard={() => finish("dashboard")} onSignOut={() => finish("signout")} />
    <button className="btn-ghost workout-back" disabled={status === "running"} onClick={() => finish("back")}>← BACK TO EXERCISE SELECTION</button>
    <div className="section-header"><span className="section-tag">ON DEVICE · PRIVATE MOVEMENT TRACKING</span><h1>Let’s <em>move.</em></h1><p className="workout-intro">Your camera stays on this device. The coach tracks your movement without sending video to a server.</p></div>
    <section className="workout-panel">
      <div className="workout-controls"><label>Exercise<input value={exercise} readOnly /></label><label>Sets to complete<input type="number" min="1" max="50" disabled={status === "running"} value={targetSets} onChange={(event) => setTargetSets(Math.max(1, Math.min(50, Number(event.target.value) || 1)))} /></label><label>Reps in each set<input type="number" min="1" max="50" disabled={status === "running"} value={repsPerSet} onChange={(event) => setRepsPerSet(Math.max(1, Math.min(50, Number(event.target.value) || 1)))} /></label>
        {status === "ready" || status === "stopped" ? <button className="btn-primary" onClick={start}>Start workout</button> : null}
        {status === "loading" ? <button className="btn-primary" disabled>Loading movement coach…</button> : null}
        {status === "running" ? <button className="btn-ghost" onClick={() => setStatus("paused")}>Pause</button> : null}
        {status === "paused" ? <button className="btn-primary" onClick={() => setStatus("running")}>Resume</button> : null}
        {(status === "running" || status === "paused") ? <button className="btn-ghost" onClick={() => finish("dashboard")}>Finish workout</button> : null}
      </div>
      <div className="workout-live-layout">
        <div className="workout-video-grid"><div className="workout-video-panel" style={{ position: "relative" }}>
          <div className="workout-feed-heading"><span className="section-tag">LIVE CAMERA</span><span className={`workout-connection connection-${status === "running" || status === "paused" ? "connected" : status}`}>{status === "running" ? "Tracking" : status === "paused" ? "Paused" : status === "ready" ? "Ready" : status === "loading" ? "Loading" : status === "error" ? "Unavailable" : "Stopped"}</span></div>
          <video ref={videoRef} autoPlay muted playsInline aria-label="Live camera preview" />
          <canvas ref={canvasRef} aria-hidden="true" style={{ position: "absolute", inset: "48px 0 0", width: "100%", height: "calc(100% - 48px)", pointerEvents: "none" }} />
          {(status === "loading" || status === "error") ? <div className="workout-feed-message" role={status === "error" ? "alert" : "status"}>{message}</div> : null}
        </div></div>
        <aside className="workout-live-sidebar"><div className="workout-pose-status"><span className={`pose-indicator${metrics?.pose_detected ? " is-detected" : ""}`} /><div><span className="section-tag">COACH STATUS</span><strong>{status === "paused" ? "Workout paused" : metrics?.pose_detected ? "Following your movement" : status === "running" ? "Finding your position…" : message}</strong></div></div>
          <div className="workout-kpis"><div><span>TIME</span><strong>{time}</strong></div><div><span>TOTAL REPS</span><strong>{reps}</strong></div><div><span>SETS</span><strong>{setsDone}<small> / {targetSets}</small></strong></div><div><span>REPS THIS SET</span><strong>{reps % repsPerSet}<small> / {repsPerSet}</small></strong></div></div>
          <div className="set-progress"><div><span>THIS SET</span><span>{Math.round(((reps % repsPerSet) / repsPerSet) * 100)}%</span></div><div className="set-progress-track"><span style={{ width: `${((reps % repsPerSet) / repsPerSet) * 100}%` }} /></div></div>
        </aside>
      </div>
      <div className="workout-feedback"><span className="section-tag">MOVEMENT TIP</span><p role="status">{status === "error" ? message : feedback}</p>
        {exerciseOptions.find((item) => item.name === exercise)?.instructions.map((tip) => <small key={tip}>{tip}</small>)}
      </div>
      {status === "stopped" ? <div className="summary-actions"><button className="button button-primary" onClick={() => finish("history")}>View workout history</button><button className="button button-secondary" onClick={() => finish("back")}>Start another workout</button></div> : null}
    </section>
  </main>;
}
