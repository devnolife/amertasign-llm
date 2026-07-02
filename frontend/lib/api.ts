// Klien WebSocket untuk streaming pengenalan + fallback HTTP.

import { API_URL, WS_URL } from "./config";
import type {
  CollectResponse,
  DatasetStats,
  FramePayload,
  HandLandmarks,
  Mode,
  RecognitionResult,
  Stage,
  TrainResult,
} from "./types";

export type SocketStatus = "connecting" | "open" | "closed" | "error";

type ResultHandler = (result: RecognitionResult) => void;
type StatusHandler = (status: SocketStatus) => void;

export class RecognitionSocket {
  private ws: WebSocket | null = null;
  private shouldRun = false;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;

  constructor(
    private readonly onResult: ResultHandler,
    private readonly onStatus: StatusHandler = () => { },
  ) { }

  connect(): void {
    this.shouldRun = true;
    this.open();
  }

  private open(): void {
    this.onStatus("connecting");
    const ws = new WebSocket(`${WS_URL}/ws/recognize`);
    this.ws = ws;

    ws.onopen = () => this.onStatus("open");
    ws.onmessage = (ev) => {
      try {
        const data = JSON.parse(ev.data) as RecognitionResult & {
          error?: string;
        };
        if (!data.error) this.onResult(data);
      } catch {
        /* abaikan payload non-JSON */
      }
    };
    ws.onerror = () => this.onStatus("error");
    ws.onclose = () => {
      this.onStatus("closed");
      if (this.shouldRun) {
        this.reconnectTimer = setTimeout(() => this.open(), 1000);
      }
    };
  }

  send(payload: FramePayload): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(payload));
    }
  }

  close(): void {
    this.shouldRun = false;
    if (this.reconnectTimer) clearTimeout(this.reconnectTimer);
    this.ws?.close();
    this.ws = null;
  }
}

// Fallback HTTP (mis. untuk uji satu frame tanpa WebSocket).
export async function recognizeOnce(
  payload: FramePayload,
): Promise<RecognitionResult> {
  const res = await fetch(`${API_URL}/recognize`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(`recognize gagal: ${res.status}`);
  return (await res.json()) as RecognitionResult;
}

// Pengenalan urutan (kata) — kirim segmen frame yang sudah disegmentasi.
export async function recognizeSequence(
  mode: Mode,
  stage: Stage,
  frames: HandLandmarks[][],
): Promise<RecognitionResult> {
  const res = await fetch(`${API_URL}/recognize_sequence`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ mode, stage, frames }),
  });
  if (!res.ok) throw new Error(`recognize_sequence gagal: ${res.status}`);
  return (await res.json()) as RecognitionResult;
}

// ───── Pengumpulan data & training (Fase 2-3) ─────

export interface CollectBody {
  mode: Mode;
  stage: Stage;
  label: string;
  hands?: HandLandmarks[];
  frames?: HandLandmarks[][];
}

export async function collectSample(
  body: CollectBody,
): Promise<CollectResponse> {
  const res = await fetch(`${API_URL}/collect`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(`collect gagal: ${res.status} ${detail}`);
  }
  return (await res.json()) as CollectResponse;
}

export async function getDatasets(
  mode?: Mode,
  stage?: Stage,
): Promise<DatasetStats> {
  const params = new URLSearchParams();
  if (mode) params.set("mode", mode);
  if (stage) params.set("stage", stage);
  const qs = params.toString();
  const res = await fetch(`${API_URL}/datasets${qs ? `?${qs}` : ""}`);
  if (!res.ok) throw new Error(`datasets gagal: ${res.status}`);
  return (await res.json()) as DatasetStats;
}

export async function trainModel(
  mode: Mode,
  stage: Stage = "abjad",
  augmentTimes = 2,
): Promise<TrainResult> {
  const res = await fetch(`${API_URL}/train`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ mode, stage, augment_times: augmentTimes }),
  });
  if (!res.ok) throw new Error(`train gagal: ${res.status}`);
  return (await res.json()) as TrainResult;
}

// Confusion matrix model tersimpan — untuk melihat huruf yang sering tertukar.
export interface ConfusionResult {
  labels: string[];
  matrix: number[][];
}

export async function getConfusion(
  mode: Mode,
  stage: Stage = "abjad",
): Promise<ConfusionResult> {
  const params = new URLSearchParams({ mode, stage });
  const res = await fetch(`${API_URL}/train/confusion?${params}`);
  if (!res.ok) throw new Error(`confusion gagal: ${res.status}`);
  return (await res.json()) as ConfusionResult;
}

// ───── Penyusunan kalimat dari gloss (Fase 5) ─────

export interface ComposeResult {
  sentence: string;
  provider: string;
  gloss: string[];
  note?: string;
}

export async function composeSentence(
  mode: Mode,
  gloss: string[],
): Promise<ComposeResult> {
  const res = await fetch(`${API_URL}/compose`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ mode, gloss }),
  });
  if (!res.ok) throw new Error(`compose gagal: ${res.status}`);
  return (await res.json()) as ComposeResult;
}
