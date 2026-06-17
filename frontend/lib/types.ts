// Tipe bersama yang mencerminkan kontrak backend (lihat docs/api-contract.md).

export type Mode = "BISINDO" | "SIBI";
export type Stage = "abjad" | "kata" | "kalimat";
export type Handedness = "Left" | "Right";

export interface Landmark {
  x: number;
  y: number;
  z: number;
}

export interface HandLandmarks {
  handedness: Handedness;
  score: number;
  landmarks: Landmark[]; // panjang 21
}

export interface FramePayload {
  mode: Mode;
  stage: Stage;
  hands: HandLandmarks[];
  timestamp?: number;
}

export interface Candidate {
  label: string;
  confidence: number;
}

export interface RecognitionResult {
  text: string;
  confidence: number;
  candidates: Candidate[];
  mode: Mode;
  stage: Stage;
  model_loaded: boolean;
  note?: string;
}

export const STAGE_LABELS: Record<Stage, string> = {
  abjad: "Abjad",
  kata: "Kata",
  kalimat: "Kalimat",
};
