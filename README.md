# amertasign-llm

Web app **pengenalan bahasa isyarat Indonesia real-time** berbasis kamera untuk
**BISINDO** dan **SIBI**. Webcam menangkap gestur tangan → sistem menampilkan teksnya.

Dikembangkan **bertahap**:
1. **Abjad / fingerspelling** (A–Z, angka) — gestur statis.
2. **Kata / kosakata** — gestur dinamis.
3. **Kalimat kontinu** — rangkaian isyarat → gloss → dirapikan **LLM** jadi kalimat natural.

> Catatan: **SIBI** di sini = *Sistem Isyarat Bahasa Indonesia* (bahasa isyarat),
> berbeda dari SIBI buku sekolah.

## Arsitektur

```
Browser (Next.js)                         Backend (FastAPI / Python)
  webcam + MediaPipe HandLandmarker  ──landmark──▶  normalisasi → model → teks
  (ekstraksi 21 titik/tangan)        ◀──teks───   /recognize, /ws/recognize
```

- **Ekstraksi landmark di browser** → latency rendah, video mentah tak dikirim.
- BISINDO: 2 tangan; SIBI (abjad): 1 tangan. Model & label **terpisah** per mode.

## Struktur

```
amertasign-llm/
├── frontend/   # Next.js + TypeScript + Tailwind (webcam, MediaPipe, UI)
├── backend/    # FastAPI: recognize, collect, train, compose; ml/, llm/
├── ml/         # skrip training (abjad/kata), ingest dataset publik
├── data/       # (gitignored) rekaman + dataset publik
├── scripts/    # dev runner & setup
└── docs/       # kontrak API, skema landmark
```

## Quick start

```bash
# 1) Install dependency (frontend + backend venv)
./scripts/setup.sh

# 2) Jalankan dev (backend :8000 + frontend :3030)
./scripts/dev.sh
```

Lalu buka http://localhost:3030

### Dataset (BISINDO alfabet, otomatis)

Belum ada data bawaan. Untuk langsung punya model abjad BISINDO dari dataset publik
**MIT** (511 sampel, val acc ~99%):

```bash
./scripts/fetch-dataset.sh                                   # unduh gambar A-Z (MIT)
./backend/.venv/bin/pip install -r scripts/requirements-ingest.txt
./backend/.venv/bin/python scripts/ingest_public.py \
    --input-dir data/public/bisindo_rhiosutoyo --mode BISINDO --stage abjad
./backend/.venv/bin/python scripts/train.py --mode BISINDO --stage abjad
```

Dataset tambahan dari **Mendeley Data** (CC BY 4.0):

```bash
./scripts/fetch-mendeley.sh
```

- **BISINDO alphabet** ([4xnkvr88tk v1](https://data.mendeley.com/datasets/4xnkvr88tk/1)) —
  ±8.000 gambar A–Z (kamera fisheye, 7 partisipan) → `data/public/bisindo_mendeley_4xnkvr88tk/`.
  Hasil ingest: ±5.760 sampel landmark. Digabung dataset MIT, training model abjad
  mencapai val acc ~97% pada domain webcam biasa (split temporal per label).
- **SIBI Dataset** ([44pbrbsnkh v3](https://data.mendeley.com/datasets/44pbrbsnkh/3)) —
  video sampel (abjad, angka, imbuhan, kalimat) + metadata CSV →
  `data/public/sibi_mendeley_44pbrbsnkh/`. Video lengkap memerlukan
  Data Use Agreement (PDF DUA ada di folder dataset).

### Dataset kata (video → urutan landmark)

Video gestur dinamis di-ingest dengan `scripts/ingest_video.py`
(struktur input: subfolder per label berisi video):

```bash
./backend/.venv/bin/python scripts/ingest_video.py \
    --input-dir data/public/sibi_mendeley_44pbrbsnkh/sibi-dataset-dib-example-face-blurred/number \
    --mode SIBI --stage kata
./backend/.venv/bin/python scripts/train.py --mode SIBI --stage kata
```

Sampel SIBI Mendeley hanya berisi **1 video per label (1 signer)** — cukup untuk
menguji pipeline end-to-end (model `SIBI_kata.joblib` = demo/seed), tetapi belum
memadai untuk model produksi. Untuk data kata yang layak: ajukan DUA dataset SIBI
lengkap (20 signer) lalu ingest folder videonya, dan/atau rekam sendiri via `/collect`.

Atau rekam sendiri (terutama untuk **kata**) via halaman `/collect`.
Detail & sumber lain: lihat `docs/datasets.md`.

### Atau dengan Docker

```bash
docker compose up --build
```

Lihat `DEPLOYMENT.md` untuk detail (HTTPS/kamera, domain, LLM, model).

## Tes

```bash
cd backend && pytest               # tes pipeline fitur & API
cd frontend && pnpm lint && pnpm build
```

## Status pengembangan

| Fase | Deskripsi                              | Status   |
|------|----------------------------------------|----------|
| 0    | Scaffolding & infra                    | ✅ selesai |
| 1    | Pipeline landmark real-time            | ✅ selesai |
| 2    | Tools perekaman data + dataset publik  | ✅ selesai |
| 3    | Pengenalan abjad                       | ✅ selesai |
| 4    | Pengenalan kata                        | ✅ selesai |
| 5    | Kalimat kontinu + LLM                  | ✅ selesai |
| 6    | Polish, evaluasi, deploy               | ✅ selesai |

## Halaman

- `/` — Pengenalan isyarat real-time (webcam → teks).
- `/collect` — Studio data: rekam sampel berlabel & latih model abjad.

Lihat `docs/` untuk detail kontrak data & API.
