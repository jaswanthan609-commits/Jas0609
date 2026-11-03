"""Burned-in captions as an ASS subtitle file.

Each scene's narration is split into short chunks (3-5 words for Shorts) and timed in
proportion to character count across that scene's audio. That works for any language,
including Tamil and Hindi, without needing word-level timestamps from the TTS engine.
"""

from __future__ import annotations

from pathlib import Path

from .config import ChannelConfig


def _chunks(text: str, max_words: int) -> list[str]:
    words = text.split()
    return [" ".join(words[i : i + max_words]) for i in range(0, len(words), max_words)] or [""]


def _ts(seconds: float) -> str:
    cs = int(round(seconds * 100))
    h, cs = divmod(cs, 360000)
    m, cs = divmod(cs, 6000)
    s, cs = divmod(cs, 100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def _escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace("{", "(").replace("}", ")").replace("\n", " ")


def build_ass(
    cfg: ChannelConfig,
    scenes: list[tuple[str, float, str]],
    width: int,
    height: int,
    out: Path,
) -> Path:
    """scenes: list of (narration, duration_seconds, on_screen_text)."""
    vertical = height > width
    font_size = int(height * (0.045 if vertical else 0.055))
    max_words = 4 if vertical else 7
    margin_v = int(height * (0.28 if vertical else 0.08))
    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {width}
PlayResY: {height}
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Caption,{cfg.font_name},{font_size},{cfg.caption_color},&H000000FF,&H00000000,&H80000000,1,0,0,0,100,100,0,0,1,{max(3, font_size // 12)},2,2,60,60,{margin_v},1
Style: Headline,{cfg.font_name},{int(font_size * 1.2)},&H00FFFFFF,&H000000FF,&H00000000,&HA0000000,1,0,0,0,100,100,0,0,3,8,0,8,60,60,{int(height * 0.12)},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    lines = []
    t = 0.0
    for narration, dur, headline in scenes:
        if headline:
            lines.append(f"Dialogue: 1,{_ts(t)},{_ts(t + dur)},Headline,,0,0,0,,{_escape(headline)}")
        chunks = _chunks(narration, max_words)
        total_chars = sum(len(c) for c in chunks) or 1
        ct = t
        for chunk in chunks:
            cd = dur * len(chunk) / total_chars
            # Small pop-in animation on each chunk.
            text = "{\\fscx90\\fscy90\\t(0,80,\\fscx100\\fscy100)}" + _escape(chunk)
            lines.append(f"Dialogue: 0,{_ts(ct)},{_ts(ct + cd)},Caption,,0,0,0,,{text}")
            ct += cd
        t += dur
    out.write_text(header + "\n".join(lines) + "\n", encoding="utf-8")
    return out
