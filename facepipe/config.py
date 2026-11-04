"""Channel configuration: one YAML file per channel in config/channels/, plus environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
CHANNELS_DIR = ROOT / "config" / "channels"

# Default voices per provider and language.
DEFAULT_VOICES = {
    # Free Microsoft neural voices (edge-tts). `edge-tts --list-voices` lists them all.
    "edge": {"en": "en-IN-PrabhatNeural", "ta": "ta-IN-ValluvarNeural", "hi": "hi-IN-MadhurNeural"},
    # Sarvam Bulbul v3 speakers (lowercase). Best-rated for Hindi and Tamil.
    "sarvam": {"en": "shubh", "ta": "shubh", "hi": "shubh"},
    # ElevenLabs voice id. Replace with the voice you choose in the ElevenLabs voice library.
    # Kokoro: free open-source voice model run on the GitHub server (English only here).
    # American voices start "a" (af_heart, am_michael), British "b" (bf_emma, bm_george).
    "kokoro": {"en": "am_michael", "ta": "", "hi": ""},
    "elevenlabs": {"en": "JBFqnCBsd6RMkjVDRZzb", "ta": "JBFqnCBsd6RMkjVDRZzb", "hi": "JBFqnCBsd6RMkjVDRZzb"},
}

LANGUAGE_NAMES = {"en": "English", "ta": "Tamil", "hi": "Hindi"}
LOCALES = {"en": "en-IN", "ta": "ta-IN", "hi": "hi-IN"}

# Fonts libass needs to shape each script. Install the matching Noto font (see assets/fonts).
DEFAULT_FONTS = {"en": "Noto Sans", "ta": "Noto Sans Tamil", "hi": "Noto Sans Devanagari"}

FORMATS = {
    # name: (width, height, target seconds)
    "short": (1080, 1920, 50),
    "long": (1920, 1080, 540),
    "deep": (1920, 1080, 1800),  # 30-minute calm videos (sleep / background listening)
    "story": (1920, 1080, 900),  # 15-minute "what really happened" stories (cold open, open loops)
    "sleep": (1920, 1080, 7200),  # 2-hour sleep videos, written chapter by chapter
    "ambience": (1920, 1080, 7800),  # 130-minute cozy scene + original music (breakout median: 129 min)
}
VISUAL_MODES = {"stock", "ai_images", "public_art", "ambience"}
LONG_FORMATS = [f for f in FORMATS if f != "short"]


@dataclass
class ChannelConfig:
    slug: str = "default"
    name: str = "My Faceless Channel"
    niche: str = "personal finance tips for young Indians"
    language: str = "hi"
    audience: str = "18-35 year olds in India"
    tone: str = "energetic, simple, trustworthy"
    voice_provider: str = "edge"
    fallback_voice: str = ""  # edge-tts voice used if the main provider fails (e.g. Kokoro not installed)
    voice: str | None = None
    voice_rate: float = 1.05  # 1.0 = normal speed
    font: str | None = None
    caption_color: str = "&H0000FFFF"  # ASS BGR hex: yellow
    music_volume: float = 0.12
    footage_dir: str | None = None  # your own clips (screen recordings), used before stock
    stock_sources: list[str] = field(default_factory=lambda: ["pexels", "pixabay"])
    visual_mode: str = "stock"  # stock | ai_images (illustration per scene) | public_art (museum paintings) | ambience
    image_model: str = "gemini-nano-banana-2.1"
    image_style: str = ""  # art direction added to every image prompt
    characters: str = ""  # recurring characters, described the same way every time
    character_refs: list[str] = field(default_factory=list)  # reference images of the characters
    extra_guidelines: str = ""  # channel-specific rules added to Claude's instructions
    default_tags: list[str] = field(default_factory=list)
    category_id: str = "27"  # YouTube "Education"
    made_for_kids: bool = False
    claude_model: str = "claude-opus-5-5"
    claude_model_short: str | None = None  # cheaper model for Shorts scripts; defaults to claude_model
    claude_effort: str = "medium"
    output_dir: str | None = None
    music_dir: str = "assets/music"
    publish_times: list[str] = field(default_factory=lambda: ["18:30"])  # local times, daily slots
    timezone: str = "Asia/Kolkata"
    monthly_target_inr: int = 0
    research_queries: list[str] = field(default_factory=list)  # YouTube searches for breakout research
    long_format: str = "long"  # this channel's long videos: long (9 min), deep (30), story (15), sleep (120)
    scan_topics: list[str] = field(default_factory=list)  # seeds from config/scan.yaml that feed this channel
    burn_captions: bool = True  # False: no subtitles on the picture; a captions.srt is uploaded instead
    dissolve: float = 0.0  # seconds each scene fades in and out (sleep videos: slow, no hard cuts)
    art_sources: list[str] = field(default_factory=lambda: ["met", "artic"])  # visual_mode public_art
    # Affiliate or referral links added to matching video descriptions (see facepipe/affiliate.py).
    # Each item: {label, url, keywords: [...], always: false}. Empty urls are skipped.
    affiliate_links: list[dict] = field(default_factory=list)

    @property
    def voice_name(self) -> str:
        return self.voice or DEFAULT_VOICES[self.voice_provider][self.language]

    @property
    def font_name(self) -> str:
        return self.font or DEFAULT_FONTS[self.language]

    @property
    def language_name(self) -> str:
        return LANGUAGE_NAMES[self.language]

    @property
    def locale(self) -> str:
        return LOCALES[self.language]

    @property
    def output_path(self) -> Path:
        return ROOT / (self.output_dir or f"output/{self.slug}")

    @property
    def music_path(self) -> Path:
        return ROOT / self.music_dir

    @property
    def footage_path(self) -> Path | None:
        return ROOT / self.footage_dir if self.footage_dir else None


def list_channels() -> list[str]:
    return sorted(p.stem for p in CHANNELS_DIR.glob("*.yaml"))


def channel_file(channel: str | None) -> Path:
    channels = list_channels()
    if channel is None:
        channel = os.environ.get("FACEPIPE_CHANNEL")
    if channel is None:
        if len(channels) == 1:
            channel = channels[0]
        else:
            raise ValueError(f"Choose a channel with --channel: {', '.join(channels)}")
    path = Path(channel)
    if path.suffix in {".yaml", ".yml"} and path.exists():
        return path
    path = CHANNELS_DIR / f"{channel}.yaml"
    if not path.exists():
        raise ValueError(f"No channel '{channel}'. Available: {', '.join(channels)}")
    return path


def load_config(channel: str | None = None, **overrides) -> ChannelConfig:
    data: dict = {}
    if channel is not None or list_channels():
        path = channel_file(channel)
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        data.setdefault("slug", path.stem)
    data.update({k: v for k, v in overrides.items() if v is not None})
    unknown = set(data) - set(ChannelConfig.__dataclass_fields__)
    if unknown:
        raise ValueError(f"Unknown config keys: {sorted(unknown)}")
    cfg = ChannelConfig(**data)
    if cfg.language not in LANGUAGE_NAMES:
        raise ValueError(f"language must be one of {list(LANGUAGE_NAMES)}, got {cfg.language!r}")
    if cfg.visual_mode not in VISUAL_MODES:
        raise ValueError(f"visual_mode must be one of {sorted(VISUAL_MODES)}, got {cfg.visual_mode!r}")
    if cfg.long_format not in LONG_FORMATS:
        raise ValueError(f"long_format must be one of {LONG_FORMATS}, got {cfg.long_format!r}")
    if cfg.voice_provider not in DEFAULT_VOICES:
        raise ValueError(f"voice_provider must be one of {list(DEFAULT_VOICES)}, got {cfg.voice_provider!r}")
    return cfg


def env(name: str, required: bool = True) -> str | None:
    value = os.environ.get(name)
    if required and not value:
        raise RuntimeError(f"Set the {name} environment variable (see .env.example).")
    return value
