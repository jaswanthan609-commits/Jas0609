"""Text-to-speech voiceover. Three providers, chosen per channel with `voice_provider`:

- edge:       free Microsoft neural voices via edge-tts. Good for testing and Shorts.
- sarvam:     Sarvam Bulbul v3, best-rated for Hindi and Tamil (about Rs 30 per 10,000 characters).
              Needs SARVAM_API_KEY.
- elevenlabs: most natural English voices. Needs ELEVENLABS_API_KEY.
"""

from __future__ import annotations

import asyncio
import base64
import re
from pathlib import Path

import requests

from .config import ChannelConfig, env
from .media import duration, run

SARVAM_URL = "https://api.sarvam.ai/text-to-speech"
SARVAM_MAX_CHARS = 2000  # API limit is 2500 for bulbul:v3; stay under it
ELEVENLABS_URL = "https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"


def _split(text: str, limit: int) -> list[str]:
    """Split on sentence ends so each piece stays under `limit` characters."""
    sentences = re.split(r"(?<=[.!?।])\s+", text.strip())  # । = Devanagari danda
    pieces, current = [], ""
    for s in sentences:
        if len(current) + len(s) + 1 > limit and current:
            pieces.append(current)
            current = s
        else:
            current = f"{current} {s}".strip()
    if current:
        pieces.append(current)
    return pieces


def _to_mp3(parts: list[Path], out: Path) -> None:
    if len(parts) == 1:
        run(["ffmpeg", "-y", "-i", str(parts[0]), "-c:a", "libmp3lame", "-q:a", "2", str(out)])
        return
    listing = out.with_suffix(".parts.txt")
    listing.write_text("".join(f"file '{p.resolve()}'\n" for p in parts), encoding="utf-8")
    run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(listing),
         "-c:a", "libmp3lame", "-q:a", "2", str(out)])


def _edge(cfg: ChannelConfig, text: str, out: Path) -> None:
    import edge_tts

    rate = f"{round((cfg.voice_rate - 1) * 100):+d}%"
    asyncio.run(edge_tts.Communicate(text, cfg.voice_name, rate=rate).save(str(out)))


def _sarvam(cfg: ChannelConfig, text: str, out: Path) -> None:
    key = env("SARVAM_API_KEY")
    parts = []
    for i, piece in enumerate(_split(text, SARVAM_MAX_CHARS)):
        r = requests.post(
            SARVAM_URL,
            headers={"api-subscription-key": key},
            json={
                "text": piece,
                "language_code": cfg.locale,
                "model": "bulbul:v3",
                "speaker": cfg.voice_name,
                "pace": cfg.voice_rate,
                "speech_sample_rate": 44100,
            },
            timeout=120,
        )
        r.raise_for_status()
        part = out.with_name(f"{out.stem}.part{i}.wav")
        part.write_bytes(base64.b64decode("".join(r.json()["audios"])))
        parts.append(part)
    _to_mp3(parts, out)


def _elevenlabs(cfg: ChannelConfig, text: str, out: Path) -> None:
    r = requests.post(
        ELEVENLABS_URL.format(voice_id=cfg.voice_name),
        params={"output_format": "mp3_44100_128"},
        headers={"xi-api-key": env("ELEVENLABS_API_KEY")},
        json={
            "text": text,
            "model_id": "eleven_multilingual_v2",
            "voice_settings": {"stability": 0.5, "similarity_boost": 0.75, "speed": cfg.voice_rate},
        },
        timeout=300,
    )
    r.raise_for_status()
    out.write_bytes(r.content)


PROVIDERS = {"edge": _edge, "sarvam": _sarvam, "elevenlabs": _elevenlabs}


def synthesize(cfg: ChannelConfig, text: str, out: Path) -> float:
    """Write an mp3 voiceover for `text` and return its length in seconds."""
    PROVIDERS[cfg.voice_provider](cfg, text, out)
    return duration(out)


def synthesize_placeholder(text: str, out: Path, words_per_second: float = 2.5) -> float:
    """Offline stand-in for dry runs: silence as long as the narration would take."""
    seconds = max(1.5, len(text.split()) / words_per_second)
    run([
        "ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
        "-t", f"{seconds:.2f}", "-c:a", "libmp3lame", "-q:a", "4", str(out),
    ])
    return duration(out)
