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
    setBusy(true);
    setMessage(null);
    setTrainResult(null);
    try {
      const res = await trainModel(mode, "abjad");
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
  }, [mode]);

  const labelsForStage = stats?.counts?.[mode]?.[stage] ?? {};

  return (
    <div className="grid gap-6 lg:grid-cols-[1fr_360px]">
      <CameraView
        tracking={tracking}
        hint='Kamera mati — tekan "Mulai kamera" untuk merekam'
      />

      <div className="flex flex-col gap-5">
        {!tracking.cameraOn ? (
          <button
            type="button"
            onClick={() => void tracking.start()}
            disabled={tracking.loading}
            className="px-5 py-2.5 rounded-lg font-semibold bg-emerald-600 hover:bg-emerald-500 text-white disabled:opacity-60"
          >
            {tracking.loading ? "Memuat…" : "Mulai kamera"}
          </button>
        ) : (
          <button
            type="button"
            onClick={tracking.stop}
            className="px-5 py-2.5 rounded-lg font-semibold bg-rose-600 hover:bg-rose-500 text-white"
          >
            Stop kamera
          </button>
        )}

        <div className="flex gap-2">
          {MODES.map((m) => (
            <button
              key={m}
              type="button"
              onClick={() => setMode(m)}
              className={`flex-1 px-3 py-2 text-sm rounded-lg ${
                mode === m
                  ? "bg-violet-600 text-white"
                  : "bg-zinc-800 text-zinc-300 hover:bg-zinc-700"
              }`}
            >
              {m}
            </button>
          ))}
        </div>

        <div className="flex gap-2">
          {STAGES.map((s) => (
            <button
              key={s.value}
              type="button"
              onClick={() => setStage(s.value)}
              className={`flex-1 px-3 py-2 text-sm rounded-lg ${
                stage === s.value
                  ? "bg-violet-600 text-white"
                  : "bg-zinc-800 text-zinc-300 hover:bg-zinc-700"
              }`}
            >
              {s.label}
            </button>
          ))}
        </div>

        <div>
          <label className="text-xs uppercase tracking-wide text-zinc-500">
            Label {stage === "abjad" ? "(huruf/angka)" : "(kata)"}
          </label>
          <div className="mt-1 flex items-center gap-2">
            <input
              value={label}
              onChange={(e) => setLabel(e.target.value)}
              placeholder={stage === "abjad" ? "A" : "makan"}
              className="flex-1 rounded-lg bg-zinc-900 border border-zinc-700 px-3 py-2 text-white focus:border-violet-500 focus:outline-none"
            />
            <span className="text-sm text-zinc-400 whitespace-nowrap">
              {labelCount} sampel
            </span>
          </div>
        </div>

        {stage === "abjad" ? (
          <button
            type="button"
            onClick={() => void captureStatic()}
            disabled={!tracking.cameraOn || busy}
            className="px-5 py-3 rounded-lg font-semibold bg-violet-600 hover:bg-violet-500 text-white disabled:opacity-50"
          >
            Tangkap sampel ({tracking.handsDetected} tangan)
          </button>
        ) : (
          <button
            type="button"
            onClick={() => void toggleSequence()}
            disabled={!tracking.cameraOn || busy}
            className={`px-5 py-3 rounded-lg font-semibold text-white disabled:opacity-50 ${
              recording
                ? "bg-rose-600 hover:bg-rose-500"
                : "bg-violet-600 hover:bg-violet-500"
            }`}
          >
            {recording ? "Stop & simpan urutan" : "Mulai rekam urutan"}
          </button>
        )}

        <button
          type="button"
          onClick={() => void onTrain()}
          disabled={busy || stage !== "abjad"}
          title={stage !== "abjad" ? "Training otomatis tersedia untuk abjad" : ""}
          className="px-5 py-2.5 rounded-lg font-medium bg-zinc-800 hover:bg-zinc-700 text-zinc-100 disabled:opacity-50"
        >
          Latih model abjad ({mode})
        </button>

        {message && (
          <div className="rounded-lg bg-zinc-900 border border-zinc-800 p-3 text-sm text-zinc-300">
            {message}
          </div>
        )}

        {trainResult && !trainResult.note && (
          <div className="rounded-lg bg-emerald-950/40 border border-emerald-900/50 p-3 text-sm text-emerald-200">
            Train {(trainResult.train_accuracy * 100).toFixed(0)}% / Val{" "}
            {(trainResult.val_accuracy * 100).toFixed(0)}% · {trainResult.n_samples} sampel ·{" "}
            {trainResult.labels.join(", ")}
          </div>
        )}

        {Object.keys(labelsForStage).length > 0 && (
          <div>
            <p className="text-xs uppercase tracking-wide text-zinc-500 mb-2">
              Terkumpul ({mode}/{stage})
            </p>
            <div className="flex flex-wrap gap-1.5">
              {Object.entries(labelsForStage)
                .sort(([a], [b]) => a.localeCompare(b))
                .map(([lbl, count]) => (
                  <span
                    key={lbl}
                    className="px-2 py-1 rounded-md bg-zinc-800 text-xs text-zinc-300"
                  >
                    {lbl} <span className="text-zinc-500">{count}</span>
                  </span>
                ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
