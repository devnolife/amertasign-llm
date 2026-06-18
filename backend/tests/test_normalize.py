"""Tes regresi pipeline fitur landmark.

Termasuk guard untuk bug nyata: SIBI (max_hands=1) tidak boleh diikat ke slot
handedness tetap — kalau diikat, fitur jadi nol & classifier kolaps.
"""
from __future__ import annotations

import numpy as np

from app.ml.normalize import (
    FEATURES_PER_HAND,
    frame_to_features,
    max_hands_for_mode,
    resample_sequence,
    sequence_feature_vector,
)


def _hand(handedness: str, seed: int) -> dict:
    rng = np.random.default_rng(seed)
    pts = rng.uniform(-0.15, 0.15, (21, 3)).astype("float32")
    pts[0] = [0.5, 0.8, 0.0]  # wrist
    pts[9] = [0.5, 0.6, 0.0]  # middle_mcp (jarak stabil utk normalisasi)
    return {
        "handedness": handedness,
        "score": 1.0,
        "landmarks": [{"x": float(x), "y": float(y), "z": float(z)} for x, y, z in pts],
    }


def test_max_hands_mode():
    assert max_hands_for_mode("BISINDO") == 2
    assert max_hands_for_mode("SIBI") == 1


def test_single_hand_features_nonzero_regardless_of_handedness():
    # Regresi: tangan "Right" pada SIBI (max_hands=1) harus tetap menghasilkan fitur non-nol.
    feats_right = frame_to_features([_hand("Right", 1)], max_hands=1)
    feats_left = frame_to_features([_hand("Left", 1)], max_hands=1)
    assert feats_right.shape == (FEATURES_PER_HAND,)
    assert np.linalg.norm(feats_right) > 0.0  # BUG lama: ini nol
    assert np.linalg.norm(feats_left) > 0.0


def test_single_hand_picks_dominant_by_score():
    low = _hand("Left", 2)
    low["score"] = 0.2
    high = _hand("Right", 3)
    high["score"] = 0.9
    feats = frame_to_features([low, high], max_hands=1)
    expected = frame_to_features([high], max_hands=1)
    assert np.allclose(feats, expected)


def test_two_hands_concatenated_for_bisindo():
    feats = frame_to_features([_hand("Left", 4), _hand("Right", 5)], max_hands=2)
    assert feats.shape == (FEATURES_PER_HAND * 2,)
    # Kedua slot terisi (non-nol).
    assert np.linalg.norm(feats[:FEATURES_PER_HAND]) > 0.0
    assert np.linalg.norm(feats[FEATURES_PER_HAND:]) > 0.0


def test_missing_hand_slot_is_zero_for_bisindo():
    feats = frame_to_features([_hand("Right", 6)], max_hands=2)
    # Slot Left kosong → nol; slot Right terisi.
    assert np.linalg.norm(feats[:FEATURES_PER_HAND]) == 0.0
    assert np.linalg.norm(feats[FEATURES_PER_HAND:]) > 0.0


def test_resample_sequence_changes_length_preserves_dim():
    seq = np.random.default_rng(0).random((23, FEATURES_PER_HAND)).astype("float32")
    out = resample_sequence(seq, 16)
    assert out.shape == (16, FEATURES_PER_HAND)


def test_sequence_feature_vector_fixed_length():
    frames = [[_hand("Left", i), _hand("Right", i + 100)] for i in range(13)]
    vec = sequence_feature_vector(frames, max_hands=2, seq_len=16)
    assert vec.shape == (16 * FEATURES_PER_HAND * 2,)
