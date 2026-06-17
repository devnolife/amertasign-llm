// Menggambar overlay kerangka tangan di atas canvas.

import { HAND_CONNECTIONS } from "./mediapipe";
import type { HandLandmarks } from "./types";

const HAND_COLORS: Record<string, { line: string; dot: string }> = {
  Left: { line: "#22d3ee", dot: "#67e8f9" }, // cyan
  Right: { line: "#a855f7", dot: "#d8b4fe" }, // ungu
};

export function drawHands(
  ctx: CanvasRenderingContext2D,
  hands: HandLandmarks[],
  width: number,
  height: number,
): void {
  ctx.clearRect(0, 0, width, height);

  for (const hand of hands) {
    const colors = HAND_COLORS[hand.handedness] ?? HAND_COLORS.Right;
    const pts = hand.landmarks;

    // Garis antar titik
    ctx.strokeStyle = colors.line;
    ctx.lineWidth = Math.max(2, width * 0.004);
    ctx.lineJoin = "round";
    for (const conn of HAND_CONNECTIONS) {
      const a = pts[conn.start];
      const b = pts[conn.end];
      if (!a || !b) continue;
      ctx.beginPath();
      ctx.moveTo(a.x * width, a.y * height);
      ctx.lineTo(b.x * width, b.y * height);
      ctx.stroke();
    }

    // Titik landmark
    ctx.fillStyle = colors.dot;
    const r = Math.max(3, width * 0.006);
    for (const p of pts) {
      ctx.beginPath();
      ctx.arc(p.x * width, p.y * height, r, 0, Math.PI * 2);
      ctx.fill();
    }
  }
}
