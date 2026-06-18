"""Normalisasi landmark tangan menjadi vektor fitur.

Tujuan: membuat fitur yang invarian terhadap translasi & skala (posisi tangan di
frame dan jarak ke kamera) sehingga model lebih robust.

Skema fitur:
- Tiap tangan: 21 titik (x, y, z) digeser relatif ke wrist (titik 0), lalu diskalakan
  dengan jarak wrist -> middle_finger_mcp (titik 9). Hasil: vektor 63 dimensi.
- Frame digabung mengikuti slot handedness yang konsisten: [Left, Right]. Tangan yang
  tidak terdeteksi diisi nol. BISINDO -> max_hands=2 (126 dim), SIBI -> max_hands=1 (63 dim).
"""
from __future__ import annotations

from typing import Iterable, Sequence

import numpy as np

WRIST = 0
MIDDLE_FINGER_MCP = 9
NUM_LANDMARKS = 21
FEATURES_PER_HAND = NUM_LANDMARKS * 3  # 63
HAND_ORDER = ("Left", "Right")


def _hand_to_array(landmarks: Sequence) -> np.ndarray:
    """Ubah daftar landmark (objek dengan .x/.y/.z atau dict) -> array (21, 3)."""
    pts = np.empty((NUM_LANDMARKS, 3), dtype=np.float32)
    for i, lm in enumerate(landmarks):
        if isinstance(lm, dict):
            pts[i] = (lm["x"], lm["y"], lm.get("z", 0.0))
        else:
            pts[i] = (lm.x, lm.y, getattr(lm, "z", 0.0))
    return pts


def normalize_hand(landmarks: Sequence) -> np.ndarray:
    """Normalisasi satu tangan -> vektor fitur (63,)."""
    pts = _hand_to_array(landmarks)
    # Translasi: jadikan wrist sebagai origin
    pts = pts - pts[WRIST]
    # Skala: jarak wrist -> middle_finger_mcp
    scale = np.linalg.norm(pts[MIDDLE_FINGER_MCP])
    if scale < 1e-6:
        scale = 1.0
    pts = pts / scale
    return pts.reshape(-1).astype(np.float32)


def frame_to_features(hands: Iterable, max_hands: int = 2) -> np.ndarray:
    """Gabungkan tangan-tangan dalam satu frame -> vektor fitur fixed-length.

    - max_hands == 1 (mis. SIBI): pakai SATU tangan dominan (skor tertinggi),
      tanpa peduli handedness. Mengikat ke slot handedness justru membuang tangan
      bila label-nya tak sesuai slot.
    - max_hands >= 2 (mis. BISINDO): pakai slot terurut [Left, Right]; slot kosong
      diisi nol sehingga posisi relatif kedua tangan konsisten.
    """
    hands = list(hands)

    if max_hands == 1:
        if not hands:
            return np.zeros(FEATURES_PER_HAND, dtype=np.float32)

        def _score(h):
            return h["score"] if isinstance(h, dict) else getattr(h, "score", 1.0)

        best = max(hands, key=_score)
        landmarks = best["landmarks"] if isinstance(best, dict) else best.landmarks
        return normalize_hand(landmarks)

    slots = {name: np.zeros(FEATURES_PER_HAND, dtype=np.float32) for name in HAND_ORDER}
    for hand in hands:
        handedness = hand["handedness"] if isinstance(hand, dict) else hand.handedness
        landmarks = hand["landmarks"] if isinstance(hand, dict) else hand.landmarks
        if handedness in slots:
            slots[handedness] = normalize_hand(landmarks)

    ordered = [slots[name] for name in HAND_ORDER[:max_hands]]
    return np.concatenate(ordered, axis=0)


def max_hands_for_mode(mode: str) -> int:
    """BISINDO umumnya dua tangan; SIBI (abjad) satu tangan."""
    return 2 if mode == "BISINDO" else 1


def sequence_to_features(frames: Iterable[Iterable], max_hands: int = 2) -> np.ndarray:
    """Ubah urutan frame -> array (T, F) untuk model temporal."""
    feats = [frame_to_features(frame, max_hands=max_hands) for frame in frames]
    if not feats:
        return np.zeros((0, FEATURES_PER_HAND * max_hands), dtype=np.float32)
    return np.stack(feats, axis=0)
