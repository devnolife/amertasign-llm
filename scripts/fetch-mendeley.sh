#!/usr/bin/env bash
# Unduh dataset bahasa isyarat publik dari Mendeley Data ke data/public/.
#
# Dataset:
#   1. BISINDO alphabet (gambar A-Z, CC BY 4.0)
#      https://data.mendeley.com/datasets/4xnkvr88tk/1
#      -> data/public/bisindo_mendeley_4xnkvr88tk/
#   2. SIBI Dataset (video sampel + metadata, CC BY 4.0; video lengkap butuh DUA)
#      https://data.mendeley.com/datasets/44pbrbsnkh/3
#      -> data/public/sibi_mendeley_44pbrbsnkh/
#
# Setelah unduh (BISINDO abjad), konversi gambar -> landmark & latih:
#   ./backend/.venv/bin/python scripts/ingest_public.py \
#       --input-dir data/public/bisindo_mendeley_4xnkvr88tk --mode BISINDO --stage abjad
#   ./backend/.venv/bin/python scripts/train.py --mode BISINDO --stage abjad
set -e

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PUBLIC_DIR="$ROOT_DIR/data/public"
DL_DIR="$PUBLIC_DIR/_downloads"

GREEN='\033[0;32m'; CYAN='\033[0;36m'; NC='\033[0m'
log() { echo -e "${CYAN}[mendeley]${NC} $1"; }
ok()  { echo -e "${GREEN}[ok]${NC} $1"; }

# fetch_mendeley <dataset_id> <version> <sha256> <out_dir>
fetch_mendeley() {
  local id="$1" version="$2" sha="$3" out_dir="$4"
  local zip="$DL_DIR/${id}-${version}.zip"
  local url="https://data.mendeley.com/public-api/zip/${id}/download/${version}"

  if [ -d "$out_dir" ] && [ "$(ls -A "$out_dir" 2>/dev/null)" ]; then
    ok "Dataset sudah ada di $out_dir (lewati)."
    return 0
  fi

  mkdir -p "$DL_DIR"
  if [ ! -f "$zip" ] || ! echo "$sha  $zip" | sha256sum -c --quiet - 2>/dev/null; then
    log "Mengunduh $id v$version ..."
    curl -sSL -o "$zip" "$url"
  fi
  log "Verifikasi checksum..."
  echo "$sha  $zip" | sha256sum -c --quiet -

  log "Mengekstrak..."
  local tmp; tmp="$(mktemp -d)"
  unzip -q "$zip" -d "$tmp"
  mkdir -p "$out_dir"
  # Zip Mendeley bisa berisi folder root bertingkat; turunkan sampai isi asli.
  local src="$tmp"
  while [ "$(find "$src" -mindepth 1 -maxdepth 1 | wc -l)" -eq 1 ] && \
        [ -d "$(find "$src" -mindepth 1 -maxdepth 1 -type d | head -1)" ]; do
    src="$(find "$src" -mindepth 1 -maxdepth 1 -type d | head -1)"
  done
  mv "$src"/* "$out_dir/"
  rm -rf "$tmp"
  ok "Selesai: $out_dir"
}

fetch_mendeley 4xnkvr88tk 1 \
  da4d83e3d9a577fef6c4f5fba33315257ecedc613ad4f151c39e6fbd70d9e804 \
  "$PUBLIC_DIR/bisindo_mendeley_4xnkvr88tk"

fetch_mendeley 44pbrbsnkh 3 \
  bbb54570348e662747f3263501320e26b96b8728d6d8451b36f6b91a8a4affd3 \
  "$PUBLIC_DIR/sibi_mendeley_44pbrbsnkh"

echo ""
echo "Langkah berikutnya (BISINDO abjad):"
echo "  ./backend/.venv/bin/python scripts/ingest_public.py --input-dir $PUBLIC_DIR/bisindo_mendeley_4xnkvr88tk --mode BISINDO --stage abjad"
echo "  ./backend/.venv/bin/python scripts/train.py --mode BISINDO --stage abjad"
echo ""
echo "Catatan SIBI: hanya sampel + metadata yang publik; dataset video lengkap"
echo "memerlukan Data Use Agreement (lihat PDF DUA di folder dataset)."
