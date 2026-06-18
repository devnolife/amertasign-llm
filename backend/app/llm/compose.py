"""Klien LLM pluggable untuk menyusun gloss isyarat menjadi kalimat natural.

Provider:
- "stub" (default): heuristik lokal tanpa API — merapikan urutan gloss menjadi
  kalimat sederhana. Membuat fitur kalimat bisa dipakai tanpa kunci API.
- "openai-compatible": memanggil endpoint chat completions yang kompatibel OpenAI
  (mis. OpenAI, vLLM, Ollama, LM Studio) lewat AMERTASIGN_LLM_* env.

Perbedaan tata bahasa:
- SIBI mengikuti struktur Bahasa Indonesia baku (berimbuhan) → minim perubahan.
- BISINDO cenderung memakai gloss tanpa imbuhan & urutan berbeda → LLM membantu
  menstrukturkan ulang menjadi kalimat baku.
"""
from __future__ import annotations

import json
import urllib.request

from app.config import settings


def compose_sentence(gloss: list[str], mode: str) -> dict:
    """Ubah urutan gloss menjadi kalimat. Mengembalikan dict {sentence, provider, gloss}."""
    cleaned = [g.strip() for g in gloss if g and g.strip()]
    if not cleaned:
        return {"sentence": "", "provider": settings.llm_provider, "gloss": []}

    provider = settings.llm_provider
    if provider == "openai-compatible" and settings.llm_base_url and settings.llm_api_key:
        try:
            sentence = _compose_openai(cleaned, mode)
            return {"sentence": sentence, "provider": provider, "gloss": cleaned}
        except Exception as exc:  # noqa: BLE001 - fallback ke stub bila gagal
            return {
                "sentence": _compose_stub(cleaned),
                "provider": "stub",
                "gloss": cleaned,
                "note": f"LLM gagal ({exc}); memakai stub.",
            }

    return {"sentence": _compose_stub(cleaned), "provider": "stub", "gloss": cleaned}


def _compose_stub(gloss: list[str]) -> str:
    """Heuristik sederhana: gabung gloss, kapitalisasi, beri tanda titik.

    Bukan parser tata bahasa — hanya placeholder yang berguna saat tanpa LLM.
    """
    words = [g.lower() for g in gloss]
    sentence = " ".join(words).strip()
    if not sentence:
        return ""
    return sentence[0].upper() + sentence[1:] + "."


def _build_prompt(gloss: list[str], mode: str) -> str:
    sys_hint = (
        "BISINDO biasanya memakai gloss tanpa imbuhan dan urutan kata yang ringkas."
        if mode == "BISINDO"
        else "SIBI mengikuti struktur Bahasa Indonesia baku."
    )
    return (
        "Anda menyusun kalimat Bahasa Indonesia yang natural dan baku dari urutan "
        "gloss bahasa isyarat. " + sys_hint + " Jangan menambah informasi yang tidak "
        "ada pada gloss. Balas hanya dengan satu kalimat.\n\n"
        f"Gloss: {' '.join(gloss)}\nKalimat:"
    )


def _compose_openai(gloss: list[str], mode: str) -> str:
    """Panggil endpoint chat completions kompatibel OpenAI."""
    url = settings.llm_base_url.rstrip("/") + "/chat/completions"
    payload = {
        "model": settings.llm_model or "gpt-3.5-turbo",
        "messages": [
            {
                "role": "system",
                "content": "Anda asisten yang menyusun kalimat Bahasa Indonesia baku dari gloss isyarat.",
            },
            {"role": "user", "content": _build_prompt(gloss, mode)},
        ],
        "temperature": 0.3,
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {settings.llm_api_key}",
        },
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        data = json.loads(resp.read())
    return data["choices"][0]["message"]["content"].strip()
