#!/usr/bin/env bash
# Dev runner amertasign-llm: backend (FastAPI :8000) + frontend (Next.js :3030).
set -e

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"
LOG_DIR="$ROOT_DIR/.dev-logs"
mkdir -p "$LOG_DIR"

BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_PORT="${FRONTEND_PORT:-3030}"

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; RED='\033[0;31m'; NC='\033[0m'
log()  { echo -e "${CYAN}[dev]${NC} $1"; }
ok()   { echo -e "${GREEN}[ok]${NC} $1"; }
warn() { echo -e "${YELLOW}[warn]${NC} $1"; }
err()  { echo -e "${RED}[err]${NC} $1"; }

is_port_used() { ss -ltn "sport = :$1" 2>/dev/null | grep -q LISTEN; }
find_free_port() {
  local p=$1
  while is_port_used "$p"; do warn "Port $p dipakai, coba $((p+1))..."; p=$((p+1)); done
  echo "$p"
}

BACKEND_PORT="$(find_free_port "$BACKEND_PORT")"
FRONTEND_PORT="$(find_free_port "$FRONTEND_PORT")"

PIDS=()
cleanup() {
  log "Menghentikan proses dev..."
  for pid in "${PIDS[@]}"; do kill "$pid" 2>/dev/null || true; done
}
trap cleanup EXIT INT TERM

# ---------- Backend ----------
if [ ! -d "$BACKEND_DIR/.venv" ]; then
  err "venv backend belum ada. Jalankan ./scripts/setup.sh dulu."; exit 1
fi
log "Backend  → http://localhost:$BACKEND_PORT (docs: /docs)"
( cd "$BACKEND_DIR" && ./.venv/bin/uvicorn app.main:app --reload --port "$BACKEND_PORT" \
    > "$LOG_DIR/backend.log" 2>&1 ) &
PIDS+=($!)

# ---------- Frontend ----------
log "Frontend → http://localhost:$FRONTEND_PORT"
PKG="npm run dev --"
command -v pnpm >/dev/null 2>&1 && PKG="pnpm dev --"
( cd "$FRONTEND_DIR" && \
    NEXT_PUBLIC_API_URL="http://localhost:$BACKEND_PORT" \
    NEXT_PUBLIC_WS_URL="ws://localhost:$BACKEND_PORT" \
    $PKG --port "$FRONTEND_PORT" > "$LOG_DIR/frontend.log" 2>&1 ) &
PIDS+=($!)

ok "Dev berjalan. Log di $LOG_DIR/. Tekan Ctrl+C untuk berhenti."
wait
