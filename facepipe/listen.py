"""Ears for the pipeline: earshot (github.com/Leonxlnx/earshot, MIT) listens to what we render.

We synthesise music and mix voices we cannot hear, so every rendered video's audio gets measured
(loudness, true peak, clipping, brightness) and described in words (what it sounds like, whether it
reads as a real recording or code-synthesised). The report lands next to the video as
audio_report.json and in metadata.json, where the drafts and publish logs show it.

earshot needs torch on CPU and two open models (~1.1 GB, cached between runs). When it is not
installed, listening is skipped and nothing else changes.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path


def available() -> bool:
    return shutil.which("earshot") is not None


def _run(*args: str, timeout: int = 900) -> dict | None:
    try:
        out = subprocess.run(["earshot", *args, "--json"], capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired) as exc:
        print(f"  listen: earshot {args[0]} failed: {exc}")
        return None
    if out.returncode != 0:
        print(f"  listen: earshot {args[0]}: {out.stderr.strip()[:300]}")
        return None
    try:
        return json.loads(out.stdout)
    except json.JSONDecodeError:
        return {"text": out.stdout.strip()[:4000]}


def excerpt(media: Path, out: Path, seconds: float = 45.0) -> Path:
    """A mono 48 kHz WAV excerpt, so the models hear the body of a long video, not its fade-in."""
    from .media import duration

    start = min(60.0, max(0.0, duration(media) / 3))
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", str(start), "-t", str(seconds), "-i", str(media),
                    "-vn", "-ac", "1", "-ar", "48000", str(out)], check=True)
    return out


def listen(media: Path, report: Path | None = None) -> dict | None:
    """Measure and describe the audio of `media`; write audio_report.json beside it. None if no earshot."""
    if not available():
        return None
    clip = excerpt(media, media.with_name("listen_excerpt.wav"))
    result = {
        "measure": _run("measure", str(clip)),
        "describe": _run("describe", str(clip)),
        "realness": _run("realness", str(clip)),
    }
    report = report or media.with_name("audio_report.json")
    report.write_text(json.dumps(result, indent=1, ensure_ascii=False), encoding="utf-8")
    clip.unlink(missing_ok=True)
    return result
