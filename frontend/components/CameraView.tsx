"use client";

import type { HandTracking } from "@/hooks/useHandTracking";

interface Props {
  tracking: HandTracking;
  hint?: string;
}

/** Tampilan webcam + overlay kerangka tangan (dipakai recognizer & recorder). */
export default function CameraView({ tracking, hint }: Props) {
  const { videoRef, canvasRef, cameraOn, loading, error, fps } = tracking;

  return (
    <div>
      <div className="relative aspect-video w-full overflow-hidden rounded-2xl bg-zinc-950 border border-zinc-800">
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

        {!cameraOn && !loading && (
          <div className="absolute inset-0 flex flex-col items-center justify-center gap-2 text-zinc-500">
            <CameraIcon />
            <p>{hint ?? 'Kamera mati — tekan "Mulai kamera"'}</p>
          </div>
        )}

        {cameraOn && (
          <span className="absolute top-3 left-3 rounded-md bg-black/60 px-2 py-1 text-xs text-zinc-300">
            {fps} FPS
          </span>
        )}
      </div>

      {error && (
        <div className="mt-3 rounded-lg bg-rose-950/50 border border-rose-900/60 p-3 text-sm text-rose-200">
          {error}
        </div>
      )}
    </div>
  );
}

function CameraIcon() {
  return (
    <svg
      width="48"
      height="48"
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
