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
      className={`seg flex-1 ${active ? "seg--active" : ""}`}
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
    <div className="card flex flex-col gap-5 p-5">
      <div>
        <p className="mb-2 text-xs font-semibold uppercase tracking-[0.14em] text-[var(--text-dim)]">
          Sistem isyarat
        </p>
        <div className="seg-group">
          {MODES.map((m) => (
            <SegButton key={m} active={mode === m} onClick={() => onModeChange(m)}>
              {m}
            </SegButton>
          ))}
        </div>
      </div>

      <div>
        <p className="mb-2 text-xs font-semibold uppercase tracking-[0.14em] text-[var(--text-dim)]">
          Tahap
        </p>
        <div className="seg-group">
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
          className={`btn ${cameraOn ? "btn-danger" : "btn-success"}`}
        >
          {loading ? "Memuat…" : cameraOn ? "■ Stop kamera" : "▶ Mulai kamera"}
        </button>

        <span className="chip chip-mono">
          <span className={`h-2 w-2 rounded-full ${status.dot}`} />
          {status.label}
        </span>
      </div>
    </div>
  );
}
