"""Visuals for each scene, tried in order:

1. Your own footage (footage_dir in the channel config), e.g. OBS screen recordings. Name files
   with the words a scene's visual_query will use ("chatgpt-custom-gpt-settings.mp4"), or put
   `footage:<file name>` as the scene's visual_query in script.json to pick a file exactly.
2. Pexels stock video, then photos (PEXELS_API_KEY). Free for commercial use.
3. Pixabay stock video (PIXABAY_API_KEY). Free for commercial use.
4. An offline colour placeholder, so dry runs work with no keys.

Illustrated channels (visual_mode: ai_images, e.g. kids stories) instead generate one picture per
scene with Google's Nano Banana image model (GEMINI_API_KEY), passing the character reference
images each time so characters stay consistent.
"""

from __future__ import annotations

import base64
import mimetypes
import os
import random
import re
from pathlib import Path

import requests

from .config import ROOT, ChannelConfig, env
from .media import run

PEXELS = "https://api.pexels.com"
PIXABAY = "https://pixabay.com/api/videos/"
MEDIA_EXT = {".mp4", ".mov", ".mkv", ".webm", ".jpg", ".jpeg", ".png", ".webp"}


def _download(url: str, out: Path) -> Path:
    with requests.get(url, stream=True, timeout=120) as r:
        r.raise_for_status()
        with open(out, "wb") as f:
            for chunk in r.iter_content(1 << 16):
                f.write(chunk)
    return out


def _words(text: str) -> set[str]:
    return {w for w in re.split(r"[^a-z0-9]+", text.lower()) if len(w) > 2}


def own_footage(cfg: ChannelConfig, query: str, used: set) -> Path | None:
    folder = cfg.footage_path
    if not folder or not folder.is_dir():
        return None
    files = [p for p in sorted(folder.iterdir()) if p.suffix.lower() in MEDIA_EXT]
    if query.startswith("footage:"):
        name = query.split(":", 1)[1].strip()
        exact = [p for p in files if p.name == name or p.stem == name]
        if not exact:
            raise FileNotFoundError(f"Scene asks for footage '{name}', not found in {folder}")
        return exact[0]
    wanted = _words(query)
    scored = [(len(wanted & _words(p.stem)), p) for p in files if p not in used]
    scored = [(score, p) for score, p in scored if score > 0]
    if not scored:
        return None
    best = max(scored, key=lambda sp: sp[0])[1]
    used.add(best)
    return best


def _pexels(query: str, width: int, height: int, out_stem: Path, used: set) -> Path | None:
    headers = {"Authorization": env("PEXELS_API_KEY")}
    orientation = "portrait" if height > width else "landscape"
    params = {"query": query, "orientation": orientation, "per_page": 15}
    data = requests.get(f"{PEXELS}/videos/search", params=params, headers=headers, timeout=30).json()
    videos = [v for v in data.get("videos", []) if ("pexels", v["id"]) not in used]
    random.shuffle(videos)
    for video in videos[:5]:
        files = [f for f in video.get("video_files", []) if f.get("file_type") == "video/mp4" and f.get("width")]
        big = [f for f in files if min(f["width"], f["height"]) >= min(width, height) * 0.7]
        pick = min(big, key=lambda f: f["width"]) if big else (max(files, key=lambda f: f["width"]) if files else None)
        if pick:
            used.add(("pexels", video["id"]))
            return _download(pick["link"], out_stem.with_suffix(".mp4"))
    data = requests.get(f"{PEXELS}/v1/search", params=params, headers=headers, timeout=30).json()
    photos = [p for p in data.get("photos", []) if ("pexels-photo", p["id"]) not in used]
    if photos:
        photo = random.choice(photos)
        used.add(("pexels-photo", photo["id"]))
        return _download(photo["src"]["large2x"], out_stem.with_suffix(".jpg"))
    return None


def _pixabay(query: str, width: int, height: int, out_stem: Path, used: set) -> Path | None:
    params = {"key": env("PIXABAY_API_KEY"), "q": query[:100], "per_page": 20, "safesearch": "true"}
    data = requests.get(PIXABAY, params=params, timeout=30).json()
    vertical = height > width
    hits = [h for h in data.get("hits", []) if ("pixabay", h["id"]) not in used]
    # Prefer clips whose orientation matches the frame.
    hits.sort(key=lambda h: (h["videos"]["large"]["height"] > h["videos"]["large"]["width"]) != vertical)
    for hit in hits[:5]:
        for size in ("large", "medium", "small"):
            v = hit["videos"].get(size) or {}
            if v.get("url"):
                used.add(("pixabay", hit["id"]))
                return _download(v["url"], out_stem.with_suffix(".mp4"))
    return None


STOCK = {"pexels": (_pexels, "PEXELS_API_KEY"), "pixabay": (_pixabay, "PIXABAY_API_KEY")}


def fetch(cfg: ChannelConfig, query: str, width: int, height: int, out_stem: Path, used: set) -> Path | None:
    """Best visual for a scene, or None if every source came back empty."""
    found = own_footage(cfg, query, used)
    if found:
        return found
    for source in cfg.stock_sources:
        fn, key = STOCK[source]
        if not os.environ.get(key):
            continue
        try:
            found = fn(query, width, height, out_stem, used)
        except requests.RequestException as exc:
            print(f"  {source} failed for '{query}': {exc}")
            continue
        if found:
            return found
    return None


GEMINI_INTERACTIONS = "https://generativelanguage.googleapis.com/v1beta/interactions"


def _image_blocks(node) -> list[dict]:
    """Every {"type": "image", "data": ...} block anywhere in the API response, in order."""
    found = []
    if isinstance(node, dict):
        if node.get("type") == "image" and isinstance(node.get("data"), str):
            found.append(node)
        for value in node.values():
            found += _image_blocks(value)
    elif isinstance(node, list):
        for value in node:
            found += _image_blocks(value)
    return found


def ai_image(cfg: ChannelConfig, prompt: str, width: int, height: int, out_stem: Path) -> Path:
    """Generate one illustration for a scene. Character reference images keep characters consistent."""
    inputs = []
    for ref in cfg.character_refs[:4]:
        path = Path(ref) if Path(ref).is_absolute() else ROOT / ref
        mime = mimetypes.guess_type(path.name)[0] or "image/png"
        inputs.append({"type": "image", "mime_type": mime, "data": base64.b64encode(path.read_bytes()).decode()})
    style = f" Art style: {cfg.image_style}." if cfg.image_style else ""
    inputs.append({"type": "text", "text": f"{prompt}{style} No text, letters or watermarks in the image."})
    body = {
        "model": cfg.image_model,
        "input": inputs,
        "response_format": {
            "type": "image",
            "mime_type": "image/png",
            "aspect_ratio": "9:16" if height > width else "16:9",
            "image_size": "2K",
        },
    }
    r = requests.post(
        GEMINI_INTERACTIONS, json=body, headers={"x-goog-api-key": env("GEMINI_API_KEY")}, timeout=300
    )
    r.raise_for_status()
    from . import budget

    budget.record("image", cfg.slug, budget.image_cost(), model=cfg.image_model)
    images = _image_blocks(r.json())
    if not images:
        raise RuntimeError(f"Image model returned no image for: {prompt[:80]}")
    out = out_stem.with_suffix(".png")
    out.write_bytes(base64.b64decode(images[-1]["data"]))
    return out


PLACEHOLDER_COLORS = ["0x1f3b73", "0x5b2a86", "0x0f6e5a", "0x8a3b12", "0x2d2d2d", "0x6b1b3a"]


def placeholder(index: int, width: int, height: int, out_stem: Path) -> Path:
    """Offline stand-in: a solid colour frame, so dry runs work without any API key."""
    out = out_stem.with_suffix(".png")
    color = PLACEHOLDER_COLORS[index % len(PLACEHOLDER_COLORS)]
    run(["ffmpeg", "-y", "-f", "lavfi", "-i", f"color=c={color}:s={width}x{height}", "-frames:v", "1", str(out)])
    return out
