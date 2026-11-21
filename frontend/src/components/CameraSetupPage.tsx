import { useCallback, useEffect, useRef, useState } from "react";
import { type AuthUser, type Exercise } from "../services/api";
import WorkoutFlowNav from "./WorkoutFlowNav";
import SquatCameraCheck from "./SquatCameraCheck";

type CameraFacingMode = "user" | "environment";

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
  const cameraRequestRef = useRef<{ deviceId?: string; facingMode: CameraFacingMode; promise: Promise<void> } | null>(null);
  const generation = useRef(0);
  const facingModeRef = useRef<CameraFacingMode>("user");
  const [devices, setDevices] = useState<MediaDeviceInfo[]>([]);
  const [deviceId, setDeviceId] = useState("");
  const [facingMode, setFacingMode] = useState<CameraFacingMode>("user");
  const [status, setStatus] = useState<"connecting" | "ready" | "error">("connecting");
  const [error, setError] = useState("");
  const [attempt, setAttempt] = useState(0);

  const connectCamera = useCallback((requestedDeviceId?: string, requestedFacingMode: CameraFacingMode = facingModeRef.current) => {
    const existingRequest = cameraRequestRef.current;
    if (existingRequest && existingRequest.deviceId === requestedDeviceId && existingRequest.facingMode === requestedFacingMode) return existingRequest.promise;

    const current = ++generation.current;
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
            ...(requestedDeviceId
              ? { deviceId: { exact: requestedDeviceId } }
              : { facingMode: { ideal: requestedFacingMode } }),
            width: { ideal: 640, max: 640 },
            height: { ideal: 480, max: 480 },
            frameRate: { ideal: 30, max: 30 },
          },
          audio: false,
        });
        if (generation.current !== current) {
          stream.getTracks().forEach(track => track.stop());
          return;
        }
        streamRef.current = stream;
        stream.getVideoTracks()[0]?.addEventListener("ended", () => {
          if (generation.current !== current) return;
          setError("Camera disconnected. Reconnect it and retry.");
          setStatus("error");
        }, { once: true });
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
          await videoRef.current.play();
        }
        if (generation.current !== current) return;

        const activeDevice = stream.getVideoTracks()[0]?.getSettings().deviceId ?? requestedDeviceId ?? "";
        setDeviceId(activeDevice);
        const actualFacingMode = stream.getVideoTracks()[0]?.getSettings().facingMode;
        if (actualFacingMode === "user" || actualFacingMode === "environment") {
          facingModeRef.current = actualFacingMode;
          setFacingMode(actualFacingMode);
        }
        setStatus("ready");

        // Device names are useful for the selector, but should not delay the live preview.
        void navigator.mediaDevices.enumerateDevices()
          .then((inputs) => { if (generation.current === current) setDevices(inputs.filter((device) => device.kind === "videoinput")); })
          .catch(() => {});
      } catch (cameraError) {
        if (generation.current !== current) return;
        streamRef.current?.getTracks().forEach(track => track.stop());
        streamRef.current = null;
        setStatus("error");
        const name = cameraError instanceof DOMException ? cameraError.name : "";
        setError(name === "NotAllowedError"
          ? "Camera permission was denied. Allow camera access in your browser, then retry."
          : name === "NotFoundError"
            ? "No camera was found. Connect a camera and retry."
            : cameraError instanceof Error ? cameraError.message : "Could not connect to the camera.");
      }
    })();

    cameraRequestRef.current = { deviceId: requestedDeviceId, facingMode: requestedFacingMode, promise: request };
    void request.finally(() => {
      if (cameraRequestRef.current?.promise === request) cameraRequestRef.current = null;
    });
    return request;
  }, []);

  useEffect(() => {
    void connectCamera();
    return () => {
      generation.current++;
      cameraRequestRef.current = null;
      streamRef.current?.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    };
  }, [attempt, connectCamera, exercise]);

  function continueToWorkout() {
    const stream = streamRef.current;
    if (!stream || stream.getVideoTracks().every((track) => track.readyState !== "live")) return;
    streamRef.current = null;
    onContinue(stream);
  }

  function chooseFacingMode(mode: CameraFacingMode) {
    facingModeRef.current = mode;
    setFacingMode(mode);
    setDeviceId("");
    void connectCamera(undefined, mode);
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
            <div className="camera-facing-controls" role="group" aria-label="Choose front or rear camera">
              <button type="button" className="camera-facing-button" aria-pressed={facingMode === "user"} onClick={() => chooseFacingMode("user")}>Front / selfie</button>
              <button type="button" className="camera-facing-button" aria-pressed={facingMode === "environment"} onClick={() => chooseFacingMode("environment")}>Rear camera</button>
            </div>
            {devices.length > 1 ? (
              <label className="camera-device-label">Camera
                <select value={deviceId} onChange={(event) => void connectCamera(event.target.value, facingModeRef.current)}>
                  {devices.map((device, index) => <option value={device.deviceId} key={device.deviceId}>{`${/front|user|face/i.test(device.label) ? "Selfie" : /back|rear|environment/i.test(device.label) ? "Rear" : "Camera"} ${index + 1}${/ultra.?wide/i.test(device.label) ? " · Ultra-wide" : /telephoto/i.test(device.label) ? " · Telephoto" : /wide/i.test(device.label) ? " · Wide" : ""}`}</option>)}
                </select>
              </label>
            ) : null}
            <div className="camera-note"><strong>Before you continue</strong><p>Keep your full body in view and leave room to move.</p><p>The coach checks your movement after you start.</p></div>
            {exercise === "Squats" && status === "ready" ? <SquatCameraCheck video={videoRef} /> : null}
            {status === "error" ? <button type="button" className="btn-ghost" onClick={() => setAttempt((value) => value + 1)}>Retry camera</button> : null}
            <button type="button" className="btn-primary" disabled={status !== "ready"} onClick={continueToWorkout}>Continue <span aria-hidden="true">→</span></button>
          </aside>
        </div>
      </section>
    </main>
  );
}
