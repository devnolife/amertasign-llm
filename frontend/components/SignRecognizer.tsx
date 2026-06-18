"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import CameraView from "@/components/CameraView";
import Controls from "@/components/Controls";
import RecognitionPanel from "@/components/RecognitionPanel";
import { useHandTracking } from "@/hooks/useHandTracking";
import { RecognitionSocket, type SocketStatus } from "@/lib/api";
import { SEND_INTERVAL_MS } from "@/lib/config";
import type { HandLandmarks, Mode, RecognitionResult, Stage } from "@/lib/types";

export default function SignRecognizer() {
  const [mode, setMode] = useState<Mode>("BISINDO");
  const [stage, setStage] = useState<Stage>("abjad");
  const [socketStatus, setSocketStatus] = useState<SocketStatus>("closed");
  const [result, setResult] = useState<RecognitionResult | null>(null);

  const socketRef = useRef<RecognitionSocket | null>(null);
  const modeRef = useRef<Mode>(mode);
  const stageRef = useRef<Stage>(stage);
  const lastSendRef = useRef(0);

  useEffect(() => {
    modeRef.current = mode;
  }, [mode]);
  useEffect(() => {
    stageRef.current = stage;
  }, [stage]);

  const handleFrame = useCallback((hands: HandLandmarks[], now: number) => {
    if (now - lastSendRef.current < SEND_INTERVAL_MS) return;
    lastSendRef.current = now;
    socketRef.current?.send({
      mode: modeRef.current,
      stage: stageRef.current,
      hands,
      timestamp: now,
    });
  }, []);

  const tracking = useHandTracking({ onFrame: handleFrame });

  const startCamera = useCallback(async () => {
    const socket = new RecognitionSocket(setResult, setSocketStatus);
    socket.connect();
    socketRef.current = socket;
    await tracking.start();
  }, [tracking]);

  const stopCamera = useCallback(() => {
    tracking.stop();
    socketRef.current?.close();
    socketRef.current = null;
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
          onStageChange={setStage}
          onToggleCamera={toggleCamera}
        />
        <RecognitionPanel
          result={result}
          handsDetected={tracking.handsDetected}
        />
      </div>
    </div>
  );
}
