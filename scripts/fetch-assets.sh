#!/usr/bin/env bash
# Menyiapkan aset MediaPipe yang di-host lokal (WASM + model hand_landmarker)
# ke frontend/public/mediapipe/. Dipanggil oleh setup.sh; aman diulang.
set -e

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FRONTEND_DIR="$ROOT_DIR/frontend"
WASM_SRC="$FRONTEND_DIR/node_modules/@mediapipe/tasks-vision/wasm"
WASM_DST="$FRONTEND_DIR/public/mediapipe/wasm"
MODEL_DST="$FRONTEND_DIR/public/mediapipe/models"
MODEL_URL="https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task"

mkdir -p "$WASM_DST" "$MODEL_DST"

if [ -d "$WASM_SRC" ]; then
  cp -f "$WASM_SRC"/* "$WASM_DST"/
  echo "[assets] WASM disalin dari node_modules."
else
  echo "[assets] WASM source belum ada — jalankan 'pnpm install' di frontend dulu." >&2
fi

if [ ! -f "$MODEL_DST/hand_landmarker.task" ]; then
  echo "[assets] Mengunduh hand_landmarker.task..."
  curl -sSL -o "$MODEL_DST/hand_landmarker.task" "$MODEL_URL"
fi
echo "[assets] Selesai."
