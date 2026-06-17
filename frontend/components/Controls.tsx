"use client";

import type { Mode, Stage } from "@/lib/types";
import type { SocketStatus } from "@/lib/api";

const MODES: Mode[] = ["BISINDO", "SIBI"];
const STAGES: { value: Stage; label: string }[] = [
  { value: "abjad", label: "Abjad" },
  { value: "kata", label: "Kata" },
  { value: "kalimat", label: "Kalimat" },
];

const STATUS_META: Record<SocketStatus, { label: string; dot: string }> = {
  connecting: { label: "Menyambung…", dot: "bg-amber-400" },
  open: { label: "Terhubung", dot: "bg-emerald-400" },
  closed: { label: "Terputus", dot: "bg-zinc-500" },
  error: { label: "Error", dot: "bg-rose-500" },
};

interface Props {
  mode: Mode;
  stage: Stage;
  cameraOn: boolean;
  loading: boolean;
  socketStatus: SocketStatus;
  onModeChange: (mode: Mode) => void;
  onStageChange: (stage: Stage) => void;
  onToggleCamera: () => void;
}

function SegButton({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors ${
        active
          ? "bg-violet-600 text-white shadow"
          : "bg-zinc-800 text-zinc-300 hover:bg-zinc-700"
      }`}
    >
      {children}
    </button>
  );
}

export default function Controls({
  mode,
  stage,
  cameraOn,
  loading,
  socketStatus,
  onModeChange,
  onStageChange,
  onToggleCamera,
}: Props) {
  const status = STATUS_META[socketStatus];

  return (
    <div className="flex flex-col gap-5">
      <div>
        <p className="text-xs uppercase tracking-wide text-zinc-500 mb-2">
          Sistem isyarat
        </p>
        <div className="flex gap-2">
          {MODES.map((m) => (
            <SegButton key={m} active={mode === m} onClick={() => onModeChange(m)}>
              {m}
            </SegButton>
          ))}
        </div>
      </div>

      <div>
        <p className="text-xs uppercase tracking-wide text-zinc-500 mb-2">
          Tahap
        </p>
        <div className="flex gap-2">
          {STAGES.map((s) => (
            <SegButton
              key={s.value}
              active={stage === s.value}
              onClick={() => onStageChange(s.value)}
            >
              {s.label}
            </SegButton>
          ))}
        </div>
      </div>

      <div className="flex items-center justify-between pt-1">
        <button
          type="button"
          onClick={onToggleCamera}
          disabled={loading}
          className={`px-5 py-2.5 rounded-lg font-semibold transition-colors disabled:opacity-60 ${
            cameraOn
              ? "bg-rose-600 hover:bg-rose-500 text-white"
              : "bg-emerald-600 hover:bg-emerald-500 text-white"
          }`}
        >
          {loading ? "Memuat…" : cameraOn ? "Stop kamera" : "Mulai kamera"}
        </button>

        <span className="flex items-center gap-2 text-sm text-zinc-400">
          <span className={`h-2.5 w-2.5 rounded-full ${status.dot}`} />
          {status.label}
        </span>
      </div>
    </div>
  );
}
