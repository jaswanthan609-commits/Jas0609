"""Real rain and fire recordings under the Cozy Hours music.

earshot heard our code-made rain as "a waterfall". These are field recordings picked by the Beds probe
(scripts/beds_probe.py, run 41925792081 on 2026-11-04): each licence was read on the item's own Freesound page
and each one was judged on a 40 s excerpt (all "real or pro-produced", every window heard as rain or a crackling
fire). Only CC0 items are used, so no credit is required; we credit the recordists anyway.

The HQ previews are downloaded at render time into a cache (never committed) and looped circularly with a long
crossfade, so a 2-hour bed has no seam.
"""

from __future__ import annotations

import os
import subprocess
import urllib.request
from pathlib import Path

import numpy as np

from .config import ROOT

SR = 44100
BEDS = {
    "rain": [
        dict(id=648529, title="RAIN on glass window", author="nicoproson", licence="CC0 1.0",
             page="https://freesound.org/s/648529/",
             audio="https://cdn.freesound.org/previews/648/648529_457982-hq.mp3", p_real=0.91),
        dict(id=752099, title="raindrops tapping against window interior 01", author="fluctuating_frequency",
             licence="CC0 1.0", page="https://freesound.org/s/752099/",
             audio="https://cdn.freesound.org/previews/752/752099_2911101-hq.mp3", p_real=0.81),
    ],
    "fire": [
        dict(id=545637, title="Fire crackles in the fireplace", author="pater.marek.op", licence="CC0 1.0",
             page="https://freesound.org/s/545637/",
             audio="https://cdn.freesound.org/previews/545/545637_7572114-hq.mp3", p_real=1.00),
        dict(id=800660, title="Inside fireplace (Crackling)", author="Sadiquecat", licence="CC0 1.0",
             page="https://freesound.org/s/800660/",
             audio="https://cdn.freesound.org/previews/800/800660_5287430-hq.mp3", p_real=0.97),
    ],
}
LEVEL = {"rain": 0.05, "fire": 0.045}  # RMS before the mix's bed gain


def home() -> Path:
    return Path(os.environ.get("FACEPIPE_BEDS", ROOT / ".cache" / "beds"))


def _path(item: dict) -> Path:
    return home() / f"freesound-{item['id']}.mp3"


def fetch(kinds: list[str], log=print) -> None:
    home().mkdir(parents=True, exist_ok=True)
    for kind in kinds:
        for item in BEDS.get(kind, []):
            p = _path(item)
            if p.exists() and p.stat().st_size > 10_000:
                continue
            try:
                req = urllib.request.Request(item["audio"], headers={"User-Agent": "facepipe/1.0"})
                p.write_bytes(urllib.request.urlopen(req, timeout=120).read())
                log(f"  beds: {kind} {item['id']} by {item['author']} ({item['licence']})")
            except Exception as e:  # noqa: BLE001 - a missing bed falls back to synthesis
                log(f"  beds: {item['id']} unavailable ({e})")


def kinds_for(texture: str) -> list[str]:
    return {"rain": ["rain"], "fire": ["fire"], "rain_fire": ["rain", "fire"]}.get(texture, [])


def available(kind: str) -> list[dict]:
    return [i for i in BEDS.get(kind, []) if _path(i).exists() and _path(i).stat().st_size > 10_000]


def credits(texture: str) -> list[str]:
    return [f"{k.capitalize()}: \"{i['title']}\" by {i['author']} on Freesound ({i['licence']})"
            for k in kinds_for(texture) for i in BEDS[k][:1]]


def _decode(path: Path) -> np.ndarray:
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-f", "f32le", "-ac", "2", "-ar", str(SR), "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype="<f4").reshape(-1, 2).astype(np.float64)


def loop(x: np.ndarray, n: int, rng: np.random.Generator, fade: float = 3.0) -> np.ndarray:
    """Fill n samples from recording x so that the result loops seamlessly (circular crossfades)."""
    xf = min(int(fade * SR), len(x) // 3)
    x = np.roll(x, -int(rng.integers(len(x))), axis=0)
    hop = len(x) - xf
    out = np.zeros((n + xf, 2))
    ramp = np.sin(np.linspace(0, np.pi / 2, xf)) ** 2
    i = 0
    while i < n + xf:
        seg = x[: min(len(x), n + xf - i)].copy()
        if i > 0:
            k = min(xf, len(seg))
            seg[:k] *= ramp[:k, None]
            out[i: i + k] *= (1 - ramp[:k, None])
        out[i: i + len(seg)] += seg
        i += hop
    head = out[:xf].copy()
    out[:xf] = head * ramp[:, None] + out[n: n + xf] * (1 - ramp[:, None])  # wrap the tail onto the start
    return out[:n]


def bed(kind: str, n: int, rng: np.random.Generator) -> np.ndarray | None:
    items = available(kind)
    if not items:
        return None
    x = _decode(_path(items[int(rng.integers(len(items)))]))
    x = x - x.mean(axis=0)
    y = loop(x, n, rng)
    return y / (np.sqrt(np.mean(y ** 2)) + 1e-9) * LEVEL[kind]
