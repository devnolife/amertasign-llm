# Skema Landmark (kontrak frontend ↔ backend)

Frontend mengekstraksi landmark tangan **di browser** menggunakan MediaPipe
HandLandmarker (Tasks Vision), lalu mengirim koordinatnya ke backend. Video mentah
**tidak** dikirim (hemat bandwidth + privasi).

## Titik landmark

Setiap tangan memiliki **21 titik** (indeks MediaPipe Hands):

```
0  wrist
1-4   ibu jari (thumb): cmc, mcp, ip, tip
5-8   telunjuk (index): mcp, pip, dip, tip
9-12  jari tengah (middle): mcp, pip, dip, tip
13-16 jari manis (ring): mcp, pip, dip, tip
17-20 kelingking (pinky): mcp, pip, dip, tip
```

Setiap titik: `{ "x": float, "y": float, "z": float }`
- `x`, `y` ternormalisasi 0..1 terhadap lebar/tinggi frame.
- `z` kedalaman relatif (perkiraan), origin di wrist.

## Objek tangan

```json
{
  "handedness": "Left | Right",
  "score": 0.98,
  "landmarks": [ { "x": .., "y": .., "z": .. }, ... 21 titik ]
}
```

> Catatan: MediaPipe melaporkan handedness dari sudut pandang kamera (gambar
> di-mirror). Frontend & backend harus konsisten memakai label yang sama.

## Normalisasi fitur (backend)

`app/ml/normalize.py` mengubah landmark menjadi vektor fitur yang invarian:
1. Geser semua titik relatif ke **wrist** (titik 0).
2. Skalakan dengan jarak **wrist → middle_finger_mcp** (titik 9).
3. Flatten → 63 dim per tangan.
4. Gabung slot `[Left, Right]` (zero-pad bila tangan tak terdeteksi):
   - **BISINDO**: 2 tangan → 126 dim.
   - **SIBI** (abjad): 1 tangan → 63 dim.
