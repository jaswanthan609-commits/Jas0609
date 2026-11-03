"""Visuals for each scene: Pexels stock video, Pexels photos, or an offline placeholder.

Pexels is free for commercial use without attribution (https://www.pexels.com/license/).
Get a key at https://www.pexels.com/api/ and set PEXELS_API_KEY.
"""

from __future__ import annotations

import random
from pathlib import Path

import requests

from .config import env
from .media import run

PEXELS = "https://api.pexels.com"


def _get(url: str, params: dict) -> dict:
    r = requests.get(url, params=params, headers={"Authorization": env("PEXELS_API_KEY")}, timeout=30)
    r.raise_for_status()
    return r.json()


def _download(url: str, out: Path) -> Path:
    with requests.get(url, stream=True, timeout=120) as r:
        r.raise_for_status()
        with open(out, "wb") as f:
            for chunk in r.iter_content(1 << 16):
                f.write(chunk)
    return out


def _best_video_file(video: dict, width: int, height: int) -> str | None:
    files = [f for f in video.get("video_files", []) if f.get("file_type") == "video/mp4" and f.get("width")]
    if not files:
        return None
    # Smallest file that still covers the target resolution, else the largest available.
    big_enough = [f for f in files if min(f["width"], f["height"]) >= min(width, height) * 0.7]
    pick = min(big_enough, key=lambda f: f["width"]) if big_enough else max(files, key=lambda f: f["width"])
    return pick["link"]


def fetch_stock(query: str, width: int, height: int, out_stem: Path, used: set[int]) -> Path | None:
    """Download a stock clip (or photo as fallback) for `query`. Returns None if nothing found."""
    orientation = "portrait" if height > width else "landscape"
    data = _get(f"{PEXELS}/videos/search", {"query": query, "orientation": orientation, "per_page": 15})
    videos = [v for v in data.get("videos", []) if v["id"] not in used]
    random.shuffle(videos)
    for video in videos[:5]:
        link = _best_video_file(video, width, height)
        if link:
            used.add(video["id"])
            return _download(link, out_stem.with_suffix(".mp4"))

    data = _get(f"{PEXELS}/v1/search", {"query": query, "orientation": orientation, "per_page": 15})
    photos = [p for p in data.get("photos", []) if p["id"] not in used]
    if photos:
        photo = random.choice(photos)
        used.add(photo["id"])
        return _download(photo["src"]["large2x"], out_stem.with_suffix(".jpg"))
    return None


PLACEHOLDER_COLORS = ["0x1f3b73", "0x5b2a86", "0x0f6e5a", "0x8a3b12", "0x2d2d2d", "0x6b1b3a"]


def placeholder(index: int, width: int, height: int, out_stem: Path) -> Path:
    """Offline stand-in: a solid colour frame, so dry runs work without any API key."""
    out = out_stem.with_suffix(".png")
    color = PLACEHOLDER_COLORS[index % len(PLACEHOLDER_COLORS)]
    run(["ffmpeg", "-y", "-f", "lavfi", "-i", f"color=c={color}:s={width}x{height}", "-frames:v", "1", str(out)])
    return out
