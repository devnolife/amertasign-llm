"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import CameraView from "@/components/CameraView";
import Controls from "@/components/Controls";
import RecognitionPanel from "@/components/RecognitionPanel";
import { useHandTracking } from "@/hooks/useHandTracking";
import {
  RecognitionSocket,
  recognizeSequence,
  type SocketStatus,
} from "@/lib/api";
import {
  SEND_INTERVAL_MS,
  SEQ_GAP_FRAMES,
  SEQ_MAX_FRAMES,
  SEQ_MIN_FRAMES,
} from "@/lib/config";
import type { HandLandmarks, Mode, RecognitionResult, Stage } from "@/lib/types";

export default function SignRecognizer() {
  const [mode, setMode] = useState<Mode>("BISINDO");
  const [stage, setStage] = useState<Stage>("abjad");
  const [socketStatus, setSocketStatus] = useState<SocketStatus>("closed");
  const [result, setResult] = useState<RecognitionResult | null>(null);
  const [capturing, setCapturing] = useState(false);

  const socketRef = useRef<RecognitionSocket | null>(null);
  const modeRef = useRef<Mode>(mode);
  const stageRef = useRef<Stage>(stage);
  const lastSendRef = useRef(0);

  // Buffer segmentasi untuk mode kata.
  const seqBufferRef = useRef<HandLandmarks[][]>([]);
  const gapRef = useRef(0);
  const inflightRef = useRef(false);

  useEffect(() => {
    modeRef.current = mode;
  }, [mode]);
  useEffect(() => {
    stageRef.current = stage;
  }, [stage]);

  const handleStageChange = useCallback((next: Stage) => {
    // Reset buffer segmentasi saat berganti tahap (di event handler, bukan effect).
    seqBufferRef.current = [];
    gapRef.current = 0;
    setCapturing(false);
    setStage(next);
  }, []);

  const finalizeSegment = useCallback(async () => {
    const frames = seqBufferRef.current;
    seqBufferRef.current = [];
    gapRef.current = 0;
    setCapturing(false);
    if (frames.length < SEQ_MIN_FRAMES || inflightRef.current) return;
    inflightRef.current = true;
    try {
      const res = await recognizeSequence(modeRef.current, "kata", frames);
      setResult(res);
    } catch {
      /* backend mungkin belum jalan / model belum ada */
    } finally {
      inflightRef.current = false;
    }
  }, []);

  const handleFrame = useCallback(
    (hands: HandLandmarks[], now: number) => {
      // Mode abjad/kalimat: streaming per-frame via WebSocket.
      if (stageRef.current !== "kata") {
        if (now - lastSendRef.current < SEND_INTERVAL_MS) return;
        lastSendRef.current = now;
        socketRef.current?.send({
          mode: modeRef.current,
          stage: stageRef.current,
          hands,
          timestamp: now,
        });
        return;
      }

      // Mode kata: segmentasi berbasis kehadiran tangan.
      if (hands.length > 0) {
        gapRef.current = 0;
        if (seqBufferRef.current.length < SEQ_MAX_FRAMES) {
          seqBufferRef.current.push(hands);
          setCapturing(true);
        } else {
          void finalizeSegment();
        }
      } else if (seqBufferRef.current.length > 0) {
        gapRef.current += 1;
        if (gapRef.current >= SEQ_GAP_FRAMES) {
          void finalizeSegment();
        }
      }
    },
    [finalizeSegment],
  );

  const tracking = useHandTracking({ onFrame: handleFrame });

  const startCamera = useCallback(async () => {
    const socket = new RecognitionSocket(setResult, setSocketStatus);
    socket.connect();
    socketRef.current = socket;
    seqBufferRef.current = [];
    gapRef.current = 0;
    await tracking.start();
  }, [tracking]);

  const stopCamera = useCallback(() => {
    tracking.stop();
    socketRef.current?.close();
    socketRef.current = null;
    seqBufferRef.current = [];
    gapRef.current = 0;
    setCapturing(false);
    setResult(null);
  }, [tracking]);

  const toggleCamera = useCallback(() => {
    if (tracking.cameraOn) stopCamera();
    else void startCamera();
  }, [tracking.cameraOn, startCamera, stopCamera]);

  return (
    <div className="grid gap-6 lg:grid-cols-[1fr_360px]">
      <CameraView tracking={tracking} />

      <div className="flex flex-col gap-6">
        <Controls
          mode={mode}
          stage={stage}
          cameraOn={tracking.cameraOn}
          loading={tracking.loading}
          socketStatus={socketStatus}
          onModeChange={setMode}
          onStageChange={handleStageChange}
          onToggleCamera={toggleCamera}
        />
        <RecognitionPanel
          result={result}
          handsDetected={tracking.handsDetected}
          capturing={stage === "kata" && capturing}
        />
      </div>
    </div>
  );
}
