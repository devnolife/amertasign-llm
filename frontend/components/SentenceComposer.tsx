"use client";

import { useCallback, useState } from "react";

import { composeSentence, type ComposeResult } from "@/lib/api";
import type { Mode } from "@/lib/types";

interface Props {
  mode: Mode;
  gloss: string[];
  onClear: () => void;
  onRemoveLast: () => void;
}

export default function SentenceComposer({
  mode,
  gloss,
  onClear,
  onRemoveLast,
}: Props) {
  const [result, setResult] = useState<ComposeResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const compose = useCallback(async () => {
    if (gloss.length === 0) return;
    setBusy(true);
    setError(null);
    try {
      setResult(await composeSentence(mode, gloss));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Gagal menyusun kalimat.");
    } finally {
      setBusy(false);
    }
  }, [mode, gloss]);

  return (
    <div className="flex flex-col gap-4">
      <div className="card p-5">
        <div className="mb-2 flex items-center justify-between">
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-[var(--text-dim)]">
            Gloss terkumpul
          </p>
          <span className="chip chip-mono">{gloss.length} token</span>
        </div>

        {gloss.length === 0 ? (
          <p className="text-sm text-[var(--text-dim)]">
            Lakukan isyarat kata satu per satu — hasilnya terkumpul di sini.
          </p>
        ) : (
          <div className="flex flex-wrap gap-1.5">
            {gloss.map((g, i) => (
              <span key={`${g}-${i}`} className="chip">
                {g}
              </span>
            ))}
          </div>
        )}

        <div className="mt-4 flex flex-wrap gap-2">
          <button
            type="button"
            onClick={() => void compose()}
            disabled={busy || gloss.length === 0}
            className="btn btn-primary"
          >
            {busy ? "Menyusun…" : "✨ Susun kalimat"}
          </button>
          <button
            type="button"
            onClick={onRemoveLast}
            disabled={gloss.length === 0}
            className="btn btn-ghost"
          >
            Hapus terakhir
          </button>
          <button
            type="button"
            onClick={() => {
              onClear();
              setResult(null);
            }}
            disabled={gloss.length === 0}
            className="btn btn-ghost"
          >
            Bersihkan
          </button>
        </div>
      </div>

      {result && (
        <div className="card card--glow animate-rise p-5">
          <p className="mb-2 text-xs font-semibold uppercase tracking-[0.14em] text-[#c4b5fd]">
            Kalimat
          </p>
          <p className="font-display text-2xl font-semibold text-white">
            {result.sentence}
          </p>
          <p className="chip-mono mt-2 text-xs text-[var(--text-dim)]">
            via {result.provider}
            {result.note ? ` · ${result.note}` : ""}
          </p>
        </div>
      )}

      {error && (
        <div
          className="rounded-xl p-3 text-sm"
          style={{
            border: "1px solid rgba(251,113,133,0.3)",
            background: "rgba(159,18,57,0.18)",
            color: "#fecdd3",
          }}
        >
          {error}
        </div>
      )}
    </div>
  );
}
