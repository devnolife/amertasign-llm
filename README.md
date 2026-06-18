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

# 2) Jalankan dev (backend :8000 + frontend :3000)
./scripts/dev.sh
```

Lalu buka http://localhost:3000

## Status pengembangan

| Fase | Deskripsi                              | Status   |
|------|----------------------------------------|----------|
| 0    | Scaffolding & infra                    | ✅ selesai |
| 1    | Pipeline landmark real-time            | ✅ selesai |
| 2    | Tools perekaman data + dataset publik  | ✅ selesai |
| 3    | Pengenalan abjad                       | ✅ selesai |
| 4    | Pengenalan kata                        | ✅ selesai |
| 5    | Kalimat kontinu + LLM                  | ✅ selesai |
| 6    | Polish, evaluasi, deploy               | berikutnya |

## Halaman

- `/` — Pengenalan isyarat real-time (webcam → teks).
- `/collect` — Studio data: rekam sampel berlabel & latih model abjad.

Lihat `docs/` untuk detail kontrak data & API.
