#!/usr/bin/env bash
# Unduh dataset bahasa isyarat publik (lisensi jelas) ke data/public/.
#
# Default: BISINDO alfabet A-Z (520 gambar, 20/huruf) dari repo MIT:
#   rhiosutoyo/Indonesian-Sign-Language-BISINDO-Hand-Sign-Detection-Dataset
#
# Setelah unduh, konversi gambar -> landmark & latih:
#   ./backend/.venv/bin/python scripts/ingest_public.py \
#       --input-dir data/public/bisindo_rhiosutoyo --mode BISINDO --stage abjad
#   ./backend/.venv/bin/python scripts/train.py --mode BISINDO --stage abjad
set -e

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT_DIR="$ROOT_DIR/data/public/bisindo_rhiosutoyo"
TMP_ZIP="$(mktemp /tmp/bisindo-XXXX.zip)"
ZIP_URL="https://codeload.github.com/rhiosutoyo/Indonesian-Sign-Language-BISINDO-Hand-Sign-Detection-Dataset/zip/refs/heads/master"

GREEN='\033[0;32m'; CYAN='\033[0;36m'; NC='\033[0m'
log() { echo -e "${CYAN}[dataset]${NC} $1"; }
ok()  { echo -e "${GREEN}[ok]${NC} $1"; }

if [ -d "$OUT_DIR" ] && [ "$(ls -A "$OUT_DIR" 2>/dev/null)" ]; then
  ok "Dataset sudah ada di $OUT_DIR (lewati unduh)."
  exit 0
fi

log "Mengunduh BISINDO alphabet (MIT, rhiosutoyo)..."
curl -sSL -o "$TMP_ZIP" "$ZIP_URL"

log "Mengekstrak..."
TMP_DIR="$(mktemp -d)"
unzip -q "$TMP_ZIP" -d "$TMP_DIR"
SRC="$(find "$TMP_DIR" -type d -name collectedimages | head -1)"
if [ -z "$SRC" ]; then
  echo "Gagal menemukan folder collectedimages dalam arsip." >&2
  exit 1
fi

mkdir -p "$OUT_DIR"
cp -r "$SRC/." "$OUT_DIR/"
rm -rf "$TMP_DIR" "$TMP_ZIP"

COUNT="$(find "$OUT_DIR" -type f -iname '*.jpg' | wc -l | tr -d ' ')"
ok "Selesai: $COUNT gambar di $OUT_DIR (A-Z)."
echo ""
echo "Langkah berikutnya:"
echo "  ./backend/.venv/bin/python scripts/ingest_public.py --input-dir $OUT_DIR --mode BISINDO --stage abjad"
echo "  ./backend/.venv/bin/python scripts/train.py --mode BISINDO --stage abjad"
