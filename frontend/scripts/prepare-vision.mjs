import { copyFile, mkdir, readdir } from "node:fs/promises";

const target = new URL("../public/vision/", import.meta.url);
const wasm = new URL("../node_modules/@mediapipe/tasks-vision/wasm/", import.meta.url);
await mkdir(target, { recursive: true });
for (const name of await readdir(wasm)) {
  await copyFile(new URL(name, wasm), new URL(name, target));
}
await copyFile(new URL("../../backend/ml_models/pose_landmarker_full.task", import.meta.url),
  new URL("pose_landmarker_full.task", target));
await copyFile(new URL("../../backend/ml_models/pose_landmarker_lite.task", import.meta.url),
  new URL("pose_landmarker_lite.task", target));
