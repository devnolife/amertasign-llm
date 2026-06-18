"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { HandLandmarker } from "@mediapipe/tasks-vision";

import { drawHands } from "@/lib/draw";
import { createHandLandmarker, toHandLandmarks } from "@/lib/mediapipe";
import type { HandLandmarks } from "@/lib/types";

interface Options {
  // Dipanggil tiap frame baru terdeteksi (untuk kirim ke backend / rekam).
  onFrame?: (hands: HandLandmarks[], now: number) => void;
}

export interface HandTracking {
  videoRef: React.RefObject<HTMLVideoElement | null>;
  canvasRef: React.RefObject<HTMLCanvasElement | null>;
  latestHandsRef: React.RefObject<HandLandmarks[]>;
  cameraOn: boolean;
  loading: boolean;
  error: string | null;
  fps: number;
  handsDetected: number;
  start: () => Promise<void>;
  stop: () => void;
}

/**
 * Hook bersama: mengelola webcam + MediaPipe HandLandmarker, menggambar overlay,
 * dan memaparkan landmark terbaru. Dipakai oleh recognizer & recorder.
 */
export function useHandTracking(options: Options = {}): HandTracking {
  const { onFrame } = options;

  const [cameraOn, setCameraOn] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [fps, setFps] = useState(0);
  const [handsDetected, setHandsDetected] = useState(0);

  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const latestHandsRef = useRef<HandLandmarks[]>([]);

  const landmarkerRef = useRef<HandLandmarker | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const rafRef = useRef<number | null>(null);
  const lastVideoTimeRef = useRef(-1);
  const frameTimesRef = useRef<number[]>([]);
  const onFrameRef = useRef(onFrame);
  const loopRef = useRef<() => void>(() => {});

  useEffect(() => {
    onFrameRef.current = onFrame;
  }, [onFrame]);

  // Loop rAF disimpan di ref agar dapat menjadwalkan dirinya sendiri tanpa
  // mereferensikan binding yang belum dideklarasikan.
  useEffect(() => {
    loopRef.current = () => {
      const video = videoRef.current;
      const canvas = canvasRef.current;
      const landmarker = landmarkerRef.current;
      if (!video || !canvas || !landmarker || video.readyState < 2) {
        rafRef.current = requestAnimationFrame(() => loopRef.current());
        return;
      }

      if (
        canvas.width !== video.videoWidth ||
        canvas.height !== video.videoHeight
      ) {
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
      }

      const now = performance.now();

      if (video.currentTime !== lastVideoTimeRef.current) {
        lastVideoTimeRef.current = video.currentTime;
        const detection = landmarker.detectForVideo(video, now);
        const hands = toHandLandmarks(detection);
        latestHandsRef.current = hands;

        const ctx = canvas.getContext("2d");
        if (ctx) drawHands(ctx, hands, canvas.width, canvas.height);
        setHandsDetected(hands.length);
        onFrameRef.current?.(hands, now);
      }

      const times = frameTimesRef.current;
      times.push(now);
      while (times.length > 0 && times[0] <= now - 1000) times.shift();
      setFps(times.length);

      rafRef.current = requestAnimationFrame(() => loopRef.current());
    };
  }, []);

  const start = useCallback(async () => {
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

      setCameraOn(true);
      lastVideoTimeRef.current = -1;
      rafRef.current = requestAnimationFrame(() => loopRef.current());
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Gagal mengakses kamera. Pastikan izin kamera diberikan.",
      );
    } finally {
      setLoading(false);
    }
  }, []);

  const stop = useCallback(() => {
    if (rafRef.current !== null) cancelAnimationFrame(rafRef.current);
    rafRef.current = null;
    streamRef.current?.getTracks().forEach((t) => t.stop());
    streamRef.current = null;
    if (videoRef.current) videoRef.current.srcObject = null;
    const canvas = canvasRef.current;
    canvas?.getContext("2d")?.clearRect(0, 0, canvas.width, canvas.height);
    latestHandsRef.current = [];
    setCameraOn(false);
    setHandsDetected(0);
    setFps(0);
  }, []);

  useEffect(() => {
    return () => stop();
  }, [stop]);

  return {
    videoRef,
    canvasRef,
    latestHandsRef,
    cameraOn,
    loading,
    error,
    fps,
    handsDetected,
    start,
    stop,
  };
}
