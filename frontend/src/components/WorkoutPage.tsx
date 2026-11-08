import { useEffect, useRef, useState } from "react";
import {
  createWorkoutSession,
  getWorkoutMetrics,
  getVoice,
  getWorkoutHistory,
  submitWebRTCOffer,
  updateWorkoutStatus,
  type Exercise,
  type WorkoutMetrics,
  type HistoryEntry,
} from "../services/api";

const exercises: Exercise[] = [
  "Squats",
  "Push-ups",
  "Biceps Curls (Dumbbell)",
  "Shoulder Press",
  "Lunges",
];

export default function WorkoutPage({ onBack }: { onBack: () => void }) {
  const [exercise, setExercise] = useState<Exercise>("Squats");
  const [targetSets, setTargetSets] = useState(3);
  const [repsPerSet, setRepsPerSet] = useState(10);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [metrics, setMetrics] = useState<WorkoutMetrics | null>(null);
  const [status, setStatus] = useState("ready");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [voiceEnabled, setVoiceEnabled] = useState(true);
  const [coachText, setCoachText] = useState("Coach is standing by.");
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const [history, setHistory] = useState<HistoryEntry[]>([]);
  const processedVideo = useRef<HTMLVideoElement>(null);
  const peerConnection = useRef<RTCPeerConnection | null>(null);
  const mediaStream = useRef<MediaStream | null>(null);

  useEffect(() => {
    if (!sessionId || status !== "running") return;
    const intervalId = window.setInterval(() => {
      getWorkoutMetrics(sessionId)
        .then((nextMetrics) => {
          setMetrics(nextMetrics);
          setElapsedSeconds(nextMetrics.elapsed_seconds);
          if (nextMetrics.workout_completed) {
            setStatus("stopped");
            mediaStream.current?.getTracks().forEach((track) => track.stop());
            void peerConnection.current?.close();
            getWorkoutHistory().then(setHistory).catch(() => undefined);
          }
        })
        .catch((requestError: unknown) => {
          setError(
            requestError instanceof Error
              ? requestError.message
              : "Unable to read workout metrics.",
          );
        });
    }, 1000);
    return () => window.clearInterval(intervalId);
  }, [sessionId, status]);

  useEffect(() => {
    if (!sessionId || !voiceEnabled || status === "ready") return;
    const intervalId = window.setInterval(() => {
      getVoice(sessionId)
        .then((voice) => {
          if (!voice) return;
          setCoachText(voice.text);
          if (voice.audio_base64) {
            new Audio(`data:audio/mp3;base64,${voice.audio_base64}`).play().catch(() => undefined);
          }
        })
        .catch(() => undefined);
    }, 1000);
    return () => window.clearInterval(intervalId);
  }, [sessionId, status, voiceEnabled]);

  useEffect(() => {
    if (status !== "running") return;
    const intervalId = window.setInterval(() => setElapsedSeconds((value) => value + 1), 1000);
    return () => window.clearInterval(intervalId);
  }, [status]);

  useEffect(
    () => () => {
      mediaStream.current?.getTracks().forEach((track) => track.stop());
      void peerConnection.current?.close();
    },
    [],
  );

  async function startWorkout() {
    setError(null);
    setBusy(true);
    try {
      const session = await createWorkoutSession(
        exercise,
        targetSets,
        repsPerSet,
      );
      if (!navigator.mediaDevices?.getUserMedia) {
        throw new Error("This browser does not support webcam access.");
      }
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { width: 640, height: 480, frameRate: { ideal: 15, max: 24 } },
        audio: false,
      });
      mediaStream.current = stream;

      const connection = new RTCPeerConnection();
      peerConnection.current = connection;
      connection.onconnectionstatechange = () => {
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
      mediaStream.current?.getTracks().forEach((track) => track.stop());
      void peerConnection.current?.close();
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Unable to start the workout.",
      );
    } finally {
      setBusy(false);
    }
  }

  async function changeStatus(action: "pause" | "stop") {
    if (!sessionId) return;
    setBusy(true);
    try {
      const result = await updateWorkoutStatus(sessionId, action);
      setStatus(result.status);
      if (action === "stop") {
        mediaStream.current?.getTracks().forEach((track) => track.stop());
        await peerConnection.current?.close();
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

  return (
    <main className="workout-page">
      <button className="btn-ghost workout-back" onClick={onBack}>
        ← BACK TO LANDING
      </button>
      <div className="section-header">
        <span className="section-tag">// WORKOUT</span>
        <h1 className="section-title">Train with <em>real-time feedback</em></h1>
      </div>
      <section className="workout-panel">
        <div className="workout-controls">
          <label>
            Exercise
            <select value={exercise} onChange={(event) => setExercise(event.target.value as Exercise)}>
              {exercises.map((option) => <option key={option}>{option}</option>)}
            </select>
          </label>
          <label>
            Sets
            <input type="number" min="1" max="50" value={targetSets} onChange={(event) => setTargetSets(Number(event.target.value))} />
          </label>
          <label>
            Reps per set
            <input type="number" min="1" max="50" value={repsPerSet} onChange={(event) => setRepsPerSet(Number(event.target.value))} />
          </label>
          <label className="voice-toggle"><input type="checkbox" checked={voiceEnabled} onChange={(event) => setVoiceEnabled(event.target.checked)} /> Voice coaching</label>
          {!sessionId || status === "stopped" ? <button className="btn-primary" disabled={busy} onClick={() => void startWorkout()}>START WORKOUT</button> : null}
          {status === "running" ? <button className="btn-ghost" disabled={busy} onClick={() => void changeStatus("pause")}>PAUSE</button> : null}
          {status === "paused" ? <button className="btn-primary" disabled={busy} onClick={resumeWorkout}>RESUME</button> : null}
          {sessionId && status !== "stopped" ? <button className="btn-ghost" disabled={busy} onClick={() => void changeStatus("stop")}>STOP</button> : null}
        </div>
        <div className="workout-video-grid">
          <div><span className="section-tag">PROCESSED FEED</span><video ref={processedVideo} autoPlay playsInline /></div>
        </div>
        <div className="workout-metrics">
          <strong>{status.toUpperCase()}</strong>
          <span>Time: {formatTime(elapsedSeconds)}</span>
          <span>Reps: {metrics?.reps ?? 0}</span>
          <span>Sets: {metrics?.sets_completed ?? 0} / {targetSets}</span>
          <span>Current set: {metrics?.current_set_reps ?? 0} / {repsPerSet}</span>
        </div>
        <div className="workout-feedback">
          <span className="section-tag">// COACH</span>
          <p>{coachText}</p>
          <div className="workout-detail-grid">
            <span>Angle: {metricValue("knee_angle") !== "N/A" ? metricValue("knee_angle") : metricValue("elbow_angle")}°</span>
            <span>Form: {metricValue("depth_status") !== "N/A" ? metricValue("depth_status") : metricValue("body_alignment")}</span>
            <span>Balance: {metricValue("balance_status")}</span>
          </div>
        </div>
        {history.length > 0 ? <div className="workout-history"><span className="section-tag">// HISTORY</span>{history.slice(0, 5).map((entry) => <div key={`${entry.exercise_name}-${entry.created_at}`}>{entry.exercise_name}: {entry.reps} reps / {entry.sets} sets</div>)}</div> : null}
        {error ? <p className="workout-error" role="alert">{error}</p> : null}
      </section>
    </main>
  );
}
