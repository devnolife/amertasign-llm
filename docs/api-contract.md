# Kontrak API

Base URL dev: `http://localhost:8000`

## Tipe bersama

```ts
type Mode  = "BISINDO" | "SIBI";
type Stage = "abjad" | "kata" | "kalimat";

interface Landmark { x: number; y: number; z: number }
interface HandLandmarks {
  handedness: "Left" | "Right";
  score: number;
  landmarks: Landmark[];   // panjang 21
}
interface FramePayload {
  mode: Mode;
  stage: Stage;
  hands: HandLandmarks[];  // 0..2 tangan
  timestamp?: number;
}
interface Candidate { label: string; confidence: number }
interface RecognitionResult {
  text: string;            // label terbaik (kosong bila di bawah ambang/ tak yakin)
  confidence: number;
  candidates: Candidate[]; // top-k
  mode: Mode;
  stage: Stage;
  model_loaded: boolean;   // false bila model untuk (mode,stage) belum dilatih
  note?: string;
}
```

## Endpoint

### `GET /health`
```json
{ "status": "ok", "app": "...", "models_available": ["SIBI_abjad.joblib"], "min_confidence": 0.6 }
```

### `POST /recognize`
Body: `FramePayload` → Response: `RecognitionResult`.
Untuk gestur statis (abjad). Satu frame per request.

### `WS /ws/recognize`
Streaming low-latency untuk real-time.
- Client mengirim `FramePayload` (JSON) per frame.
- Server membalas `RecognitionResult` (JSON) per frame.
- Payload invalid → `{ "error": "invalid_payload", "detail": [...] }`.

## Endpoint (rencana fase berikutnya)

| Fase | Endpoint            | Fungsi                                       |
|------|---------------------|----------------------------------------------|
| 2    | `POST /collect`     | Simpan sampel berlabel untuk dataset         |
| 2    | `GET  /datasets`    | Statistik dataset terkumpul                  |
| 2    | `POST /train`       | Trigger training model (mode, stage)         |
| 4    | `WS /ws/recognize`  | Mode urutan (kata) — buffering temporal      |
| 5    | `POST /compose`     | Urutan gloss → kalimat natural (LLM)         |
