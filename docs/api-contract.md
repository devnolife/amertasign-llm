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

### `POST /collect`
Simpan satu sampel berlabel untuk training.
```ts
interface CollectRequest {
  mode: Mode;
  stage: Stage;
  label: string;             // mis. "A" (abjad) atau "makan" (kata)
  hands?: HandLandmarks[];   // gestur statis (abjad)
  frames?: HandLandmarks[][];// gestur dinamis (kata/kalimat)
}
interface CollectResponse {
  id: string; label: string; num_frames: number;
  feature_dim: number; total_for_label: number;
}
```

### `GET /datasets?mode=&stage=`
Statistik sampel terkumpul: `{ total, counts: { mode: { stage: { label: n } } } }`.

### `POST /train`
Latih classifier abjad dari sampel terkumpul.
```ts
// body: { mode: Mode, stage?: "abjad", augment_times?: number }
interface TrainResult {
  mode: Mode; stage: Stage; labels: string[];
  n_samples: number; n_classes: number;
  train_accuracy: number; val_accuracy: number;
  model_path: string; note?: string;
}
```

### `GET /train/confusion?mode=&stage=`
Confusion matrix model tersimpan: `{ labels: string[], matrix: number[][] }`.

## Endpoint (rencana fase berikutnya)

| Fase | Endpoint            | Fungsi                                       |
|------|---------------------|----------------------------------------------|
| 4    | `WS /ws/recognize`  | Mode urutan (kata) — buffering temporal      |
| 5    | `POST /compose`     | Urutan gloss → kalimat natural (LLM)         |
