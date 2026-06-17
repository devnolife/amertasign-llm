// Konfigurasi runtime frontend.
// URL backend bisa dioverride lewat env NEXT_PUBLIC_API_URL / NEXT_PUBLIC_WS_URL
// (di-inject oleh scripts/dev.sh). Default menunjuk ke backend dev lokal.

export const API_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export const WS_URL = process.env.NEXT_PUBLIC_WS_URL ?? "ws://localhost:8000";

// Aset MediaPipe di-host lokal dari /public (offline-friendly & privasi).
export const ASSETS = {
  wasmPath: "/mediapipe/wasm",
  handModelPath: "/mediapipe/models/hand_landmarker.task",
} as const;

// Throttle pengiriman frame ke backend (ms). ~15 fps cukup untuk pengenalan.
export const SEND_INTERVAL_MS = 66;
