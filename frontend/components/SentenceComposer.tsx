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
      <div className="rounded-xl bg-zinc-900 border border-zinc-800 p-5">
        <div className="mb-2 flex items-center justify-between">
          <p className="text-xs uppercase tracking-wide text-zinc-500">
            Gloss terkumpul
          </p>
          <span className="text-xs text-zinc-500">{gloss.length} token</span>
        </div>

        {gloss.length === 0 ? (
          <p className="text-sm text-zinc-600">
            Lakukan isyarat kata satu per satu — hasilnya terkumpul di sini.
          </p>
        ) : (
          <div className="flex flex-wrap gap-1.5">
            {gloss.map((g, i) => (
              <span
                key={`${g}-${i}`}
                className="rounded-md bg-zinc-800 px-2.5 py-1 text-sm text-zinc-200"
              >
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
            className="rounded-lg bg-violet-600 px-4 py-2 text-sm font-semibold text-white hover:bg-violet-500 disabled:opacity-50"
          >
            {busy ? "Menyusun…" : "Susun kalimat"}
          </button>
          <button
            type="button"
            onClick={onRemoveLast}
            disabled={gloss.length === 0}
            className="rounded-lg bg-zinc-800 px-4 py-2 text-sm text-zinc-200 hover:bg-zinc-700 disabled:opacity-50"
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
            className="rounded-lg bg-zinc-800 px-4 py-2 text-sm text-zinc-200 hover:bg-zinc-700 disabled:opacity-50"
          >
            Bersihkan
          </button>
        </div>
      </div>

      {result && (
        <div className="rounded-xl border border-violet-900/50 bg-violet-950/30 p-5">
          <p className="text-xs uppercase tracking-wide text-violet-400 mb-2">
            Kalimat
          </p>
          <p className="text-xl font-semibold text-white">{result.sentence}</p>
          <p className="mt-2 text-xs text-zinc-500">
            via {result.provider}
            {result.note ? ` · ${result.note}` : ""}
          </p>
        </div>
      )}

      {error && (
        <div className="rounded-lg bg-rose-950/50 border border-rose-900/60 p-3 text-sm text-rose-200">
          {error}
        </div>
      )}
    </div>
  );
}
