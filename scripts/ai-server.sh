#!/usr/bin/env bash
# Server AI amertasign — jalankan backend FastAPI + tunnel domain tetap.
#
#   ./scripts/ai-server.sh          # restart backend (port 8010) + tunnel domain
#   PUBLIC=0 ./scripts/ai-server.sh # backend lokal saja
#
# Server ini KHUSUS AI/backend. Next.js & APK Android di-deploy terpisah dan
# mengakses API lewat https://amertasign.lab-if.tech.
#
# Tunnel domain memakai Cloudflare NAMED TUNNEL (bukan quick tunnel) sehingga
# URL tidak berubah-ubah. Sekali saja, siapkan token:
#   1. Pindahkan DNS lab-if.tech ke Cloudflare (gratis) bila belum.
#   2. Zero Trust → Networks → Tunnels → Create tunnel (Cloudflared).
#   3. Tambahkan Public Hostname: amertasign.lab-if.tech → http://localhost:8010
#   4. Salin token tunnel, simpan:  echo 'TOKEN' > ~/.cloudflared/amertasign.token
set -u

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
PORT="${BACKEND_PORT:-8010}"
WORKERS="${WORKERS:-2}"
DOMAIN="amertasign.lab-if.tech"
TOKEN_FILE="${CF_TOKEN_FILE:-$HOME/.cloudflared/amertasign.token}"
CF_BIN="${CF_BIN:-$HOME/bin/cloudflared}"
BE_LOG="/tmp/amerta-ai-backend.log"
CF_LOG="/tmp/cf-amertasign-domain.log"

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'
log()  { echo -e "${CYAN}[ai]${NC} $1"; }
ok()   { echo -e "${GREEN}[ok]${NC} $1"; }
warn() { echo -e "${YELLOW}[warn]${NC} $1"; }

# ---------- 1) Restart backend milik project ini saja ----------
log "Menghentikan backend lama..."
for pid in $(pgrep -f 'uvicorn' 2>/dev/null); do
  cwd=$(readlink "/proc/$pid/cwd" 2>/dev/null) || continue
  [ "$cwd" = "$BACKEND_DIR" ] && kill "$pid" 2>/dev/null
done
sleep 2

log "Menjalankan backend produksi di 127.0.0.1:$PORT ($WORKERS worker)..."
cd "$BACKEND_DIR"
nohup .venv/bin/uvicorn app.main:app \
  --host 127.0.0.1 --port "$PORT" --workers "$WORKERS" \
  > "$BE_LOG" 2>&1 &

for _ in $(seq 1 30); do
  code=$(curl -s -o /dev/null -w '%{http_code}' "http://localhost:$PORT/health" 2>/dev/null)
  [ "$code" = "200" ] && break
  sleep 1
done
[ "${code:-}" = "200" ] && ok "Backend sehat: http://localhost:$PORT/health" \
  || { warn "Backend belum merespons — cek $BE_LOG"; exit 1; }

[ "${PUBLIC:-1}" = "0" ] && { ok "Mode lokal (PUBLIC=0) — selesai."; exit 0; }

# ---------- 2) Tunnel domain tetap ----------
if [ ! -s "$TOKEN_FILE" ]; then
  warn "Token tunnel belum ada di $TOKEN_FILE."
  warn "Ikuti langkah di header skrip ini, lalu jalankan ulang."
  warn "Sementara itu backend tetap bisa diakses via quick tunnel yang ada."
  exit 0
fi

if pgrep -f "cloudflared tunnel run --token" >/dev/null 2>&1; then
  ok "Tunnel domain sudah berjalan."
else
  log "Menjalankan tunnel $DOMAIN → localhost:$PORT ..."
  nohup "$CF_BIN" tunnel run --token "$(cat "$TOKEN_FILE")" > "$CF_LOG" 2>&1 &
  sleep 3
fi

code=$(curl -s -o /dev/null -w '%{http_code}' "https://$DOMAIN/health" 2>/dev/null)
if [ "$code" = "200" ]; then
  ok "API publik siap: https://$DOMAIN"
else
  warn "https://$DOMAIN belum merespons (DNS/token belum siap?) — cek $CF_LOG"
fi
