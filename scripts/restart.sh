#!/usr/bin/env bash
# Jalankan ulang amertasign-llm (backend :8000 + frontend :3030) + tunnel publik.
#
# Pemakaian:
#   ./scripts/restart.sh           # restart + tunnel publik (URL tetap sama bila tunnel masih hidup)
#   PUBLIC=0 ./scripts/restart.sh  # restart lokal saja, tanpa tunnel
#
# Catatan: tunnel cloudflared sengaja TIDAK dimatikan saat restart, sehingga
# URL https://*.trycloudflare.com tetap sama. URL baru hanya muncul bila tunnel
# benar-benar mati lalu dijalankan ulang.
set -u

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"

BACKEND_PORT="${BACKEND_PORT:-8000}"   # harus sama dgn yg dipakai tunnel backend
FRONTEND_PORT="${FRONTEND_PORT:-3030}" # harus sama dgn "next dev -p" di package.json

CF_BIN="${CF_BIN:-$HOME/bin/cloudflared}"
CF_BE_LOG="/tmp/cf-backend.log"
CF_FE_LOG="/tmp/cf-frontend.log"
BE_LOG="/tmp/amerta-backend.log"
FE_LOG="/tmp/amerta-frontend.log"

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; RED='\033[0;31m'; NC='\033[0m'
log()  { echo -e "${CYAN}[run]${NC} $1"; }
ok()   { echo -e "${GREEN}[ok]${NC} $1"; }
warn() { echo -e "${YELLOW}[warn]${NC} $1"; }
err()  { echo -e "${RED}[err]${NC} $1"; }

# --- pastikan pnpm tersedia (PATH user interaktif kadang tak punya pnpm) ---
if ! command -v pnpm >/dev/null 2>&1; then
  for d in "$HOME"/.nvm/versions/node/*/bin; do
    [ -x "$d/pnpm" ] && { PATH="$d:$PATH"; break; }
  done
fi
PKG="npm run dev"
command -v pnpm >/dev/null 2>&1 && PKG="pnpm dev"

get_tunnel_url() { grep -oE 'https://[a-z0-9-]+\.trycloudflare\.com' "$1" 2>/dev/null | head -1; }

wait_http() { # url retries
  local url=$1 n=${2:-40} code
  for ((i=0; i<n; i++)); do
    code=$(curl -s -o /dev/null -w '%{http_code}' "$url" 2>/dev/null)
    [ "$code" = "200" ] && return 0
    sleep 1
  done
  return 1
}

# ---------- 1) Stop hanya proses project ini (match by cwd, aman utk project lain) ----------
log "Menghentikan backend & frontend lama..."
for pid in $(pgrep -f 'uvicorn|next|pnpm|node' 2>/dev/null); do
  cwd=$(readlink "/proc/$pid/cwd" 2>/dev/null) || continue
  case "$cwd" in
    "$BACKEND_DIR"|"$FRONTEND_DIR") kill "$pid" 2>/dev/null ;;
  esac
done
sleep 2

# ---------- 2) Tunnel publik (reuse bila masih hidup) ----------
ensure_tunnel() { # port logfile label
  local port=$1 logf=$2 label=$3
  if pgrep -f "cloudflared tunnel --url http://localhost:$port" >/dev/null 2>&1; then
    log "Tunnel $label masih hidup (URL tetap)."
    return 0
  fi
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

# ---------- 3) Backend ----------
[ -d "$BACKEND_DIR/.venv" ] || { err "venv backend belum ada. Jalankan ./scripts/setup.sh dulu."; exit 1; }
log "Start backend → http://localhost:$BACKEND_PORT"
( cd "$BACKEND_DIR" && nohup ./.venv/bin/uvicorn app.main:app --reload --port "$BACKEND_PORT" > "$BE_LOG" 2>&1 & )
if wait_http "http://localhost:$BACKEND_PORT/health" 40; then ok "Backend siap (/health 200)"; else
  err "Backend gagal start. Cek log: $BE_LOG"; exit 1; fi

# ---------- 4) Frontend ----------
log "Start frontend → http://localhost:$FRONTEND_PORT  (API: $API_URL)"
( cd "$FRONTEND_DIR" && NEXT_PUBLIC_API_URL="$API_URL" NEXT_PUBLIC_WS_URL="$WS_URL" \
    nohup $PKG > "$FE_LOG" 2>&1 & )
if wait_http "http://localhost:$FRONTEND_PORT" 40; then ok "Frontend siap (:$FRONTEND_PORT 200)"; else
  err "Frontend gagal start. Cek log: $FE_LOG"; exit 1; fi

# ---------- 5) Ringkasan ----------
echo
ok "amertasign-llm berjalan."
echo -e "  Lokal    : http://localhost:$FRONTEND_PORT"
if [ -n "$FE_URL" ]; then
  echo -e "  Publik   : ${GREEN}$FE_URL${NC}   <-- bagikan ini"
  echo -e "  Backend  : $BE_URL"
else
  warn "Tanpa URL publik (PUBLIC=0 atau cloudflared tidak tersedia)."
fi
echo -e "  Log      : $BE_LOG , $FE_LOG"
