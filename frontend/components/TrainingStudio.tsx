"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import CameraView from "@/components/CameraView";
import { useHandTracking } from "@/hooks/useHandTracking";
import { collectSample, getConfusion, getDatasets, trainModel } from "@/lib/api";
import type { DatasetStats, Mode, TrainResult } from "@/lib/types";

const MODES: Mode[] = ["BISINDO", "SIBI"];
const ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ".split("");
const TARGET_PER_LABEL = 30; // rekomendasi sampel per huruf
const CAPTURE_INTERVAL_MS = 350; // jeda antar-tangkapan otomatis
const COUNTDOWN_SECONDS = 3;

type Phase = "idle" | "countdown" | "capturing";

interface WeakLabel {
  label: string;
  accuracy: number; // 0..1 pada seluruh sampel label ini
  confusedWith: string; // label lain yang paling sering tertukar
}

/**
 * Studio training terpandu: pilih huruf → auto-capture N sampel dari kamera →
 * lanjut huruf berikutnya → latih model. Progres per label ditampilkan.
 */
export default function TrainingStudio() {
  const [mode, setMode] = useState<Mode>("BISINDO");
  const [label, setLabel] = useState("A");
  const [batchSize, setBatchSize] = useState(10);
  const [phase, setPhase] = useState<Phase>("idle");
  const [countdown, setCountdown] = useState(0);
  const [captured, setCaptured] = useState(0);
  const [message, setMessage] = useState<string | null>(null);
  const [stats, setStats] = useState<DatasetStats | null>(null);
  const [training, setTraining] = useState(false);
  const [trainResult, setTrainResult] = useState<TrainResult | null>(null);
  const [weakLabels, setWeakLabels] = useState<WeakLabel[]>([]);

  const tracking = useHandTracking();
  const phaseRef = useRef<Phase>("idle");
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const [statsVersion, setStatsVersion] = useState(0);
  const refreshStats = useCallback(() => setStatsVersion((v) => v + 1), []);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const data = await getDatasets(mode, "abjad");
        if (!cancelled) setStats(data);
      } catch {
        /* backend mungkin belum jalan */
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [mode, statsVersion]);

  const counts = stats?.counts?.[mode]?.abjad ?? {};
  const countFor = useCallback(
    (lbl: string) => counts[lbl] ?? 0,
    [counts],
  );

  const stopCapture = useCallback(
    (msg?: string) => {
      if (timerRef.current) clearInterval(timerRef.current);
      timerRef.current = null;
      phaseRef.current = "idle";
      setPhase("idle");
      if (msg) setMessage(msg);
      refreshStats();
    },
    [refreshStats],
  );

  // Loop tangkapan otomatis: ambil landmark terbaru tiap interval.
  const runCaptureLoop = useCallback(() => {
    phaseRef.current = "capturing";
    setPhase("capturing");
    setCaptured(0);
    setMessage(null);
    let done = 0;
    let missed = 0;

    timerRef.current = setInterval(() => {
      if (phaseRef.current !== "capturing") return;
      const hands = tracking.latestHandsRef.current;
      if (hands.length === 0) {
        missed += 1;
        if (missed >= 15) {
          stopCapture("Tangan tidak terdeteksi — tangkapan dihentikan.");
        }
        return;
      }
      missed = 0;
      const snapshot = hands.map((h) => ({ ...h, landmarks: [...h.landmarks] }));
      void collectSample({ mode, stage: "abjad", label, hands: snapshot })
        .then(() => {
          done += 1;
          setCaptured(done);
          if (done >= batchSize) {
            stopCapture(`Selesai — ${done} sampel "${label}" tersimpan.`);
          }
        })
        .catch((err: unknown) => {
          stopCapture(
            err instanceof Error ? err.message : "Gagal menyimpan sampel.",
          );
        });
    }, CAPTURE_INTERVAL_MS);
  }, [batchSize, label, mode, stopCapture, tracking.latestHandsRef]);

  const startCapture = useCallback(() => {
    if (!tracking.cameraOn) {
      setMessage("Nyalakan kamera dulu.");
      return;
    }
    setTrainResult(null);
    setMessage(null);
    phaseRef.current = "countdown";
    setPhase("countdown");
    setCountdown(COUNTDOWN_SECONDS);

    let remaining = COUNTDOWN_SECONDS;
    timerRef.current = setInterval(() => {
      remaining -= 1;
      setCountdown(remaining);
      if (remaining <= 0) {
        if (timerRef.current) clearInterval(timerRef.current);
        timerRef.current = null;
        runCaptureLoop();
      }
    }, 1000);
  }, [runCaptureLoop, tracking.cameraOn]);

  useEffect(() => {
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, []);

  const onTrain = useCallback(async () => {
    setTraining(true);
    setMessage(null);
    setTrainResult(null);
    setWeakLabels([]);
    try {
      const res = await trainModel(mode, "abjad");
      setTrainResult(res);
      setMessage(
        res.note ??
        `Model dilatih: ${res.n_classes} kelas dari ${res.n_samples} sampel.`,
      );

      // Analisis huruf lemah dari confusion matrix (panduan koleksi data).
      if (!res.note) {
        try {
          const conf = await getConfusion(mode, "abjad");
          const weak: WeakLabel[] = [];
          conf.labels.forEach((lbl, i) => {
            const row = conf.matrix[i] ?? [];
            const total = row.reduce((a, b) => a + b, 0);
            if (total === 0) return;
            const correct = row[i] ?? 0;
            const accuracy = correct / total;
            if (accuracy >= 0.9) return;
            let worstJ = -1;
            let worstN = 0;
            row.forEach((n, j) => {
              if (j !== i && n > worstN) {
                worstN = n;
                worstJ = j;
              }
            });
            weak.push({
              label: lbl,
              accuracy,
              confusedWith: worstJ >= 0 ? conf.labels[worstJ] : "-",
            });
          });
          weak.sort((a, b) => a.accuracy - b.accuracy);
          setWeakLabels(weak.slice(0, 6));
        } catch {
          /* opsional — abaikan bila gagal */
        }
      }
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Gagal melatih model.");
    } finally {
      setTraining(false);
    }
  }, [mode]);

  const busy = phase !== "idle" || training;
  const totalSamples = ALPHABET.reduce((acc, l) => acc + countFor(l), 0);
  const labelsReady = ALPHABET.filter(
    (l) => countFor(l) >= TARGET_PER_LABEL,
  ).length;

  return (
    <div className="grid gap-6 lg:grid-cols-[1fr_380px]">
      {/* ── Kolom kamera ── */}
      <div className="relative">
        <CameraView
          tracking={tracking}
          hint='Kamera mati — tekan "Mulai kamera" untuk mulai training'
        />

        {phase === "countdown" && (
          <div className="pointer-events-none absolute inset-0 flex items-center justify-center rounded-3xl bg-black/30 backdrop-blur-[2px]">
            <span
              className="font-display text-9xl font-black text-white"
              style={{ textShadow: "0 0 60px rgba(139,92,246,0.9)" }}
            >
              {countdown}
            </span>
          </div>
        )}

        {phase === "capturing" && (
          <div className="pointer-events-none absolute inset-x-0 top-4 flex justify-center">
            <span
              className="chip-mono flex items-center gap-2 rounded-full px-4 py-1.5 text-sm font-semibold text-white"
              style={{
                background: "linear-gradient(120deg, rgba(139,92,246,0.95), rgba(14,165,233,0.9))",
                boxShadow: "0 8px 30px -8px rgba(139,92,246,0.8)",
              }}
            >
              <span className="h-2 w-2 animate-pulse rounded-full bg-white" />
              REC “{label}” {captured}/{batchSize}
            </span>
          </div>
        )}
      </div>

      {/* ── Kolom kontrol ── */}
      <div className="card flex flex-col gap-5 p-5">
        {!tracking.cameraOn ? (
          <button
            type="button"
            onClick={() => void tracking.start()}
            disabled={tracking.loading}
            className="btn btn-success"
          >
            {tracking.loading ? "Memuat…" : "▶ Mulai kamera"}
          </button>
        ) : (
          <button
            type="button"
            onClick={tracking.stop}
            disabled={busy}
            className="btn btn-danger"
          >
            ■ Stop kamera
          </button>
        )}

        <div className="seg-group">
          {MODES.map((m) => (
            <button
              key={m}
              type="button"
              onClick={() => setMode(m)}
              disabled={busy}
              className={`seg flex-1 ${mode === m ? "seg--active" : ""}`}
            >
              {m}
            </button>
          ))}
        </div>

        {/* Pilihan huruf A-Z dengan progres */}
        <div>
          <div className="mb-2 flex items-baseline justify-between">
            <h2 className="text-xs font-semibold uppercase tracking-[0.14em] text-[var(--text-dim)]">
              Pilih huruf
            </h2>
            <span className="chip-mono text-xs text-[var(--text-dim)]">
              target {TARGET_PER_LABEL}/huruf
            </span>
          </div>
          <div className="grid grid-cols-7 gap-1.5 sm:grid-cols-9 lg:grid-cols-7">
            {ALPHABET.map((l) => {
              const n = countFor(l);
              const pct = Math.min(100, (n / TARGET_PER_LABEL) * 100);
              const active = label === l;
              const ready = n >= TARGET_PER_LABEL;
              return (
                <button
                  key={l}
                  type="button"
                  onClick={() => setLabel(l)}
                  disabled={busy}
                  title={`${l}: ${n} sampel`}
                  className="font-display relative overflow-hidden rounded-lg py-2 text-sm font-bold transition-all disabled:opacity-50"
                  style={
                    active
                      ? {
                        background:
                          "linear-gradient(120deg, #8b5cf6, #7c3aed)",
                        color: "white",
                        boxShadow:
                          "0 0 0 1.5px rgba(196,181,253,0.6), 0 6px 20px -6px rgba(139,92,246,0.8)",
                      }
                      : ready
                        ? {
                          background: "rgba(6,78,59,0.45)",
                          color: "#6ee7b7",
                          border: "1px solid rgba(52,211,153,0.3)",
                        }
                        : {
                          background: "rgba(148,163,216,0.07)",
                          color: "var(--text)",
                          border: "1px solid var(--border)",
                        }
                  }
                >
                  <span className="relative z-10">{l}</span>
                  {!active && n > 0 && !ready && (
                    <span
                      className="absolute inset-x-0 bottom-0 h-1"
                      style={{
                        width: `${pct}%`,
                        background:
                          "linear-gradient(90deg, #8b5cf6, #22d3ee)",
                      }}
                    />
                  )}
                </button>
              );
            })}
          </div>
        </div>

        {/* Jumlah tangkapan per sesi */}
        <div>
          <h2 className="mb-2 text-xs font-semibold uppercase tracking-[0.14em] text-[var(--text-dim)]">
            Sampel per sesi
          </h2>
          <div className="seg-group">
            {[5, 10, 20, 30].map((n) => (
              <button
                key={n}
                type="button"
                onClick={() => setBatchSize(n)}
                disabled={busy}
                className={`seg chip-mono flex-1 ${batchSize === n ? "seg--active" : ""}`}
              >
                {n}
              </button>
            ))}
          </div>
        </div>

        {phase === "capturing" ? (
          <button
            type="button"
            onClick={() => stopCapture("Tangkapan dihentikan.")}
            className="btn btn-warning py-3"
          >
            ■ Berhenti ({captured}/{batchSize})
          </button>
        ) : (
          <button
            type="button"
            onClick={startCapture}
            disabled={busy || !tracking.cameraOn}
            className="btn btn-primary py-3"
          >
            ◉ Ambil {batchSize} sampel “{label}” · mundur {COUNTDOWN_SECONDS}s
          </button>
        )}

        {/* Ringkasan & train */}
        <div
          className="rounded-2xl p-4 text-sm"
          style={{
            border: "1px solid var(--border)",
            background: "rgba(10,12,20,0.5)",
          }}
        >
          <div className="mb-3 flex justify-between text-[var(--text-dim)]">
            <span>
              Total sampel:{" "}
              <b className="chip-mono text-white">{totalSamples}</b>
            </span>
            <span>
              Huruf siap:{" "}
              <b className="chip-mono text-white">
                {labelsReady}/{ALPHABET.length}
              </b>
            </span>
          </div>
          <button
            type="button"
            onClick={() => void onTrain()}
            disabled={busy || totalSamples === 0}
            className="btn btn-success w-full"
          >
            {training ? "Melatih…" : `⚡ Latih model abjad ${mode}`}
          </button>

          {trainResult && !trainResult.note && (
            <div className="chip-mono mt-3 grid grid-cols-2 gap-2 text-xs text-[var(--text)]">
              <span>kelas: {trainResult.n_classes}</span>
              <span>sampel: {trainResult.n_samples}</span>
              <span>
                acc latih: {(trainResult.train_accuracy * 100).toFixed(0)}%
              </span>
              <span>
                acc val: {(trainResult.val_accuracy * 100).toFixed(0)}%
              </span>
            </div>
          )}
        </div>

        {weakLabels.length > 0 && (
          <div
            className="rounded-2xl p-4 text-sm"
            style={{
              border: "1px solid rgba(251,191,36,0.25)",
              background: "rgba(120,53,15,0.15)",
            }}
          >
            <p className="mb-2 text-xs font-semibold uppercase tracking-[0.14em] text-amber-200">
              Huruf yang perlu sampel tambahan
            </p>
            <div className="flex flex-col gap-1.5">
              {weakLabels.map((w) => (
                <div
                  key={w.label}
                  className="flex items-center justify-between gap-2 text-amber-100/90"
                >
                  <span>
                    <b className="font-display">{w.label}</b>{" "}
                    <span className="text-amber-200/60">
                      sering terbaca sebagai
                    </span>{" "}
                    <b className="font-display">{w.confusedWith}</b>
                  </span>
                  <span className="chip-mono text-xs">
                    {(w.accuracy * 100).toFixed(0)}%
                  </span>
                </div>
              ))}
            </div>
            <p className="mt-2 text-xs text-amber-200/60">
              Klik hurufnya lalu ambil sesi sampel baru dengan variasi
              sudut/jarak, kemudian latih ulang.
            </p>
          </div>
        )}

        {message && (
          <div
            className="rounded-xl p-3 text-sm"
            style={{
              border: "1px solid var(--border)",
              background: "rgba(10,12,20,0.6)",
              color: "var(--text)",
            }}
          >
            {message}
          </div>
        )}
      </div>
    </div>
  );
}
