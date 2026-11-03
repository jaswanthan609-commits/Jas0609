"""Channel configuration: loads config/channel.yaml plus environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent

# Free Microsoft neural voices served by edge-tts. Run `edge-tts --list-voices` for more.
DEFAULT_VOICES = {
    "en": "en-IN-PrabhatNeural",
    "ta": "ta-IN-ValluvarNeural",
    "hi": "hi-IN-MadhurNeural",
}

LANGUAGE_NAMES = {"en": "English", "ta": "Tamil", "hi": "Hindi"}

# Fonts libass needs to shape each script. Install the matching Noto font (see README).
DEFAULT_FONTS = {"en": "Noto Sans", "ta": "Noto Sans Tamil", "hi": "Noto Sans Devanagari"}

FORMATS = {
    # name: (width, height, target seconds)
    "short": (1080, 1920, 50),
    "long": (1920, 1080, 480),
}


@dataclass
class ChannelConfig:
    name: str = "My Faceless Channel"
    niche: str = "personal finance tips for young Indians"
    language: str = "hi"
    audience: str = "18-35 year olds in India"
    tone: str = "energetic, simple, trustworthy"
    voice: str | None = None
    voice_rate: str = "+5%"
    font: str | None = None
    caption_color: str = "&H0000FFFF"  # ASS BGR hex: yellow
    music_volume: float = 0.12
    default_tags: list[str] = field(default_factory=list)
    category_id: str = "27"  # YouTube "Education"
    made_for_kids: bool = False
    claude_model: str = "claude-opus-5-5"
    claude_effort: str = "medium"
    output_dir: str = "output"
    music_dir: str = "assets/music"
    publish_times: list[str] = field(default_factory=lambda: ["18:30"])  # local times, daily slots
    timezone: str = "Asia/Kolkata"

    @property
    def voice_name(self) -> str:
        return self.voice or DEFAULT_VOICES[self.language]

    @property
    def font_name(self) -> str:
        return self.font or DEFAULT_FONTS[self.language]

    @property
    def language_name(self) -> str:
        return LANGUAGE_NAMES[self.language]

    @property
    def output_path(self) -> Path:
        return ROOT / self.output_dir

    @property
    def music_path(self) -> Path:
        return ROOT / self.music_dir


def load_config(path: str | os.PathLike | None = None, **overrides) -> ChannelConfig:
    path = Path(path) if path else ROOT / "config" / "channel.yaml"
    data = {}
    if path.exists():
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    data.update({k: v for k, v in overrides.items() if v is not None})
    known = ChannelConfig.__dataclass_fields__
    unknown = set(data) - set(known)
    if unknown:
        raise ValueError(f"Unknown keys in {path}: {sorted(unknown)}")
    cfg = ChannelConfig(**data)
    if cfg.language not in LANGUAGE_NAMES:
        raise ValueError(f"language must be one of {list(LANGUAGE_NAMES)}, got {cfg.language!r}")
    return cfg


def env(name: str, required: bool = True) -> str | None:
    value = os.environ.get(name)
    if required and not value:
        raise RuntimeError(f"Set the {name} environment variable (see .env.example).")
    return value
