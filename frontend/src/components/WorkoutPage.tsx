import { useEffect, useRef, useState } from "react";
import {
  createWorkoutSession,
  getWebRTCIceServers,
  getWorkoutMetrics,
  getVoice,
  getWorkoutHistory,
  submitWebRTCOffer,
  updateWorkoutStatus,
  type Exercise,
  type WorkoutSession,
  type WorkoutMetrics,
  type HistoryEntry,
  type AuthUser,
} from "../services/api";
import { exerciseOptions } from "./exerciseOptions";
import WorkoutFlowNav from "./WorkoutFlowNav";

function readVoicePreference(): boolean {
  try { return window.localStorage.getItem("ai_gym_voice_coaching") !== "false"; }
  catch { return true; }
}

const exerciseMetrics: Record<Exercise, { label: string; key: string; angle?: boolean }[]> = {
  "Squats": [
    { label: "Knee angle", key: "knee_angle", angle: true },
    { label: "Depth", key: "depth_status" },
    { label: "Back angle", key: "back_angle", angle: true },
  ],
  "Push-ups": [
    { label: "Elbow angle", key: "elbow_angle", angle: true },
    { label: "Alignment", key: "body_alignment" },
    { label: "Hip position", key: "hip_status" },
  ],
  "Biceps Curls (Dumbbell)": [
    { label: "Elbow angle", key: "elbow_angle", angle: true },
    { label: "Shoulder", key: "shoulder_status" },
    { label: "Movement", key: "swing_status" },
  ],
  "Shoulder Press": [
    { label: "Elbow angle", key: "elbow_angle", angle: true },
    { label: "Extension", key: "extension_status" },
    { label: "Back", key: "back_arch_status" },
  ],
  "Lunges": [
    { label: "Front knee angle", key: "front_knee_angle", angle: true },
    { label: "Torso angle", key: "torso_angle", angle: true },
    { label: "Balance", key: "balance_status" },
  ],
};

export default function WorkoutPage({ user, onBack, onDashboard, onHistory, onSignOut, initialExercise, preparedStream }: { user: AuthUser; onBack: () => void; onDashboard: () => void; onHistory: () => void; onSignOut: () => void; initialExercise?: Exercise; preparedStream?: MediaStream }) {
  const [exercise, setExercise] = useState<Exercise>(initialExercise ?? "Squats");
  const [targetSets, setTargetSets] = useState(3);
  const [repsPerSet, setRepsPerSet] = useState(10);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [metrics, setMetrics] = useState<WorkoutMetrics | null>(null);
  const [status, setStatus] = useState<WorkoutSession["status"]>("ready");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [voiceEnabled, setVoiceEnabled] = useState(readVoicePreference);
  const [coachText, setCoachText] = useState("Coach is standing by.");
  const [voiceStatus, setVoiceStatus] = useState<"off" | "idle" | "waiting" | "ready" | "speaking" | "unavailable" | "error" | "paused">("idle");
  const [connectionState, setConnectionState] = useState<RTCPeerConnectionState | "new">("new");
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const [history, setHistory] = useState<HistoryEntry[]>([]);
  const processedVideo = useRef<HTMLVideoElement>(null);
  const peerConnection = useRef<RTCPeerConnection | null>(null);
  const mediaStream = useRef<MediaStream | null>(null);
  const preparedMediaStream = useRef<MediaStream | null>(preparedStream ?? null);
  const voiceAudio = useRef<HTMLAudioElement | null>(null);
  const metricsRequestActive = useRef(false);

  useEffect(() => {
    try { window.localStorage.setItem("ai_gym_voice_coaching", String(voiceEnabled)); }
    catch { /* Keep coaching available for this session if storage is disabled. */ }
  }, [voiceEnabled]);

  useEffect(() => {
    let active = true;
    getWorkoutHistory()
      .then((savedHistory) => {
        if (active) setHistory(savedHistory);
      })
      .catch(() => {
        if (active) setError("Unable to load workout history.");
      });
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    if (!sessionId || status !== "running") return;
    const intervalId = window.setInterval(() => {
      if (metricsRequestActive.current) return;
      metricsRequestActive.current = true;
      getWorkoutMetrics(sessionId)
        .then((nextMetrics) => {
          setMetrics(nextMetrics);
          setElapsedSeconds(nextMetrics.elapsed_seconds);
          if (nextMetrics.workout_completed) {
            void updateWorkoutStatus(sessionId, "stop").catch(() => undefined);
            setStatus("stopped");
            mediaStream.current?.getTracks().forEach((track) => track.stop());
            void peerConnection.current?.close();
            peerConnection.current = null;
            mediaStream.current = null;
            setConnectionState("closed");
            getWorkoutHistory().then(setHistory).catch(() => undefined);
          }
        })
        .catch((requestError: unknown) => {
          setError(
            requestError instanceof Error
              ? requestError.message
              : "Unable to read workout metrics.",
          );
        })
        .finally(() => { metricsRequestActive.current = false; });
    }, 1000);
    return () => window.clearInterval(intervalId);
  }, [sessionId, status]);

  useEffect(() => {
    if (!voiceEnabled) {
      setVoiceStatus("off");
      return;
    }
    if (!sessionId || status !== "running") {
      setVoiceStatus(status === "paused" ? "paused" : "idle");
      return;
    }
    setVoiceStatus("waiting");
    const intervalId = window.setInterval(() => {
      getVoice(sessionId)
        .then((voice) => {
          if (!voice) return;
          if (!voice.available) {
            setVoiceStatus("unavailable");
            return;
          }
          if (voice.error) {
            setVoiceStatus("error");
            return;
          }
          if (voice.text) setCoachText(voice.text);
          if (voice.audio_base64) {
            voiceAudio.current?.pause();
            const audio = new Audio(`data:audio/mp3;base64,${voice.audio_base64}`);
            voiceAudio.current = audio;
            audio.onended = () => setVoiceStatus("ready");
            audio.play()
              .then(() => setVoiceStatus("speaking"))
              .catch(() => setVoiceStatus("error"));
          } else if (voice.text) {
            setVoiceStatus("ready");
          }
        })
        .catch(() => setVoiceStatus("unavailable"));
    }, 1000);
    return () => window.clearInterval(intervalId);
  }, [sessionId, status, voiceEnabled]);

  useEffect(
    () => () => {
      mediaStream.current?.getTracks().forEach((track) => track.stop());
      void peerConnection.current?.close();
      voiceAudio.current?.pause();
    },
    [],
  );

  async function startWorkout() {
    setError(null);
    setBusy(true);
    let createdSessionId: string | null = null;
    try {
      const stream = preparedMediaStream.current ?? await (async () => {
        if (!navigator.mediaDevices?.getUserMedia) {
          throw new Error("This browser does not support webcam access.");
        }
        return navigator.mediaDevices.getUserMedia({
          video: { width: 640, height: 480, frameRate: { ideal: 15, max: 24 } },
          audio: false,
        });
      })();
      preparedMediaStream.current = null;
      mediaStream.current = stream;
      const session = await createWorkoutSession(
        exercise,
        targetSets,
        repsPerSet,
      );
      createdSessionId = session.session_id;

      const { ice_servers: iceServers } = await getWebRTCIceServers();
      const connection = new RTCPeerConnection({ iceServers });
      peerConnection.current = connection;
      setConnectionState("connecting");
      connection.onconnectionstatechange = () => {
        setConnectionState(connection.connectionState);
        if (connection.connectionState === "failed" || connection.connectionState === "disconnected") {
          setError("WebRTC connection lost. Stop and restart the workout.");
        }
      };
      connection.addTransceiver("video", { direction: "sendrecv" });
      const sender = connection.getSenders()[0];
      await sender.replaceTrack(stream.getVideoTracks()[0]);
      connection.ontrack = (event) => {
        if (processedVideo.current) {
          processedVideo.current.srcObject = event.streams[0];
          void processedVideo.current.play().catch(() => undefined);
        }
      };

      const offer = await connection.createOffer();
      await connection.setLocalDescription(offer);
      const answer = await submitWebRTCOffer(session.session_id, offer);
      await connection.setRemoteDescription(answer);
      await updateWorkoutStatus(session.session_id, "start");
      setSessionId(session.session_id);
      setStatus("running");
      setMetrics(null);
      setElapsedSeconds(0);
    } catch (requestError: unknown) {
      if (createdSessionId) {
        void updateWorkoutStatus(createdSessionId, "stop").catch(() => undefined);
      }
      mediaStream.current?.getTracks().forEach((track) => track.stop());
      mediaStream.current = null;
      void peerConnection.current?.close();
      peerConnection.current = null;
      setConnectionState("closed");
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Unable to start the workout.",
      );
    } finally {
      setBusy(false);
    }
  }

  async function exitWorkout(destination: "exercise" | "dashboard" | "signout" = "exercise") {
    if (sessionId && (status === "running" || status === "paused")) {
      const prompt = destination === "signout"
        ? "Finish and save this workout before signing out?"
        : `Finish this workout and return to your ${destination === "dashboard" ? "dashboard" : "exercise selection"}?`;
      if (!window.confirm(prompt)) return;
      setBusy(true);
      try {
        await updateWorkoutStatus(sessionId, "stop");
        setStatus("stopped");
        mediaStream.current?.getTracks().forEach((track) => track.stop());
        mediaStream.current = null;
        await peerConnection.current?.close();
        peerConnection.current = null;
        setConnectionState("closed");
      } catch (requestError) {
        setError(requestError instanceof Error ? requestError.message : "Unable to finish the workout.");
        return;
      } finally {
        setBusy(false);
      }
    }
    if (destination === "dashboard") onDashboard();
    else if (destination === "signout") onSignOut();
    else onBack();
  }

  async function changeStatus(action: "pause" | "stop") {
    if (!sessionId) return;
    setBusy(true);
    try {
      const result = await updateWorkoutStatus(sessionId, action);
      setStatus(result.status);
      if (action === "stop") {
        mediaStream.current?.getTracks().forEach((track) => track.stop());
        mediaStream.current = null;
        await peerConnection.current?.close();
        peerConnection.current = null;
        setConnectionState("closed");
        const finalMetrics = await getWorkoutMetrics(sessionId);
        setMetrics(finalMetrics);
        setElapsedSeconds(finalMetrics.elapsed_seconds);
        setHistory(await getWorkoutHistory());
      }
    } catch (requestError: unknown) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Unable to update workout state.",
      );
    } finally {
      setBusy(false);
    }
  }

  function resumeWorkout() {
    if (sessionId) {
      void updateWorkoutStatus(sessionId, "start")
        .then(() => setStatus("running"))
        .catch(() => setError("Unable to resume the workout."));
    }

  }

  const formatTime = (seconds: number) =>
    `${Math.floor(seconds / 60).toString().padStart(2, "0")}:${(seconds % 60)
      .toString()
      .padStart(2, "0")}`;

  const metricValue = (key: string) => metrics?.metrics[key] ?? "N/A";
  const poseDetected = metrics?.metrics.pose_detected === true;
  const landmarksVisible = metrics?.metrics.landmarks_visible;
  const formStatus = typeof metrics?.metrics.form_status === "string" ? metrics.metrics.form_status : "waiting";
  const formIssue = typeof metrics?.metrics.form_issue === "string" ? metrics.metrics.form_issue : "";
  const poseSignal = metrics?.metrics.pose_status;
  const poseStatus = !sessionId
    ? "Ready when you are"
    : poseDetected && landmarksVisible === false
      ? "I can see you. Move back so your full body is visible."
      : poseDetected
      ? "You’re in view"
      : poseSignal === "loading"
        ? "Getting the coach ready"
        : poseSignal === "unavailable"
          ? "Movement tracking is unavailable. Try again in a moment."
          : poseSignal === "error"
            ? "Movement tracking stopped because of an error."
      : metrics
        ? "I can’t see you yet. Move into the camera frame."
        : "Finding your position…";
  const connectionLabel = connectionState === "connected"
    ? "Connected"
    : connectionState === "connecting" || connectionState === "new"
      ? "Connecting"
      : connectionState === "disconnected"
        ? "Disconnected"
        : connectionState === "failed"
          ? "Connection failed"
          : connectionState === "closed"
            ? "Closed"
            : connectionState;
  const voiceStatusLabel: Record<typeof voiceStatus, string> = {
    off: "Off",
    idle: "Waiting to start",
    waiting: "Waiting for a cue",
    ready: "Cue ready",
    speaking: "Speaking",
    unavailable: "Voice tips unavailable",
    error: "Couldn’t play the last voice tip",
    paused: "Paused",
  };
  const progressPercent = Math.min(100, ((metrics?.current_set_reps ?? 0) / repsPerSet) * 100);
  const configurationLocked = Boolean(sessionId && status !== "stopped");
  const displayedFeedback = !sessionId
    ? "Start your workout and I’ll follow your movement."
    : !poseDetected
      ? "Move into the camera frame so I can see you."
      : landmarksVisible === false
        ? `I can see you, but not your full movement. ${exerciseOptions.find((option) => option.name === exercise)?.camera ?? "Adjust your camera view."}`
      : formIssue
        ? formIssue
      : voiceStatus === "off"
        ? "You’re in view. Spoken tips are turned off."
        : voiceStatus === "unavailable"
          ? "You’re in view. Spoken tips aren’t available right now."
          : voiceStatus === "error"
            ? "You’re in view, but the last spoken tip couldn’t play."
            : voiceStatus === "waiting"
              ? "You’re in view. I’ll speak up when I have a tip."
              : voiceStatus === "paused"
                ? "Workout paused. Resume when you are ready."
            : coachText;

  return (
    <main className="workout-page">
      <WorkoutFlowNav user={user} step={3} onDashboard={() => void exitWorkout("dashboard")} onSignOut={() => void exitWorkout("signout")} />
      <button className="btn-ghost workout-back" disabled={busy} onClick={() => void exitWorkout()}>
        ← BACK TO EXERCISE SELECTION
      </button>
      <div className="section-header">
        <span className="section-tag">YOUR SESSION</span>
        <h1 className="section-title">Let’s <em>move.</em></h1>
        <p className="workout-intro">The coach follows your movement and counts each rep. Keep your full body in view.</p>
      </div>
      <section className="workout-panel">
        <div className="workout-controls">
          <label>
            Exercise
            <select disabled={configurationLocked || Boolean(initialExercise)} value={exercise} onChange={(event) => setExercise(event.target.value as Exercise)}>
              {exerciseOptions.map(({ name }) => <option key={name}>{name}</option>)}
            </select>
          </label>
          <label>
            Sets to complete
            <input disabled={configurationLocked} type="number" min="1" max="50" value={targetSets} onChange={(event) => setTargetSets(Number(event.target.value))} />
          </label>
          <label>
            Reps in each set
            <input disabled={configurationLocked} type="number" min="1" max="50" value={repsPerSet} onChange={(event) => setRepsPerSet(Number(event.target.value))} />
          </label>
          <label className="voice-toggle"><input type="checkbox" checked={voiceEnabled} onChange={(event) => setVoiceEnabled(event.target.checked)} /> Spoken tips</label>
          {!sessionId || status === "stopped" ? <button className="btn-primary" disabled={busy} onClick={() => void startWorkout()}>Start workout</button> : null}
          {status === "running" ? <button className="btn-ghost" disabled={busy} onClick={() => void changeStatus("pause")}>Pause</button> : null}
          {status === "paused" ? <button className="btn-primary" disabled={busy} onClick={resumeWorkout}>Resume</button> : null}
          {sessionId && status !== "stopped" ? <button className="btn-ghost" disabled={busy} onClick={() => void changeStatus("stop")}>Finish workout</button> : null}
        </div>
        <div className="workout-live-layout">
          <div className="workout-video-grid">
            <div className="workout-video-panel">
              <div className="workout-feed-heading"><span className="section-tag">LIVE COACH VIEW</span><span className={`workout-connection connection-${connectionState}`}>{connectionLabel}</span></div>
              <video ref={processedVideo} autoPlay playsInline aria-label="Processed workout video with pose overlay" />
              {connectionState !== "connected" ? <div className="workout-feed-message" role="status">{sessionId ? `Camera ${connectionLabel.toLowerCase()}.` : "Your live camera view will appear here when you start."}</div> : null}
            </div>
          </div>
          <aside className="workout-live-sidebar">
            <div className="workout-pose-status"><span className={`pose-indicator${poseDetected ? " is-detected" : ""}`} />
              <div><span className="section-tag">COACH STATUS</span><strong>{poseStatus}</strong></div>
            </div>
            <div className="workout-kpis">
              <div><span>TIME</span><strong>{formatTime(elapsedSeconds)}</strong></div>
              <div><span>TOTAL REPS</span><strong>{metrics?.reps ?? 0}</strong></div>
              <div><span>SETS</span><strong>{metrics?.sets_completed ?? 0}<small> / {targetSets}</small></strong></div>
              <div><span>REPS THIS SET</span><strong>{metrics?.current_set_reps ?? 0}<small> / {repsPerSet}</small></strong></div>
              <div><span>FORM SCORE</span><strong>{metrics?.form_score == null ? "—" : metrics.form_score}<small>{metrics?.form_score == null ? " waiting" : " / 100"}</small></strong></div>
            </div>
            <div className="set-progress" aria-label={`${metrics?.current_set_reps ?? 0} of ${repsPerSet} reps in current set`}>
              <div><span>THIS SET</span><span>{Math.round(progressPercent)}%</span></div>
              <div className="set-progress-track"><span style={{ width: `${progressPercent}%` }} /></div>
            </div>
            <div className="workout-system-status">
              <div><span>CAMERA</span><strong>{connectionLabel}</strong></div>
              <div><span>BODY TRACKING</span><strong>{landmarksVisible === false ? "Move back a little" : poseDetected ? "Following you" : sessionId ? "Looking for you" : "Ready to start"}</strong></div>
              <div><span>SPOKEN TIPS</span><strong>{voiceStatusLabel[voiceStatus]}</strong></div>
            </div>
          </aside>
        </div>
        <div className="workout-feedback">
          <div className="feedback-heading"><span className="section-tag">MOVEMENT TIPS</span>
            {sessionId ? <span className={`feedback-state feedback-${formStatus}`}>{formStatus === "good" ? "Looking good" : formStatus === "waiting" ? "Waiting for a clear view" : formStatus === "incorrect" ? "Adjust your form" : "Small adjustment"}</span> : null}
          </div>
          <p role="status">{displayedFeedback}</p>
          <div className="feedback-meta"><span>VIEW QUALITY <strong>{typeof metrics?.metrics.pose_confidence === "number" ? `${metrics.metrics.pose_confidence}%` : "—"}</strong></span><span>MOVEMENT <strong>{typeof metrics?.metrics.exercise_stage === "string" ? metrics.metrics.exercise_stage : "—"}</strong></span></div>
          <div className="workout-detail-grid" aria-label={`${exercise} movement measurements`}>
            {exerciseMetrics[exercise].map((item) => {
              const value = poseDetected ? metricValue(item.key) : "—";
              return <div className="workout-detail-item" key={item.key}><span>{item.label}</span><strong>{value === "N/A" ? "—" : `${value}${item.angle && value !== "—" ? "°" : ""}`}</strong></div>;
            })}
          </div>
          <details className="form-score-method"><summary>How the form score works</summary><p>The score is based on the movement the camera can see. It appears after enough clear movement has been recorded and may be missing if your body is out of view. Use it as a coaching guide, not medical advice.</p></details>
        </div>
        {status === "stopped" && sessionId ? <section className="workout-summary" aria-live="polite"><span className="section-tag">SESSION SUMMARY</span><h2>{metrics?.workout_completed ? "Workout complete" : "Workout ended"}</h2><p>{metrics?.reps ? "Your workout was saved to your history." : "No reps were counted this time."}</p><div><span>{exercise}</span><span>{metrics?.reps ?? 0} reps</span><span>{metrics?.sets_completed ?? 0} sets</span><span>{formatTime(elapsedSeconds)}</span><span>{metrics?.form_score == null ? "No form score this time (not enough movement data)." : `Form score: ${metrics.form_score}/100`}</span></div><small>Form scores are estimates, not medical advice.</small><div className="summary-actions"><button className="button button-primary" type="button" onClick={onHistory}>View workout history</button><button className="button button-secondary" type="button" onClick={onDashboard}>Return to dashboard</button><button className="button button-secondary" type="button" onClick={onBack}>Start another workout</button></div></section> : null}
        {history.length > 0 ? <div className="workout-history"><span className="section-tag">// HISTORY</span>{history.slice(0, 5).map((entry) => <div key={`${entry.exercise_name}-${entry.created_at}`}>{entry.exercise_name}: {entry.reps} reps / {entry.sets} sets</div>)}</div> : null}
        {error ? <p className="workout-error" role="alert">{error}</p> : null}
      </section>
    </main>
  );
}
