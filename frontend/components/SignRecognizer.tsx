"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { HandLandmarker } from "@mediapipe/tasks-vision";

import Controls from "@/components/Controls";
import RecognitionPanel from "@/components/RecognitionPanel";
import { RecognitionSocket, type SocketStatus } from "@/lib/api";
import { SEND_INTERVAL_MS } from "@/lib/config";
import { drawHands } from "@/lib/draw";
import { createHandLandmarker, toHandLandmarks } from "@/lib/mediapipe";
import type { HandLandmarks, Mode, RecognitionResult, Stage } from "@/lib/types";

export default function SignRecognizer() {
  const [mode, setMode] = useState<Mode>("BISINDO");
  const [stage, setStage] = useState<Stage>("abjad");
  const [cameraOn, setCameraOn] = useState(false);
  const [loading, setLoading] = useState(false);
  const [socketStatus, setSocketStatus] = useState<SocketStatus>("closed");
  const [result, setResult] = useState<RecognitionResult | null>(null);
  const [handsDetected, setHandsDetected] = useState(0);
  const [fps, setFps] = useState(0);
  const [error, setError] = useState<string | null>(null);

  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const landmarkerRef = useRef<HandLandmarker | null>(null);
  const socketRef = useRef<RecognitionSocket | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const rafRef = useRef<number | null>(null);

  const modeRef = useRef<Mode>(mode);
  const stageRef = useRef<Stage>(stage);
  const lastVideoTimeRef = useRef(-1);
  const lastSendRef = useRef(0);
  const frameTimesRef = useRef<number[]>([]);

  useEffect(() => {
    modeRef.current = mode;
  }, [mode]);
  useEffect(() => {
    stageRef.current = stage;
  }, [stage]);

  const predict = useCallback(() => {
    const video = videoRef.current;
    const canvas = canvasRef.current;
    const landmarker = landmarkerRef.current;
    if (!video || !canvas || !landmarker || video.readyState < 2) {
      rafRef.current = requestAnimationFrame(predict);
      return;
    }

    if (canvas.width !== video.videoWidth || canvas.height !== video.videoHeight) {
      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;
    }

    const now = performance.now();
    let hands: HandLandmarks[] = [];

    // MediaPipe membutuhkan timestamp naik & frame baru.
    if (video.currentTime !== lastVideoTimeRef.current) {
      lastVideoTimeRef.current = video.currentTime;
      const detection = landmarker.detectForVideo(video, now);
      hands = toHandLandmarks(detection);

      const ctx = canvas.getContext("2d");
      if (ctx) drawHands(ctx, hands, canvas.width, canvas.height);
      setHandsDetected(hands.length);

      // Kirim ke backend (throttle).
      if (now - lastSendRef.current >= SEND_INTERVAL_MS) {
        lastSendRef.current = now;
        socketRef.current?.send({
          mode: modeRef.current,
          stage: stageRef.current,
          hands,
          timestamp: now,
        });
      }
    }

    // FPS (rata-rata 1 detik terakhir).
    const times = frameTimesRef.current;
    times.push(now);
    while (times.length > 0 && times[0] <= now - 1000) times.shift();
    setFps(times.length);

    rafRef.current = requestAnimationFrame(predict);
  }, []);

  const startCamera = useCallback(async () => {
    setError(null);
    setLoading(true);
    try {
      if (!landmarkerRef.current) {
        try {
          landmarkerRef.current = await createHandLandmarker(2, "GPU");
        } catch {
          landmarkerRef.current = await createHandLandmarker(2, "CPU");
        }
      }

      const stream = await navigator.mediaDevices.getUserMedia({
        video: { width: 1280, height: 720, facingMode: "user" },
        audio: false,
      });
      streamRef.current = stream;
      const video = videoRef.current;
      if (!video) throw new Error("Elemen video tidak tersedia.");
      video.srcObject = stream;
      await video.play();

      const socket = new RecognitionSocket(setResult, setSocketStatus);
      socket.connect();
      socketRef.current = socket;

      setCameraOn(true);
      lastVideoTimeRef.current = -1;
      rafRef.current = requestAnimationFrame(predict);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Gagal mengakses kamera. Pastikan izin kamera diberikan.",
      );
    } finally {
      setLoading(false);
    }
  }, [predict]);

  const stopCamera = useCallback(() => {
    if (rafRef.current !== null) cancelAnimationFrame(rafRef.current);
    rafRef.current = null;
    streamRef.current?.getTracks().forEach((t) => t.stop());
    streamRef.current = null;
    socketRef.current?.close();
    socketRef.current = null;
    if (videoRef.current) videoRef.current.srcObject = null;
    const canvas = canvasRef.current;
    canvas?.getContext("2d")?.clearRect(0, 0, canvas.width, canvas.height);
    setCameraOn(false);
    setResult(null);
    setHandsDetected(0);
    setFps(0);
  }, []);

  const toggleCamera = useCallback(() => {
    if (cameraOn) stopCamera();
    else void startCamera();
  }, [cameraOn, startCamera, stopCamera]);

  useEffect(() => {
    return () => stopCamera();
  }, [stopCamera]);

  return (
    <div className="grid gap-6 lg:grid-cols-[1fr_360px]">
      <div className="relative">
        <div className="relative aspect-video w-full overflow-hidden rounded-2xl bg-zinc-950 border border-zinc-800">
          {/* video + overlay di-mirror bersama agar tampak natural & selaras */}
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
              <p>Kamera mati — tekan &quot;Mulai kamera&quot;</p>
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

      <div className="flex flex-col gap-6">
        <Controls
          mode={mode}
          stage={stage}
          cameraOn={cameraOn}
          loading={loading}
          socketStatus={socketStatus}
          onModeChange={setMode}
          onStageChange={setStage}
          onToggleCamera={toggleCamera}
        />
        <RecognitionPanel result={result} handsDetected={handsDetected} />
      </div>
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
