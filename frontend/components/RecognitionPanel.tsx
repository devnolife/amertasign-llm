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
      <div className="rounded-xl bg-zinc-900 border border-zinc-800 p-6 min-h-[140px] flex flex-col justify-center">
        <p className="text-xs uppercase tracking-wide text-zinc-500 mb-2">
          Teks terdeteksi
        </p>
        <p className="text-5xl font-bold text-white break-words min-h-[3.5rem]">
          {text || <span className="text-zinc-600 text-2xl">—</span>}
        </p>

        {modelLoaded && confidence > 0 && (
          <div className="mt-4">
            <div className="h-2 rounded-full bg-zinc-800 overflow-hidden">
              <div
                className="h-full bg-violet-500 transition-all"
                style={{ width: `${Math.round(confidence * 100)}%` }}
              />
            </div>
            <p className="text-xs text-zinc-500 mt-1">
              keyakinan {Math.round(confidence * 100)}%
            </p>
          </div>
        )}
      </div>

      {candidates.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {candidates.map((c) => (
            <span
              key={c.label}
              className="px-3 py-1 rounded-full bg-zinc-800 text-zinc-300 text-sm"
            >
              {c.label}{" "}
              <span className="text-zinc-500">
                {Math.round(c.confidence * 100)}%
              </span>
            </span>
          ))}
        </div>
      )}

      {result && !modelLoaded && (
        <div className="rounded-lg bg-amber-950/40 border border-amber-900/50 p-3 text-sm text-amber-200">
          {result.note ??
            "Model belum dilatih. Jalur kamera → landmark → backend sudah aktif."}
        </div>
      )}

      <p className="text-xs text-zinc-500">
        Tangan terdeteksi: <span className="text-zinc-300">{handsDetected}</span>
        {capturing && (
          <span className="ml-2 inline-flex items-center gap-1 text-rose-400">
            <span className="h-2 w-2 rounded-full bg-rose-500 animate-pulse" />
            merekam gestur…
          </span>
        )}
      </p>
    </div>
  );
}
