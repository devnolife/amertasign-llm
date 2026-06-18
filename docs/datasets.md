# Dataset

Proyek ini **tidak menyertakan** data mentah/model (di-`.gitignore` karena besar &
lisensi beragam). Ada dua cara mengisi dataset.

## 1. Dataset publik (otomatis) — BISINDO alfabet

Sumber default: **rhiosutoyo/Indonesian-Sign-Language-BISINDO-Hand-Sign-Detection-Dataset**
(GitHub, **lisensi MIT**) — 520 gambar alfabet **A–Z** (20 per huruf), satu/dua tangan.

```bash
# 1) Unduh gambar ke data/public/bisindo_rhiosutoyo/  (A/, B/, ... Z/)
./scripts/fetch-dataset.sh

# 2) Konversi gambar -> landmark (butuh mediapipe + opencv)
./backend/.venv/bin/pip install -r scripts/requirements-ingest.txt
./backend/.venv/bin/python scripts/ingest_public.py \
    --input-dir data/public/bisindo_rhiosutoyo --mode BISINDO --stage abjad

# 3) Latih model abjad
./backend/.venv/bin/python scripts/train.py --mode BISINDO --stage abjad
```

Hasil acuan pada dataset ini: **511/520** gambar berhasil diekstrak landmark-nya
(9 dilewati karena tangan tak terdeteksi), **26 kelas**, **val accuracy ~0.99**.

> Ekstraksi memakai **MediaPipe Tasks HandLandmarker** (model
> `frontend/public/mediapipe/models/hand_landmarker.task`, di-setup oleh
> `scripts/fetch-assets.sh`) — sama dengan ekstraksi di frontend.

### Sumber publik lain (unduh manual)
Tidak di-otomatiskan karena butuh login / persetujuan (DUA) / API key:

| Dataset | Platform | Cakupan | Akses |
|---|---|---|---|
| Labeled Official SIBI Alphabet (yhsgmynccf) | Mendeley | SIBI A–Z (±31.950 img) | unduh gratis |
| BISINDO Alphabet Image Data (ywnjpbcz8m) | Mendeley | BISINDO A–Z | unduh gratis |
| Bahasa Isyarat Indonesia (BISINDO) Alphabets | Kaggle | BISINDO A–Z | perlu akun |
| BISINDO Dataset (8.700+ img) | Roboflow | isyarat | perlu API key |
| SIBI Video Dataset (44pbrbsnkh) | Mendeley | SIBI kata/kalimat | perlu DUA |

Untuk dataset gambar apa pun, susun jadi folder per-label lalu jalankan
`ingest_public.py --input-dir <folder> --mode SIBI|BISINDO --stage abjad`.

## 2. Rekam sendiri

Gunakan halaman **`/collect`** (Studio data) untuk merekam sampel berlabel langsung
dari webcam — cocok untuk **kata** (urutan) dan kosakata yang tak tersedia di dataset
publik. Lihat README utama.

## Catatan SIBI vs BISINDO

- **SIBI** = *Sistem Isyarat Bahasa Indonesia* (mengikuti tata bahasa Indonesia baku,
  abjad umumnya **satu tangan**).
- **BISINDO** = *Bahasa Isyarat Indonesia* (alami komunitas Tuli, sering **dua tangan**).

Model & label disimpan **terpisah** per mode; jangan mencampur sampel keduanya.

## Atribusi

Bila memakai dataset rhiosutoyo, sertakan atribusi sesuai lisensi MIT repo tersebut:
*Rhio Sutoyo, Indonesian Sign Language (BISINDO) Hand Sign Detection Dataset.*
