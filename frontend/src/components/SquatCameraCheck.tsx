import { useRef, useState, type RefObject } from "react";
import { SquatDetector } from "../vision/squat";
import { usePoseCamera } from "../vision/usePoseCamera";

export default function SquatCameraCheck({ video }: { video: RefObject<HTMLVideoElement> }) {
  const [enabled, setEnabled] = useState(false);
  const [feedback, setFeedback] = useState("");
  const detector = useRef(new SquatDetector());
  usePoseCamera(video, enabled, pose => {
    if (!pose) { setFeedback("Step back until your full body is visible."); return; }
    const result = detector.current.process(pose);
    setFeedback(result.landmarks_visible
      ? `Practice reps: ${result.reps}. ${result.form_issue || result.exercise_stage}`
      : "Move back until your hip, knee and ankle are visible on the same side.");
  }, () => {
    setFeedback("This browser could not run the local tracking check.");
    setEnabled(false);
  });
  return <div className="camera-note">
    <button className="btn-ghost" type="button" onClick={() => {
      setFeedback(enabled ? "" : "Loading the squat model…");
      detector.current = new SquatDetector();
      setEnabled(!enabled);
    }}>{enabled ? "Stop practice" : "Test squats on this device"}</button>
    <p>Practice uses this camera on your device. Practice reps are unsaved.</p>
    <p role="status">{feedback}</p>
  </div>;
}
