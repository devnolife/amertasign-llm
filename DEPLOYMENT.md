# Deployment — amertasign-llm

Dua layanan: **backend** (FastAPI, port 8000) dan **frontend** (Next.js, port 3030).

## Opsi 1 — Docker Compose (disarankan)

```bash
docker compose up --build
```

- Frontend: http://localhost:3030
- Backend:  http://localhost:8000 (docs: `/docs`)

Data rekaman & model tersimpan di volume `amerta-data` dan `amerta-models`
sehingga bertahan antar restart.

> **Penting (HTTPS & kamera):** browser hanya mengizinkan akses webcam pada
> `localhost` atau origin **HTTPS**. Untuk deploy ke domain, sajikan frontend via
> HTTPS (mis. di belakang reverse proxy seperti Caddy/Nginx/Cloudflare).

### Mengarahkan ke domain lain
URL backend di-bake ke bundle browser saat build. Override lewat build args:
```bash
docker compose build \
  --build-arg NEXT_PUBLIC_API_URL=https://api.contoh.id \
  --build-arg NEXT_PUBLIC_WS_URL=wss://api.contoh.id
```
Dan set `AMERTASIGN_CORS_ORIGINS='["https://contoh.id"]'` pada service backend.

## Opsi 2 — Manual (tanpa Docker)

```bash
# Backend
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000

# Frontend (terminal lain)
cd frontend
pnpm install && pnpm build
NEXT_PUBLIC_API_URL=http://localhost:8000 \
NEXT_PUBLIC_WS_URL=ws://localhost:8000 \
pnpm start -- --port 3030
```

## Konfigurasi LLM (tahap kalimat)

Default memakai `stub` (heuristik lokal, tanpa API). Untuk LLM nyata, set pada
service backend (lihat `backend/.env.example`):

```
AMERTASIGN_LLM_PROVIDER=openai-compatible
AMERTASIGN_LLM_BASE_URL=https://api.openai.com/v1   # atau endpoint lokal (vLLM/Ollama)
AMERTASIGN_LLM_API_KEY=sk-...
AMERTASIGN_LLM_MODEL=gpt-4o-mini
```

## Model

Image dibangun tanpa model terlatih. Latih model lewat UI `/collect` (tombol
"Latih model") atau CLI:

```bash
python scripts/train.py --mode SIBI                 # abjad
python scripts/train.py --mode BISINDO --stage kata # kata
```

Model `*.joblib` tersimpan di volume `amerta-models` dan dimuat otomatis.

## Tes

```bash
cd backend && pytest          # tes pipeline & API
cd frontend && pnpm lint && pnpm build
```
