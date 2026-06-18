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

// Segmentasi gestur kata: buffer frame saat tangan hadir; finalisasi segmen
// setelah jeda (tangan hilang) beberapa frame berturut-turut.
export const SEQ_MIN_FRAMES = 8; // segmen minimal agar dianggap gestur valid
export const SEQ_MAX_FRAMES = 80; // batas atas buffer (cegah segmen kepanjangan)
export const SEQ_GAP_FRAMES = 8; // jumlah frame "kosong" untuk menutup segmen
