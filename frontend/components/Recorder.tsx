"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import CameraView from "@/components/CameraView";
import { useHandTracking } from "@/hooks/useHandTracking";
import {
  collectSample,
  getDatasets,
  trainModel,
} from "@/lib/api";
import type {
  DatasetStats,
  HandLandmarks,
  Mode,
  Stage,
  TrainResult,
} from "@/lib/types";

const MODES: Mode[] = ["BISINDO", "SIBI"];
const STAGES: { value: Stage; label: string }[] = [
  { value: "abjad", label: "Abjad" },
  { value: "kata", label: "Kata" },
  { value: "kalimat", label: "Kalimat" },
];

export default function Recorder() {
  const [mode, setMode] = useState<Mode>("SIBI");
  const [stage, setStage] = useState<Stage>("abjad");
  const [label, setLabel] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [stats, setStats] = useState<DatasetStats | null>(null);
  const [trainResult, setTrainResult] = useState<TrainResult | null>(null);
  const [recording, setRecording] = useState(false);

  const recordBufferRef = useRef<HandLandmarks[][]>([]);

  // Untuk stage dinamis (kata/kalimat) buffer urutan frame selama merekam.
  const handleFrame = useCallback(
    (hands: HandLandmarks[]) => {
      if (recording && stage !== "abjad" && hands.length > 0) {
        recordBufferRef.current.push(hands);
      }
    },
    [recording, stage],
  );

  const tracking = useHandTracking({ onFrame: handleFrame });

  const [statsVersion, setStatsVersion] = useState(0);
  const refreshStats = useCallback(() => setStatsVersion((v) => v + 1), []);

  // Sinkronisasi statistik dataset dari backend saat mode/stage berubah atau
  // setelah aksi (collect/train) menaikkan statsVersion. setState terjadi
  // setelah await sehingga tidak memicu cascading render sinkron.
  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const data = await getDatasets(mode, stage);
        if (!cancelled) setStats(data);
      } catch {
        /* backend mungkin belum jalan */
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [mode, stage, statsVersion]);

  const labelCount =
    stats?.counts?.[mode]?.[stage]?.[label.trim().toUpperCase()] ??
    stats?.counts?.[mode]?.[stage]?.[label.trim()] ??
    0;

  // Abjad: tangkap 1 frame statis.
  const captureStatic = useCallback(async () => {
    const lbl = label.trim();
    if (!lbl) {
      setMessage("Isi label dulu (mis. A).");
      return;
    }
    const hands = tracking.latestHandsRef.current;
    if (hands.length === 0) {
      setMessage("Tidak ada tangan terdeteksi.");
      return;
    }
    setBusy(true);
    setMessage(null);
    try {
      const res = await collectSample({ mode, stage, label: lbl, hands });
      setMessage(`Tersimpan "${res.label}" — total ${res.total_for_label} sampel.`);
      refreshStats();
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Gagal menyimpan.");
    } finally {
      setBusy(false);
    }
  }, [label, mode, stage, tracking.latestHandsRef, refreshStats]);

  // Kata/kalimat: rekam urutan frame antara start & stop.
  const toggleSequence = useCallback(async () => {
    if (!recording) {
      const lbl = label.trim();
      if (!lbl) {
        setMessage("Isi label dulu.");
        return;
      }
      recordBufferRef.current = [];
      setRecording(true);
      setMessage("Merekam… lakukan gestur, lalu tekan Stop.");
      return;
    }

    // stop
    setRecording(false);
    const frames = recordBufferRef.current;
    recordBufferRef.current = [];
    if (frames.length === 0) {
      setMessage("Tidak ada frame terekam.");
      return;
    }
    setBusy(true);
    try {
      const res = await collectSample({
        mode,
        stage,
        label: label.trim(),
        frames,
      });
      setMessage(
        `Tersimpan urutan "${res.label}" (${res.num_frames} frame) — total ${res.total_for_label}.`,
      );
      refreshStats();
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Gagal menyimpan.");
    } finally {
      setBusy(false);
    }
  }, [recording, label, mode, stage, refreshStats]);

  const onTrain = useCallback(async () => {
    // Training otomatis tersedia untuk abjad & kata.
    const trainStage = stage === "kata" ? "kata" : "abjad";
    setBusy(true);
    setMessage(null);
    setTrainResult(null);
    try {
      const res = await trainModel(mode, trainStage);
      setTrainResult(res);
      setMessage(
        res.note
          ? res.note
          : `Model dilatih: ${res.n_classes} kelas, val acc ${(res.val_accuracy * 100).toFixed(0)}%.`,
      );
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Gagal melatih.");
    } finally {
      setBusy(false);
    }
  }, [mode, stage]);

  const labelsForStage = stats?.counts?.[mode]?.[stage] ?? {};

  return (
    <div className="grid gap-6 lg:grid-cols-[1fr_360px]">
      <CameraView
        tracking={tracking}
        hint='Kamera mati — tekan "Mulai kamera" untuk merekam'
      />

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
              className={`seg flex-1 ${mode === m ? "seg--active" : ""}`}
            >
              {m}
            </button>
          ))}
        </div>

        <div className="seg-group">
          {STAGES.map((s) => (
            <button
              key={s.value}
              type="button"
              onClick={() => setStage(s.value)}
              className={`seg flex-1 ${stage === s.value ? "seg--active" : ""}`}
            >
              {s.label}
            </button>
          ))}
        </div>

        <div>
          <label className="text-xs font-semibold uppercase tracking-[0.14em] text-[var(--text-dim)]">
            Label {stage === "abjad" ? "(huruf/angka)" : "(kata)"}
          </label>
          <div className="mt-1.5 flex items-center gap-2">
            <input
              value={label}
              onChange={(e) => setLabel(e.target.value)}
              placeholder={stage === "abjad" ? "A" : "makan"}
              className="flex-1 rounded-xl px-3.5 py-2.5 text-white outline-none transition-colors"
              style={{
                background: "rgba(10,12,20,0.6)",
                border: "1px solid var(--border)",
              }}
              onFocus={(e) =>
                (e.currentTarget.style.borderColor = "var(--border-strong)")
              }
              onBlur={(e) =>
                (e.currentTarget.style.borderColor = "var(--border)")
              }
            />
            <span className="chip chip-mono whitespace-nowrap">
              {labelCount} sampel
            </span>
          </div>
        </div>

        {stage === "abjad" ? (
          <button
            type="button"
            onClick={() => void captureStatic()}
            disabled={!tracking.cameraOn || busy}
            className="btn btn-primary py-3"
          >
            ◉ Tangkap sampel ({tracking.handsDetected} tangan)
          </button>
        ) : (
          <button
            type="button"
            onClick={() => void toggleSequence()}
            disabled={!tracking.cameraOn || busy}
            className={`btn py-3 ${recording ? "btn-danger" : "btn-primary"}`}
          >
            {recording ? "■ Stop & simpan urutan" : "● Mulai rekam urutan"}
          </button>
        )}

        <button
          type="button"
          onClick={() => void onTrain()}
          disabled={busy || stage === "kalimat"}
          title={
            stage === "kalimat"
              ? "Tahap kalimat memakai LLM (Fase 5), bukan training classifier"
              : ""
          }
          className="btn btn-ghost"
        >
          ⚡ Latih model {stage === "kata" ? "kata" : "abjad"} ({mode})
        </button>

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

        {trainResult && !trainResult.note && (
          <div
            className="rounded-xl p-3 text-sm"
            style={{
              border: "1px solid rgba(52,211,153,0.25)",
              background: "rgba(6,78,59,0.25)",
              color: "#a7f3d0",
            }}
          >
            Train {(trainResult.train_accuracy * 100).toFixed(0)}% / Val{" "}
            {(trainResult.val_accuracy * 100).toFixed(0)}% · {trainResult.n_samples} sampel ·{" "}
            {trainResult.labels.join(", ")}
          </div>
        )}

        {Object.keys(labelsForStage).length > 0 && (
          <div>
            <p className="mb-2 text-xs font-semibold uppercase tracking-[0.14em] text-[var(--text-dim)]">
              Terkumpul ({mode}/{stage})
            </p>
            <div className="flex flex-wrap gap-1.5">
              {Object.entries(labelsForStage)
                .sort(([a], [b]) => a.localeCompare(b))
                .map(([lbl, count]) => (
                  <span key={lbl} className="chip chip-mono">
                    {lbl}
                    <span className="text-[var(--text-dim)]">{count}</span>
                  </span>
                ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
