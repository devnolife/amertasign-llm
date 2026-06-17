#!/usr/bin/env bash
# Setup dependency amertasign-llm: backend (venv + pip) & frontend (pnpm).
set -e

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
GREEN='\033[0;32m'; CYAN='\033[0;36m'; NC='\033[0m'
log() { echo -e "${CYAN}[setup]${NC} $1"; }
ok()  { echo -e "${GREEN}[ok]${NC} $1"; }

# ---------- Backend ----------
log "Menyiapkan backend (Python venv)..."
cd "$ROOT_DIR/backend"
if command -v uv >/dev/null 2>&1; then
  uv venv --python 3.10 .venv 2>/dev/null || uv venv .venv
  uv pip install --python .venv/bin/python -r requirements.txt
else
  python3 -m venv .venv
  ./.venv/bin/pip install --upgrade pip
  ./.venv/bin/pip install -r requirements.txt
fi
ok "Backend siap."

# ---------- Frontend ----------
log "Menyiapkan frontend (pnpm)..."
cd "$ROOT_DIR/frontend"
if command -v pnpm >/dev/null 2>&1; then
  pnpm install
else
  npm install
fi
ok "Frontend siap."

# ---------- Aset MediaPipe (WASM + model) ----------
log "Menyiapkan aset MediaPipe..."
bash "$ROOT_DIR/scripts/fetch-assets.sh"
ok "Aset MediaPipe siap."

ok "Setup selesai. Jalankan: ./scripts/dev.sh"
