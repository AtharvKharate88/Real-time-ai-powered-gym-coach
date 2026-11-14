import { useCallback, useEffect, useRef, useState } from "react";
import type { AuthUser, Exercise } from "../services/api";
import WorkoutFlowNav from "./WorkoutFlowNav";

interface CameraSetupPageProps {
  user: AuthUser;
  cameraGuidance: string;
  exercise: Exercise;
  onContinue: (stream: MediaStream) => void;
  onBack: () => void;
  onDashboard: () => void;
  onSignOut: () => void;
}

export default function CameraSetupPage({ user, cameraGuidance, exercise, onContinue, onBack, onDashboard, onSignOut }: CameraSetupPageProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const cameraRequestRef = useRef<{ deviceId?: string; promise: Promise<void> } | null>(null);
  const transferredRef = useRef(false);
  const [devices, setDevices] = useState<MediaDeviceInfo[]>([]);
  const [deviceId, setDeviceId] = useState("");
  const [status, setStatus] = useState<"connecting" | "ready" | "error">("connecting");
  const [error, setError] = useState("");
  const [attempt, setAttempt] = useState(0);

  const connectCamera = useCallback((requestedDeviceId?: string) => {
    const existingRequest = cameraRequestRef.current;
    if (existingRequest && existingRequest.deviceId === requestedDeviceId) return existingRequest.promise;

    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;
    setStatus("connecting");
    setError("");
    const request = (async () => {
      try {
        if (!navigator.mediaDevices?.getUserMedia) {
          throw new Error("Camera access is not available in this browser. Use a current browser over HTTPS or localhost.");
        }
        const stream = await navigator.mediaDevices.getUserMedia({
          video: {
            ...(requestedDeviceId ? { deviceId: { exact: requestedDeviceId } } : {}),
            width: { ideal: 640, max: 640 },
            height: { ideal: 480, max: 480 },
            frameRate: { ideal: 15, max: 24 },
          },
          audio: false,
        });
        streamRef.current = stream;
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
          await videoRef.current.play();
        }

        const activeDevice = stream.getVideoTracks()[0]?.getSettings().deviceId ?? requestedDeviceId ?? "";
        setDeviceId(activeDevice);
        setStatus("ready");

        // Device names are useful for the selector, but should not delay the live preview.
        void navigator.mediaDevices.enumerateDevices()
          .then((inputs) => setDevices(inputs.filter((device) => device.kind === "videoinput")))
          .catch(() => setDevices([]));
      } catch (cameraError) {
        setStatus("error");
        const name = cameraError instanceof DOMException ? cameraError.name : "";
        setError(name === "NotAllowedError"
          ? "Camera permission was denied. Allow camera access in your browser, then retry."
          : name === "NotFoundError"
            ? "No camera was found. Connect a camera and retry."
            : cameraError instanceof Error ? cameraError.message : "Could not connect to the camera.");
      }
    })();

    cameraRequestRef.current = { deviceId: requestedDeviceId, promise: request };
    void request.finally(() => {
      if (cameraRequestRef.current?.promise === request) cameraRequestRef.current = null;
    });
    return request;
  }, []);

  useEffect(() => {
    void connectCamera();
    return () => {
      if (!transferredRef.current) streamRef.current?.getTracks().forEach((track) => track.stop());
    };
  }, [attempt, connectCamera, exercise]);

  function continueToWorkout() {
    const stream = streamRef.current;
    if (!stream || stream.getVideoTracks().every((track) => track.readyState !== "live")) return;
    transferredRef.current = true;
    streamRef.current = null;
    onContinue(stream);
  }

  return (
    <main className="camera-page">
      <WorkoutFlowNav user={user} step={2} onDashboard={onDashboard} onSignOut={onSignOut} />
      <section className="camera-content">
        <button type="button" className="btn-ghost flow-back" onClick={onBack}>← Back to exercises</button>
        <div className="section-tag">CAMERA SETUP</div>
        <h1>Check your <em>camera</em></h1>
        <p className="camera-intro">{cameraGuidance}</p>
        <div className="camera-layout">
          <div className="camera-preview">
            <video ref={videoRef} autoPlay muted playsInline aria-label="Live camera preview" />
            {status !== "ready" ? <div className="camera-overlay" role={status === "error" ? "alert" : "status"}>{status === "connecting" ? "Connecting to camera…" : error}</div> : null}
          </div>
          <aside className="camera-details">
            <div className={`camera-status camera-status-${status}`}><span className="dot" />{status === "ready" ? "Camera ready" : status === "connecting" ? "Connecting to camera" : "Camera unavailable"}</div>
            {devices.length > 1 ? (
              <label className="camera-device-label">Camera
                <select value={deviceId} onChange={(event) => void connectCamera(event.target.value)}>
                  {devices.map((device, index) => <option value={device.deviceId} key={device.deviceId}>{device.label || `Camera ${index + 1}`}</option>)}
                </select>
              </label>
            ) : null}
            <div className="camera-note"><strong>Before you continue</strong><p>Keep your full body in view and leave room to move.</p><p>The coach checks your movement after you start.</p></div>
            {status === "error" ? <button type="button" className="btn-ghost" onClick={() => setAttempt((value) => value + 1)}>Retry camera</button> : null}
            <button type="button" className="btn-primary" disabled={status !== "ready"} onClick={continueToWorkout}>Continue <span aria-hidden="true">→</span></button>
          </aside>
        </div>
      </section>
    </main>
  );
}
