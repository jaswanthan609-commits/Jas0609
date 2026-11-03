"""Text-to-speech voiceover with free Microsoft neural voices (edge-tts).

English, Tamil and Hindi each have male and female voices, for example:
  en-IN-PrabhatNeural / en-IN-NeerjaNeural
  ta-IN-ValluvarNeural / ta-IN-PallaviNeural
  hi-IN-MadhurNeural / hi-IN-SwaraNeural
"""

from __future__ import annotations

import asyncio
from pathlib import Path

from .config import ChannelConfig
from .media import duration, run


async def _speak(text: str, voice: str, rate: str, out: Path) -> None:
    import edge_tts

    await edge_tts.Communicate(text, voice, rate=rate).save(str(out))


def synthesize(cfg: ChannelConfig, text: str, out: Path) -> float:
    """Write an mp3 voiceover for `text` and return its length in seconds."""
    asyncio.run(_speak(text, cfg.voice_name, cfg.voice_rate, out))
    return duration(out)


def synthesize_placeholder(text: str, out: Path, words_per_second: float = 2.5) -> float:
    """Offline stand-in for dry runs: silence as long as the narration would take."""
    seconds = max(1.5, len(text.split()) / words_per_second)
    run([
        "ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
        "-t", f"{seconds:.2f}", "-c:a", "libmp3lame", "-q:a", "4", str(out),
    ])
    return duration(out)
