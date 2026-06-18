# Backend FastAPI — image produksi
FROM python:3.10-slim

WORKDIR /app

# Dependency dulu (cache layer)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Kode aplikasi
COPY app ./app

# Direktori model & data (di-mount sebagai volume saat runtime)
RUN mkdir -p /app/models /data/recordings

ENV AMERTASIGN_DATA_DIR=/data \
    AMERTASIGN_MODELS_DIR=/app/models \
    PYTHONUNBUFFERED=1

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
