import { FilesetResolver, PoseLandmarker } from "@mediapipe/tasks-vision";

type WorkerRequest =
  | { type: "init" }
  | { type: "dispose" }
  | { type: "frame"; frame: VideoFrame; timestamp: number };

let landmarker: PoseLandmarker | null = null;
let initialization: Promise<void> | null = null;

async function initialize() {
  if (initialization) return initialization;
  initialization = (async () => {
    const files = await FilesetResolver.forVisionTasks(`${self.location.origin}${import.meta.env.BASE_URL}mediapipe/wasm`);
    const options = {
      baseOptions: {
        modelAssetPath: `${self.location.origin}${import.meta.env.BASE_URL}models/pose_landmarker_lite.task`,
        delegate: "GPU" as const,
      },
      runningMode: "VIDEO" as const,
      numPoses: 1,
      minPoseDetectionConfidence: 0.55,
      minPosePresenceConfidence: 0.55,
      minTrackingConfidence: 0.5,
      outputSegmentationMasks: false,
    };
    try {
      landmarker = await PoseLandmarker.createFromOptions(files, options);
    } catch (gpuError) {
      console.warn("Browser GPU pose delegate unavailable; using CPU", gpuError);
      landmarker = await PoseLandmarker.createFromOptions(files, {
        ...options,
        baseOptions: { ...options.baseOptions, delegate: "CPU" },
      });
    }
  })();
  return initialization;
}

self.onmessage = async (event: MessageEvent<WorkerRequest>) => {
  const message = event.data;
  if (message.type === "dispose") {
    landmarker?.close();
    landmarker = null;
    self.close();
    return;
  }
  if (message.type === "init") {
    try {
      await initialize();
      self.postMessage({ type: "ready" });
    } catch (error) {
      initialization = null;
      self.postMessage({
        type: "error",
        message: error instanceof Error ? error.message : "Pose model could not load.",
      });
    }
    return;
  }

  try {
    await initialize();
    const result = landmarker!.detectForVideo(message.frame, message.timestamp);
    const landmarks = result.landmarks[0]?.map(({ x, y, z, visibility }) => ({
      x, y, z, visibility: visibility ?? 0,
    })) ?? null;
    self.postMessage({ type: "pose", landmarks, timestamp: message.timestamp });
  } catch (error) {
    self.postMessage({
      type: "error",
      message: error instanceof Error ? error.message : "Pose tracking failed.",
    });
  } finally {
    message.frame.close();
  }
};
