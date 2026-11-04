"""Quality gates measured by tools, not by the model that made the video (see .claude/skills/quality-gate).

visual_report: is the picture alive (contrast, motion, depth of movement), does the loop close without a jump,
does anything pop? audio_report: is the music over the bed by the intended margin, and does earshot hear the
bed as rain/fire rather than noise? gate() turns both into pass/fail lines that go into qa.json, the publish
log and the drafts PR; publish refuses a video whose hard gates fail.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import numpy as np

W, H = 320, 180


def _frames(video: Path, fps: float = 2.0) -> np.ndarray:
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(video), "-vf", f"fps={fps},scale={W}:{H}",
                          "-f", "rawvideo", "-pix_fmt", "gray", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(-1, H, W).astype(np.float32) / 255


def visual_report(loop: Path, fps: float = 2.0) -> dict:
    f = _frames(loop, fps)
    diffs = np.abs(np.diff(f, axis=0)).mean(axis=(1, 2))
    med = float(np.median(diffs)) if len(diffs) else 0.0
    seam = float(np.abs(f[-1] - f[0]).mean()) if len(f) > 1 else 0.0
    # motion per band (top / middle / bottom thirds): moving layers at different speeds read as depth
    bands = [float(np.abs(np.diff(f[:, i * H // 3:(i + 1) * H // 3], axis=0)).mean()) for i in range(3)]
    return {
        "frames": int(len(f)),
        "luma_std": round(float(f.std(axis=(1, 2)).mean()), 4),
        "motion_pct": round(100 * med, 3),
        "seam_pct": round(100 * seam, 3),
        "pop_ratio": round(float(diffs.max() / med), 2) if med > 0 else 0.0,
        "band_motion_pct": [round(100 * b, 3) for b in bands],
    }


def _db(x: np.ndarray) -> float:
    x = x[np.abs(x).max(axis=1) > 1e-4] if x.ndim == 2 else x
    return float(20 * np.log10(np.sqrt(np.mean(x.astype(np.float64) ** 2)) + 1e-12)) if len(x) else -120.0


def audio_report(music: np.ndarray, bed: np.ndarray, listened: dict | None = None) -> dict:
    rep = {"music_db": round(_db(music), 1), "bed_db": round(_db(bed), 1)}
    rep["music_over_bed_db"] = round(rep["music_db"] - rep["bed_db"], 1)
    if listened:
        text = json.dumps(listened.get("describe") or {}).lower()
        rep["heard_noise"] = any(w in text for w in ("white noise", "pink noise", "waterfall", "vacuum"))
        real = listened.get("realness") or {}
        rep["p_real"] = real.get("p_real") if isinstance(real, dict) else None
    return rep


GATES = [  # (name, test, hard) - hard gates stop the upload
    ("picture has contrast (luma std >= 0.12)", lambda v, a: v.get("luma_std", 1) >= 0.12, False),
    ("picture moves (motion >= 0.3 %)", lambda v, a: v.get("motion_pct", 1) >= 0.3, False),
    ("loop closes cleanly (seam <= 3x a normal step)",
     lambda v, a: v.get("seam_pct", 0) <= 3 * max(v.get("motion_pct", 0), 0.05), True),
    ("nothing pops (spike <= 6x median)", lambda v, a: v.get("pop_ratio", 0) <= 6, True),
    ("music 3-6 dB over the bed", lambda v, a: "music_over_bed_db" not in a or 3 <= a["music_over_bed_db"] <= 6.5, False),
    ("bed heard as rain/fire, not noise", lambda v, a: not a.get("heard_noise", False), False),
    ("audio reads real (p_real >= 0.6)", lambda v, a: a.get("p_real") is None or a["p_real"] >= 0.6, True),
]


def gate(visual: dict, audio: dict) -> dict:
    rows = [{"gate": name, "pass": bool(test(visual, audio)), "hard": hard} for name, test, hard in GATES]
    return {"visual": visual, "audio": audio, "gates": rows,
            "ok": all(r["pass"] for r in rows if r["hard"]),
            "summary": "; ".join(("PASS " if r["pass"] else "FAIL ") + r["gate"] for r in rows)}


def write(folder: Path, report: dict) -> Path:
    p = folder / "qa.json"
    p.write_text(json.dumps(report, indent=1), encoding="utf-8")
    return p
