"use client";

import type { HandTracking } from "@/hooks/useHandTracking";

interface Props {
  tracking: HandTracking;
  hint?: string;
}

/** Tampilan webcam + overlay kerangka tangan (dipakai recognizer & recorder). */
export default function CameraView({ tracking, hint }: Props) {
  const { videoRef, canvasRef, cameraOn, loading, error, fps, handsDetected } =
    tracking;

  return (
    <div>
      <div
        className="relative aspect-video w-full overflow-hidden rounded-3xl"
        style={{
          background: "#04050a",
          border: "1px solid var(--border)",
          boxShadow: cameraOn
            ? "0 0 60px -18px rgba(34,211,238,0.35), 0 30px 70px -40px rgba(0,0,0,0.9)"
            : "0 30px 70px -40px rgba(0,0,0,0.9)",
          transition: "box-shadow 0.5s ease",
        }}
      >
        <video
          ref={videoRef}
          playsInline
          muted
          className="absolute inset-0 h-full w-full object-cover -scale-x-100"
        />
        <canvas
          ref={canvasRef}
          className="absolute inset-0 h-full w-full object-cover -scale-x-100"
        />

        {/* Bracket sudut ala viewfinder */}
        <CornerBrackets active={cameraOn} />

        {cameraOn && <div className="scanline" aria-hidden />}

        {!cameraOn && !loading && (
          <div className="absolute inset-0 flex flex-col items-center justify-center gap-3 text-[var(--text-dim)]">
            <span
              className="grid h-16 w-16 place-items-center rounded-2xl"
              style={{
                border: "1px solid var(--border)",
                background: "rgba(148,163,216,0.05)",
              }}
            >
              <CameraIcon />
            </span>
            <p className="max-w-xs text-center text-sm">
              {hint ?? 'Kamera mati — tekan "Mulai kamera"'}
            </p>
          </div>
        )}

        {cameraOn && (
          <div className="absolute top-4 left-4 flex items-center gap-2">
            <span className="chip chip-mono border-none bg-black/60 backdrop-blur">
              <span className="dot-live h-1.5 w-1.5 rounded-full bg-emerald-400" />
              LIVE
            </span>
            <span className="chip chip-mono border-none bg-black/60 backdrop-blur">
              {fps} FPS
            </span>
            <span className="chip chip-mono border-none bg-black/60 backdrop-blur">
              {handsDetected} tangan
            </span>
          </div>
        )}
      </div>

      {error && (
        <div
          className="mt-3 rounded-xl p-3 text-sm"
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

function CornerBrackets({ active }: { active: boolean }) {
  const color = active ? "rgba(34,211,238,0.65)" : "rgba(148,163,216,0.25)";
  const size = 26;
  const common: React.CSSProperties = {
    position: "absolute",
    width: size,
    height: size,
    borderColor: color,
    borderStyle: "solid",
    borderWidth: 0,
    transition: "border-color 0.5s ease",
    pointerEvents: "none",
  };
  return (
    <>
      <span style={{ ...common, top: 14, left: 14, borderTopWidth: 2, borderLeftWidth: 2, borderTopLeftRadius: 10 }} />
      <span style={{ ...common, top: 14, right: 14, borderTopWidth: 2, borderRightWidth: 2, borderTopRightRadius: 10 }} />
      <span style={{ ...common, bottom: 14, left: 14, borderBottomWidth: 2, borderLeftWidth: 2, borderBottomLeftRadius: 10 }} />
      <span style={{ ...common, bottom: 14, right: 14, borderBottomWidth: 2, borderRightWidth: 2, borderBottomRightRadius: 10 }} />
    </>
  );
}

function CameraIcon() {
  return (
    <svg
      width="32"
      height="32"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z" />
      <circle cx="12" cy="13" r="4" />
    </svg>
  );
}
