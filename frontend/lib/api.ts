// Klien WebSocket untuk streaming pengenalan + fallback HTTP.

import { API_URL, WS_URL } from "./config";
import type { FramePayload, RecognitionResult } from "./types";

export type SocketStatus = "connecting" | "open" | "closed" | "error";

type ResultHandler = (result: RecognitionResult) => void;
type StatusHandler = (status: SocketStatus) => void;

export class RecognitionSocket {
  private ws: WebSocket | null = null;
  private shouldRun = false;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;

  constructor(
    private readonly onResult: ResultHandler,
    private readonly onStatus: StatusHandler = () => {},
  ) {}

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
