import { useEffect, useRef, type RefObject } from "react";
import type { PoseLandmarker } from "@mediapipe/tasks-vision";
import type { Joint } from "./squat";

export function usePoseCamera(video: RefObject<HTMLVideoElement>, enabled: boolean,
  onFrame: (pose: Joint[] | undefined, mediaTime: number) => void, onError: () => void, onTiming?: (start: number, inferenceMs: number, mediaTime: number) => void, onReady?: () => void,
  model: "full" | "lite" = "full", delegate: "CPU" | "GPU" = "CPU") {
  const callbacks = useRef({ onFrame, onError, onTiming, onReady });
  useEffect(() => { callbacks.current = { onFrame, onError, onTiming, onReady }; }, [onFrame, onError, onTiming, onReady]);
  useEffect(() => {
    if (!enabled) return;
    let disposed = false;
    let timer = 0;
    let frameCallback = 0;
    const element = video.current;
    let task: PoseLandmarker | undefined;
    async function run() {
      try {
        const { FilesetResolver, PoseLandmarker } = await import("@mediapipe/tasks-vision");
        const assets = new URL(import.meta.env.BASE_URL + "vision/", document.baseURI);
        const files = await FilesetResolver.forVisionTasks(assets.href.replace(/\/$/, ""));
        if (disposed) return;
        task = await PoseLandmarker.createFromOptions(files, {
          baseOptions: { modelAssetPath: new URL(`pose_landmarker_${model}.task`, assets).href, delegate },
          runningMode: "VIDEO", minPoseDetectionConfidence: 0.7, minPosePresenceConfidence: 0.7,
          minTrackingConfidence: 0.7, numPoses: 1,
        });
        if (disposed) { task.close(); return; }
        callbacks.current.onReady?.();
        let lastFrame = -1;
        let nextDue = 0;
        function schedule() {
          if (disposed) return;
          if (element && typeof element.requestVideoFrameCallback === "function") {
            frameCallback = element.requestVideoFrameCallback((_now, frame) => tick(frame.presentedFrames, frame.mediaTime));
          } else {
            timer = window.setTimeout(() => {
              const presented = element?.getVideoPlaybackQuality?.().totalVideoFrames;
              tick(presented || element?.currentTime || 0, element?.currentTime ?? 0);
            }, Math.max(10, nextDue - performance.now()));
          }
        }
        function tick(frame: number, mediaTime: number) {
          if (disposed) return;
          try {
            const start = performance.now();
            if (!document.hidden && element && element.readyState >= 2 && frame !== lastFrame && start >= nextDue) {
              lastFrame = frame;
              nextDue = Math.max(start, (nextDue || start) + 80);
              const pose = task!.detectForVideo(element, start).landmarks[0];
              const ms = performance.now() - start;
              callbacks.current.onFrame(pose, mediaTime);
              callbacks.current.onTiming?.(start, ms, mediaTime);
            }
            schedule();
          } catch { callbacks.current.onError(); }
        }
        schedule();
      } catch { if (!disposed) callbacks.current.onError(); }
    }
    void run();
    return () => { disposed = true; clearTimeout(timer);
      if (frameCallback) element?.cancelVideoFrameCallback(frameCallback);
      task?.close(); };
  }, [enabled, video, model, delegate]);
}
