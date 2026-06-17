// Setup MediaPipe HandLandmarker (berjalan di browser via WASM) dan helper
// pemetaan hasil deteksi ke skema HandLandmarks milik kita.

import {
  FilesetResolver,
  HandLandmarker,
  type HandLandmarkerResult,
} from "@mediapipe/tasks-vision";

import { ASSETS } from "./config";
import type { Handedness, HandLandmarks } from "./types";

let visionFilesetPromise: ReturnType<typeof FilesetResolver.forVisionTasks> | null =
  null;

function getVisionFileset() {
  if (!visionFilesetPromise) {
    visionFilesetPromise = FilesetResolver.forVisionTasks(ASSETS.wasmPath);
  }
  return visionFilesetPromise;
}

// numHands=2 agar BISINDO (dua tangan) tertangani; SIBI cukup memakai salah satu.
export async function createHandLandmarker(
  numHands = 2,
  delegate: "GPU" | "CPU" = "GPU",
): Promise<HandLandmarker> {
  const vision = await getVisionFileset();
  return HandLandmarker.createFromOptions(vision, {
    baseOptions: {
      modelAssetPath: ASSETS.handModelPath,
      delegate,
    },
    runningMode: "VIDEO",
    numHands,
  });
}

// Konektivitas titik untuk menggambar kerangka tangan.
export const HAND_CONNECTIONS = HandLandmarker.HAND_CONNECTIONS;

export function toHandLandmarks(result: HandLandmarkerResult): HandLandmarks[] {
  return result.landmarks.map((points, i) => {
    const category = result.handedness[i]?.[0];
    return {
      handedness: (category?.categoryName as Handedness) ?? "Right",
      score: category?.score ?? 1,
      landmarks: points.map((p) => ({ x: p.x, y: p.y, z: p.z ?? 0 })),
    };
  });
}
