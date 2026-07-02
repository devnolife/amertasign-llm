"use client";

import type { RecognitionResult } from "@/lib/types";

interface Props {
  result: RecognitionResult | null;
  handsDetected: number;
  capturing?: boolean;
}

export default function RecognitionPanel({
  result,
  handsDetected,
  capturing = false,
}: Props) {
  const text = result?.text ?? "";
  const confidence = result?.confidence ?? 0;
  const candidates = result?.candidates ?? [];
  const modelLoaded = result?.model_loaded ?? false;

  return (
    <div className="flex flex-col gap-4">
      <div className="card card--glow flex min-h-[170px] flex-col justify-center p-6">
        <p className="mb-2 text-xs font-semibold uppercase tracking-[0.14em] text-[var(--text-dim)]">
          Teks terdeteksi
        </p>
        <p className="font-display min-h-[4rem] break-words text-6xl font-bold">
          {text ? (
            <span className="gradient-text">{text}</span>
          ) : (
            <span className="text-2xl text-[var(--text-dim)] opacity-50">—</span>
          )}
        </p>

        {modelLoaded && confidence > 0 && (
          <div className="mt-4">
            <div className="h-1.5 overflow-hidden rounded-full bg-white/5">
              <div
                className="h-full rounded-full transition-all duration-300"
                style={{
                  width: `${Math.round(confidence * 100)}%`,
                  background: "linear-gradient(90deg, #8b5cf6, #22d3ee)",
                  boxShadow: "0 0 12px rgba(139,92,246,0.6)",
                }}
              />
            </div>
            <p className="chip-mono mt-1.5 text-xs text-[var(--text-dim)]">
              keyakinan {Math.round(confidence * 100)}%
            </p>
          </div>
        )}
      </div>

      {candidates.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {candidates.map((c) => (
            <span key={c.label} className="chip">
              <b>{c.label}</b>
              <span className="chip-mono text-[var(--text-dim)]">
                {Math.round(c.confidence * 100)}%
              </span>
            </span>
          ))}
        </div>
      )}

      {result && !modelLoaded && (
        <div
          className="rounded-xl p-3 text-sm"
          style={{
            border: "1px solid rgba(251,191,36,0.25)",
            background: "rgba(120,53,15,0.2)",
            color: "#fde68a",
          }}
        >
          {result.note ??
            "Model belum dilatih. Jalur kamera → landmark → backend sudah aktif."}
        </div>
      )}

      <p className="flex items-center gap-2 text-xs text-[var(--text-dim)]">
        Tangan terdeteksi:{" "}
        <span className="chip-mono text-white">{handsDetected}</span>
        {capturing && (
          <span className="inline-flex items-center gap-1.5 text-rose-300">
            <span className="h-2 w-2 animate-pulse rounded-full bg-rose-500" />
            merekam gestur…
          </span>
        )}
      </p>
    </div>
  );
}
