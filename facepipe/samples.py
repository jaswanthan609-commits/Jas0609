"""Real recorded instruments for the ambience music: a Wurlitzer electric piano, a double bass and a jazz kit.

earshot heard the all-synthesised score as "code-synthesized" (p_real 0.13-0.35, "a music box", "a synth pad").
These are real multi-sampled instruments from the SFZ Instruments collection on GitHub, pinned to a commit and
fetched sparsely (only the articulations we play, ~150 MB) into a cache that CI keeps between runs. The notes,
voicings and arrangement are still ours and new for every video; only the instrument sounds are recorded.

Licences (checked on each repo's LICENSE file, 2026-11-04):
- Wurlitzer EP200 by Greg Sullivan, mapped by kinwie: CC BY 3.0 -> credit line required (see credits()).
- Sneakybass (double bass, finger) by Karoryfer Samples: CC0 1.0.
- Virtuosity Drums by Versilian Studios and Karoryfer Samples: CC0 1.0.
- Osiris Piano (upright, una corda, mic A) by Versilian Studios and Karoryfer Samples: CC0 1.0.
"""

from __future__ import annotations

import os
import re
import subprocess
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

import numpy as np

from .config import ROOT

SR = 44100
PITCH = {"c": 0, "db": 1, "d": 2, "eb": 3, "e": 4, "f": 5, "gb": 6, "g": 7, "ab": 8, "a": 9, "bb": 10, "b": 11}

LIBS = {
    "wurli": dict(repo="https://github.com/sfzinstruments/GregSullivan.E-Pianos.git",
                  commit="8c3e581acda3594b553948ff0222d4f84a698376",
                  paths=["Wurlitzer EP200/Samples/*", "LICENSE"],
                  licence="CC BY 3.0",
                  credit="Wurlitzer EP200 samples by Greg Sullivan (sullivang.net), SFZ mapping by kinwie, "
                         "licensed CC BY 3.0 (creativecommons.org/licenses/by/3.0)"),
    "bass": dict(repo="https://github.com/sfzinstruments/karoryfer.sneakybass.git",
                 commit="cc1a67e5c913678b85eaad1a3b5cb180d3be3e2d",
                 paths=["Samples/finger/*", "LICENSE"],
                 licence="CC0 1.0",
                 credit="Double bass: Sneakybass by Karoryfer Samples (CC0)"),
    "drums": dict(repo="https://github.com/sfzinstruments/virtuosity_drums.git",
                  commit="9f04cf9a734527edfbb0a4eee1f674e45bbf71bc",
                  paths=["Samples/oh/ride/oh_ride_ride_*", "Samples/oh/hh/oh_hh_pedal_*",
                         "Samples/oh/snare/oh_snare_crossstick_*", "Samples/oh/kick/oh_kick_snoff_*", "LICENSE"],
                  licence="CC0 1.0",
                  credit="Drums: Virtuosity Drums by Versilian Studios and Karoryfer Samples (CC0)"),
    "piano": dict(repo="https://github.com/sfzinstruments/Osiris_Piano.git",
                  commit="18c6afccb60cff458edbf7c394571783e074e1e9",
                  paths=["UC/A/*", "LICENSE"],
                  licence="CC0 1.0",
                  credit="Piano: Osiris Piano by Versilian Studios and Karoryfer Samples (CC0)"),
}
JAZZ = ("wurli", "bass", "drums")
PIANO = ("piano",)


def home() -> Path:
    return Path(os.environ.get("FACEPIPE_SAMPLES", ROOT / ".cache" / "samples"))


def _ready(name: str) -> bool:
    d = home() / name
    return (d / ".ok").exists()


def fetch(names: list[str] | None = None, log=print) -> bool:
    """Sparse-fetch the pinned sample sets. Returns True when all are present. Safe to call repeatedly."""
    ok = True
    for name in names or list(LIBS):
        if _ready(name):
            continue
        lib, d = LIBS[name], home() / name
        d.mkdir(parents=True, exist_ok=True)
        log(f"  samples: fetching {name} ({lib['licence']})")
        git = ["git", "-C", str(d)]
        try:
            if not (d / ".git").exists():
                subprocess.run(git + ["init", "-q"], check=True)
                subprocess.run(git + ["remote", "add", "origin", lib["repo"]], check=True)
            subprocess.run(git + ["sparse-checkout", "set", "--no-cone", *lib["paths"]], check=True)
            subprocess.run(git + ["fetch", "-q", "--depth", "1", "--filter=blob:none", "origin", lib["commit"]],
                           check=True, timeout=1200)
            subprocess.run(git + ["checkout", "-q", "FETCH_HEAD"], check=True, timeout=1200)
            (d / ".ok").write_text(lib["commit"])
        except (subprocess.SubprocessError, OSError) as e:
            log(f"  samples: {name} unavailable ({e}); falling back to synthesis")
            ok = False
    return ok


def available(names: tuple[str, ...] = JAZZ) -> bool:
    return all(_ready(n) for n in names)


def credits(names: tuple[str, ...] = JAZZ) -> list[str]:
    return [LIBS[n]["credit"] for n in names]


def _midi(name: str, octave: str) -> int:
    return 12 * (int(octave) + 1) + PITCH[name]


@lru_cache(maxsize=4096)
def _load(path: str) -> np.ndarray:
    import soundfile as sf

    x, sr = sf.read(path, dtype="float32", always_2d=True)
    x = x.mean(axis=1)
    if sr != SR:
        t = np.arange(int(len(x) * SR / sr)) * (sr / SR)
        x = np.interp(t, np.arange(len(x)), x).astype("float32")
    return x


def _repitch(x: np.ndarray, semitones: float) -> np.ndarray:
    if abs(semitones) < 1e-3:
        return x
    ratio = 2 ** (semitones / 12)
    t = np.arange(int(len(x) / ratio)) * ratio
    return np.interp(t, np.arange(len(x)), x).astype("float32")


def _shape(x: np.ndarray, dur: float | None, release: float) -> np.ndarray:
    if dur is None:
        return x
    n, r = int(dur * SR), int(release * SR)
    x = x[: n + r].copy()
    if len(x) > n:
        x[n:] *= np.linspace(1, 0, len(x) - n) ** 2
    return x


@dataclass
class Pitched:
    """A multi-sampled instrument: entries of (midi note, velocity layer 0..1, round robin, file)."""
    entries: list[tuple[int, float, str]] = field(default_factory=list)
    release: float = 0.25
    gain: float = 1.0

    def note(self, midi: int, vel: float, dur: float | None, rng: np.random.Generator) -> np.ndarray:
        cost = [abs(m - midi) + 4 * abs(layer - vel) + rng.random() * 0.3 for m, layer, _ in self.entries]
        m, _, path = self.entries[int(np.argmin(cost))]
        x = _repitch(_load(path), midi - m)
        return _shape(x, dur, self.release) * self.gain * (0.35 + 0.65 * vel)


@dataclass
class Kit:
    pieces: dict[str, list[tuple[float, str]]] = field(default_factory=dict)

    def hit(self, piece: str, vel: float, rng: np.random.Generator, dur: float | None = None) -> np.ndarray:
        opts = self.pieces[piece]
        best = min(abs(layer - vel) for layer, _ in opts)
        pick = [p for layer, p in opts if abs(layer - vel) == best]
        return _shape(_load(pick[rng.integers(len(pick))]), dur, 0.3) * (0.4 + 0.6 * vel)


def _layers(found: dict[str, list]) -> dict[str, float]:
    keys = sorted(found)
    return {k: (i / (len(keys) - 1) if len(keys) > 1 else 0.5) for i, k in enumerate(keys)}


@lru_cache(maxsize=1)
def piano() -> Pitched:
    """Soft upright piano. Osiris names notes the Yamaha way (A3 = 440 Hz = MIDI 69)."""
    inst = Pitched(release=0.45, gain=1.0)
    for p in sorted((home() / "piano" / "UC" / "A").glob("*.flac")):
        m = re.fullmatch(r"Piano_UC_MicA_([A-G])(-?\d)_vl(\d)", p.stem)
        if m:
            inst.entries.append((12 * (int(m[2]) + 2) + PITCH[m[1].lower()], (int(m[3]) - 1) * 1.0, str(p)))
    if not inst.entries:
        raise RuntimeError("piano samples missing; run facepipe.samples.fetch(['piano'])")
    return inst


@lru_cache(maxsize=1)
def instruments() -> tuple[Pitched, Pitched, Kit]:
    """(wurlitzer, double bass, jazz kit) from the fetched sample sets."""
    root = home()
    dyn = {"pp": 0.0, "mp": 0.35, "f": 0.7, "ff": 1.0}
    wurli = Pitched(release=0.35, gain=1.0)
    for p in sorted((root / "wurli" / "Wurlitzer EP200" / "Samples").glob("*.flac")):
        m = re.fullmatch(r"([a-g]b?)(\d)(pp|mp|ff|f)", p.stem)
        if m:
            wurli.entries.append((_midi(m[1], m[2]), dyn[m[3]], str(p)))
    bass = Pitched(release=0.12, gain=1.0)
    for p in sorted((root / "bass" / "Samples" / "finger").glob("*.wav")):
        m = re.fullmatch(r"sneakybass_([a-g]b?)(\d)_finger_rr(\d)", p.stem)
        if m:
            bass.entries.append((_midi(m[1], m[2]), 0.5, str(p)))
    kit = Kit()
    for piece, pat in {"ride": "ride/oh_ride_ride_vl*", "pedal": "hh/oh_hh_pedal_vl*",
                       "xstick": "snare/oh_snare_crossstick_vl*", "kick": "kick/oh_kick_snoff_vl*"}.items():
        files = sorted((root / "drums" / "Samples" / "oh").glob(pat + ".flac"))
        by_vl: dict[str, list[str]] = {}
        for p in files:
            vl = re.search(r"_vl(\d+)", p.stem)
            by_vl.setdefault(f"{int(vl[1]):02d}" if vl else "01", []).append(str(p))
        layer = _layers(by_vl)
        kit.pieces[piece] = [(layer[k], f) for k, fs in by_vl.items() for f in fs]
    if not (wurli.entries and bass.entries and all(kit.pieces.values())):
        raise RuntimeError("sample sets incomplete; run facepipe.samples.fetch()")
    return wurli, bass, kit
