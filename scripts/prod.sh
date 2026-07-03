#!/usr/bin/env bash
# Jalankan amertasign-llm dalam MODE PRODUKSI (tanpa Docker), lengkap dgn tunnel.
#
#   ./scripts/prod.sh            # build + start produksi + tunnel publik
#   PUBLIC=0 ./scripts/prod.sh   # lokal saja (tanpa tunnel)
#   SKIP_BUILD=1 ./scripts/prod.sh   # lewati build frontend (pakai .next yg ada)
#
# Beda dari restart.sh (dev):
#   - Backend: uvicorn TANPA --reload, multi-worker (stabil).
#   - Frontend: `next build` lalu `next start` (bukan `next dev`).
#   - NEXT_PUBLIC_* di-bake saat build → build dilakukan SETELAH URL tunnel diketahui.
#   - Data persisten: SQLite data/mobile.db + data/recordings + backend/models (file di host).
set -u

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"

BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_PORT="${FRONTEND_PORT:-3030}"
WORKERS="${WORKERS:-2}"

CF_BIN="${CF_BIN:-$HOME/bin/cloudflared}"
CF_BE_LOG="/tmp/cf-backend.log"
CF_FE_LOG="/tmp/cf-frontend.log"
BE_LOG="/tmp/amerta-backend.log"
FE_LOG="/tmp/amerta-frontend.log"
FE_BUILD_LOG="/tmp/amerta-frontend-build.log"

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; RED='\033[0;31m'; NC='\033[0m'
log()  { echo -e "${CYAN}[run]${NC} $1"; }
ok()   { echo -e "${GREEN}[ok]${NC} $1"; }
warn() { echo -e "${YELLOW}[warn]${NC} $1"; }
err()  { echo -e "${RED}[err]${NC} $1"; }

# pnpm di PATH interaktif user kadang tak ada.
if ! command -v pnpm >/dev/null 2>&1; then
  for d in "$HOME"/.nvm/versions/node/*/bin; do
    [ -x "$d/pnpm" ] && { PATH="$d:$PATH"; break; }
  done
fi
PKG="pnpm"; command -v pnpm >/dev/null 2>&1 || PKG="npm"

get_tunnel_url() { grep -oE 'https://[a-z0-9-]+\.trycloudflare\.com' "$1" 2>/dev/null | head -1; }

wait_http() { local url=$1 n=${2:-60} code; for ((i=0; i<n; i++)); do
  code=$(curl -s -o /dev/null -w '%{http_code}' "$url" 2>/dev/null)
  [ "$code" = "200" ] && return 0; sleep 1; done; return 1; }

# ---------- 1) Stop hanya proses project ini (aman utk project lain) ----------
log "Menghentikan proses lama (backend/frontend project ini)..."
for pid in $(pgrep -f 'uvicorn|next|pnpm|node' 2>/dev/null); do
  cwd=$(readlink "/proc/$pid/cwd" 2>/dev/null) || continue
  case "$cwd" in "$BACKEND_DIR"|"$FRONTEND_DIR") kill "$pid" 2>/dev/null ;; esac
done
sleep 2

# ---------- 2) Tunnel publik (reuse bila masih hidup) ----------
ensure_tunnel() { local port=$1 logf=$2 label=$3
  if pgrep -f "cloudflared tunnel --url http://localhost:$port" >/dev/null 2>&1; then
    log "Tunnel $label masih hidup (URL tetap)."; return 0; fi
  [ -x "$CF_BIN" ] || { warn "cloudflared tidak ada di $CF_BIN — lewati tunnel $label."; return 1; }
  log "Menjalankan tunnel $label baru..."
  nohup "$CF_BIN" tunnel --url "http://localhost:$port" --no-autoupdate > "$logf" 2>&1 &
  for ((i=0; i<30; i++)); do [ -n "$(get_tunnel_url "$logf")" ] && break; sleep 1; done
}

BE_URL=""; FE_URL=""
if [ "${PUBLIC:-1}" = "1" ]; then
  ensure_tunnel "$BACKEND_PORT"  "$CF_BE_LOG" "backend"  || true
  ensure_tunnel "$FRONTEND_PORT" "$CF_FE_LOG" "frontend" || true
  BE_URL="$(get_tunnel_url "$CF_BE_LOG")"
  FE_URL="$(get_tunnel_url "$CF_FE_LOG")"
fi
if [ -n "$BE_URL" ]; then
  API_URL="$BE_URL"; WS_URL="wss://${BE_URL#https://}"
else
  API_URL="http://localhost:$BACKEND_PORT"; WS_URL="ws://localhost:$BACKEND_PORT"
fi

# ---------- 3) Backend (produksi: tanpa --reload, multi-worker) ----------
[ -d "$BACKEND_DIR/.venv" ] || { err "venv backend belum ada. Jalankan ./scripts/setup.sh dulu."; exit 1; }
log "Start backend (produksi, $WORKERS worker) → http://localhost:$BACKEND_PORT"
( cd "$BACKEND_DIR" && nohup ./.venv/bin/uvicorn app.main:app \
    --host 127.0.0.1 --port "$BACKEND_PORT" --workers "$WORKERS" \
    > "$BE_LOG" 2>&1 & )
if wait_http "http://localhost:$BACKEND_PORT/health" 60; then ok "Backend siap (/health 200)"; else
  err "Backend gagal start. Cek log: $BE_LOG"; exit 1; fi

# ---------- 4) Frontend (produksi: build standalone lalu jalankan server.js) ----------
if [ "${SKIP_BUILD:-0}" != "1" ]; then
  log "Build frontend (API di-bake: $API_URL) — lihat $FE_BUILD_LOG"
  if ! ( cd "$FRONTEND_DIR" && NEXT_PUBLIC_API_URL="$API_URL" NEXT_PUBLIC_WS_URL="$WS_URL" \
        $PKG run build > "$FE_BUILD_LOG" 2>&1 ); then
    err "Build frontend gagal. Cek log: $FE_BUILD_LOG"; exit 1; fi
  ok "Build frontend selesai."
fi

# output:standalone tidak menyalin public/ & static/ otomatis → salin manual.
if [ -f "$FRONTEND_DIR/.next/standalone/server.js" ]; then
  cp -r "$FRONTEND_DIR/public" "$FRONTEND_DIR/.next/standalone/" 2>/dev/null || true
  mkdir -p "$FRONTEND_DIR/.next/standalone/.next"
  cp -r "$FRONTEND_DIR/.next/static" "$FRONTEND_DIR/.next/standalone/.next/" 2>/dev/null || true
  log "Start frontend (standalone server.js) → http://localhost:$FRONTEND_PORT"
  ( cd "$FRONTEND_DIR/.next/standalone" && \
      HOSTNAME=127.0.0.1 PORT="$FRONTEND_PORT" nohup node server.js > "$FE_LOG" 2>&1 & )
else
  warn "Artefak standalone tak ada — fallback ke 'next start'."
  ( cd "$FRONTEND_DIR" && NEXT_PUBLIC_API_URL="$API_URL" NEXT_PUBLIC_WS_URL="$WS_URL" \
      nohup $PKG run start > "$FE_LOG" 2>&1 & )
fi
if wait_http "http://localhost:$FRONTEND_PORT" 60; then ok "Frontend siap (:$FRONTEND_PORT 200)"; else
  err "Frontend gagal start. Cek log: $FE_LOG"; exit 1; fi

# ---------- 5) Ringkasan ----------
echo
ok "amertasign-llm berjalan (MODE PRODUKSI)."
echo -e "  Lokal    : http://localhost:$FRONTEND_PORT"
if [ -n "$FE_URL" ]; then
  echo -e "  Web      : ${GREEN}$FE_URL${NC}"
  echo -e "  API      : ${GREEN}$API_URL/api/v1${NC}   <-- base URL utk Expo"
else
  echo -e "  API      : $API_URL/api/v1   <-- base URL utk Expo"
  warn "Tanpa URL publik (PUBLIC=0 atau cloudflared tak tersedia)."
fi
echo -e "  Data     : data/mobile.db (auth) · data/recordings (ML) · backend/models"
echo -e "  Log      : $BE_LOG , $FE_LOG , $FE_BUILD_LOG"
