# amertasign-llm — backend (FastAPI)

Service pengenalan isyarat: menerima landmark tangan dari frontend (MediaPipe) dan
mengembalikan teks hasil pengenalan.

## Menjalankan

```bash
cd backend
uv venv && source .venv/bin/activate    # atau: python3 -m venv .venv && source .venv/bin/activate
uv pip install -r requirements.txt       # atau: pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Buka dokumentasi interaktif di http://localhost:8000/docs

## Endpoint

| Method | Path             | Fungsi                                            |
|--------|------------------|---------------------------------------------------|
| GET    | `/health`        | Status + daftar model tersedia                    |
| POST   | `/recognize`     | Kenali 1 frame landmark (gestur statis / abjad)   |
| WS     | `/ws/recognize`  | Streaming: kirim FramePayload, terima hasil       |

Lihat `../docs/api-contract.md` dan `../docs/landmark-schema.md` untuk kontrak data.

## Struktur

```
app/
├── main.py            # entry FastAPI + CORS
├── config.py          # settings (env AMERTASIGN_*)
├── schemas/           # Pydantic: landmark & hasil
├── ml/
│   ├── normalize.py   # landmark -> vektor fitur (invarian translasi/skala)
│   └── registry.py    # load model per (mode, stage) + prediksi
├── routers/           # health, recognize (HTTP + WS)
└── llm/               # gloss -> kalimat (Fase 5)
```
