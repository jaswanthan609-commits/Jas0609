"""Original, seamless background music for ambience videos, synthesised from a seed (numpy only).

Every video gets its own piece: key, mode, tempo, chord progression, melody and texture all come from
the scene spec and its seed, so no two uploads share a soundtrack (YouTube's "repetitive content" rule
hits ambience channels that reuse one track). The sound: a soft electric piano (FM synthesis), a warm
pad, a gentle bass, then a convolution reverb, with rain or fire textures underneath.

The piece is rendered circularly (the reverb tail wraps onto the start), so it loops without a seam
for hours. Nothing here is sampled from anyone else's recording.
"""

from __future__ import annotations

import wave
from pathlib import Path

import numpy as np

SR = 44100
NOTES = {"C": 0, "C#": 1, "Db": 1, "D": 2, "D#": 3, "Eb": 3, "E": 4, "F": 5, "F#": 6, "Gb": 6, "G": 7,
         "G#": 8, "Ab": 8, "A": 9, "A#": 10, "Bb": 10, "B": 11}
SCALES = {"major": [0, 2, 4, 5, 7, 9, 11], "minor": [0, 2, 3, 5, 7, 8, 10], "dorian": [0, 2, 3, 5, 7, 9, 10]}
# Progressions as scale degrees (0 = tonic); every chord is a stacked 7th inside the scale.
PROGRESSIONS = [[0, 5, 3, 4], [0, 3, 5, 4], [5, 3, 0, 4], [0, 2, 3, 3], [0, 5, 1, 4], [3, 4, 2, 5]]


def _hz(midi: float) -> float:
    return 440.0 * 2 ** ((midi - 69) / 12)


def _chord(root: int, scale: list[int], degree: int) -> list[int]:
    def note(step: int) -> int:
        octave, idx = divmod(degree + step, 7)
        return root + scale[idx] + 12 * octave
    return [note(0), note(2), note(4), note(6)]


def _epiano(f: float, dur: float, vel: float) -> np.ndarray:
    t = np.arange(int(dur * SR)) / SR
    index = 1.8 * np.exp(-t * 3.0) + 0.25
    env = (1 - np.exp(-t * 400)) * np.exp(-t * (1.1 + f / 900))
    tone = np.sin(2 * np.pi * f * t + index * np.sin(2 * np.pi * f * t))
    tone += 0.18 * np.sin(2 * np.pi * 2 * f * t) * np.exp(-t * 4)  # bell-ish attack
    return tone * env * vel


def _pad(freqs: list[float], dur: float, vel: float) -> np.ndarray:
    t = np.arange(int(dur * SR)) / SR
    env = np.minimum(1, t / 1.5) * np.minimum(1, (dur - t) / 1.5).clip(0)
    out = np.zeros_like(t)
    for f in freqs:
        for det in (-0.12, 0.0, 0.13):
            out += np.sin(2 * np.pi * f * (1 + det / 100) * t + det * 7)
    return out * env * vel / (len(freqs) * 3)


def _lowpass(x: np.ndarray, cutoff: float) -> np.ndarray:
    """One-pole low-pass, vectorised through the FFT (good enough for noise beds)."""
    spec = np.fft.rfft(x)
    freqs = np.fft.rfftfreq(len(x), 1 / SR)
    spec /= np.sqrt(1 + (freqs / cutoff) ** 2)
    return np.fft.irfft(spec, n=len(x))


def _reverb(x: np.ndarray, seconds: float, rng: np.random.Generator) -> np.ndarray:
    """Circular convolution with a decaying-noise impulse (a soft room), done with one FFT."""
    n = len(x)
    t = np.arange(int(seconds * SR)) / SR
    ir = rng.standard_normal(len(t)) * np.exp(-t * 6.9 / seconds)
    ir = _lowpass(ir, 5000)
    ir /= np.sqrt(np.sum(ir ** 2))
    pad = np.zeros(n); pad[: len(ir)] = ir
    return np.fft.irfft(np.fft.rfft(x) * np.fft.rfft(pad), n=n)  # circular: the tail wraps to the start


def compose(key: str = "D", mode: str = "major", bpm: int = 66, bars: int = 64, texture: str = "rain",
            seed: int = 1) -> np.ndarray:
    """Return a stereo float array (n, 2) in [-1, 1] that loops seamlessly."""
    rng = np.random.default_rng(seed)
    root = 48 + NOTES.get(key, 2)
    scale = SCALES.get(mode, SCALES["major"])
    prog = PROGRESSIONS[seed % len(PROGRESSIONS)]
    beat = 60 / bpm
    n = int(bars * 4 * beat * SR)
    left, right = np.zeros(n), np.zeros(n)

    def add(sig: np.ndarray, start: float, pan: float) -> None:
        i = int(start * SR) % n
        for buf, gain in ((left, 1 - pan), (right, pan)):
            end = i + len(sig)
            if end <= n:
                buf[i:end] += sig * gain
            else:  # wrap: the piece is circular
                buf[i:] += sig[: n - i] * gain
                buf[: end - n] += sig[n - i:] * gain

    melody_scale = [root + 12 + s for s in scale] + [root + 24 + s for s in scale[:5]]
    last = len(melody_scale) // 2
    for bar in range(bars):
        start = bar * 4 * beat
        chord = _chord(root, scale, prog[bar % len(prog)])
        add(_pad([_hz(m) for m in chord], 4 * beat + 1.5, 0.22), start, 0.5)
        add(_epiano(_hz(chord[0] - 12), 4 * beat, 0.30), start, 0.45)  # bass
        # soft rolled chord on beat 1, sometimes again on beat 3
        for k, m in enumerate(chord[1:] + [chord[0] + 12]):
            add(_epiano(_hz(m), 3.5, 0.10), start + k * 0.06, 0.35 + 0.1 * k)
        if rng.random() < 0.5:
            for k, m in enumerate(chord[1:]):
                add(_epiano(_hz(m), 3.0, 0.07), start + 2 * beat + k * 0.05, 0.6 - 0.1 * k)
        # sparse melody: a slow random walk on the scale; rests are as important as notes
        if bar % 8 >= 2:
            for b in range(4):
                if rng.random() < 0.42:
                    last = int(np.clip(last + rng.choice([-2, -1, -1, 0, 1, 1, 2]), 0, len(melody_scale) - 1))
                    add(_epiano(_hz(melody_scale[last]), 2.8, 0.13), start + b * beat + rng.random() * 0.03,
                        0.3 + 0.4 * rng.random())
    music = np.stack([left, right], axis=1)
    music = np.stack([_reverb(music[:, 0], 3.2, rng) * 0.5 + music[:, 0] * 0.6,
                      _reverb(music[:, 1], 3.2, rng) * 0.5 + music[:, 1] * 0.6], axis=1)
    music = _lowpass_stereo(music, 6500)
    music /= np.max(np.abs(music)) + 1e-9
    music *= 0.55
    bed = texture_bed(texture, n, rng)
    out = music + bed
    return out / max(1.0, np.max(np.abs(out)) / 0.95)


def _lowpass_stereo(x: np.ndarray, cutoff: float) -> np.ndarray:
    return np.stack([_lowpass(x[:, 0], cutoff), _lowpass(x[:, 1], cutoff)], axis=1)


def texture_bed(texture: str, n: int, rng: np.random.Generator) -> np.ndarray:
    """Rain, fire crackle or neither, generated circularly so it loops without a seam."""
    out = np.zeros((n, 2))
    if texture in {"rain", "rain_fire"}:
        for ch in range(2):
            noise = _lowpass(rng.standard_normal(n), 2200) - _lowpass(rng.standard_normal(n), 300) * 0.3
            swell = 1 + 0.15 * np.sin(2 * np.pi * np.arange(n) / n * 3 + ch)  # whole cycles: seamless
            out[:, ch] += noise / (np.std(noise) + 1e-9) * 0.05 * swell
            drops = np.zeros(n)
            idx = rng.integers(0, n, size=n // SR * 25)
            drops[idx] = rng.random(len(idx)) * 0.5
            out[:, ch] += _lowpass(drops, 3500) * 0.25
    if texture in {"fire", "rain_fire"}:
        crack = np.zeros(n)
        idx = rng.integers(0, n, size=n // SR * 6)
        crack[idx] = rng.random(len(idx)) ** 3
        crack = _lowpass(crack, 4000) * 0.6
        rumble = _lowpass(rng.standard_normal(n), 180)
        rumble = rumble / (np.std(rumble) + 1e-9) * 0.03
        out[:, 0] += crack + rumble
        out[:, 1] += np.roll(crack, 900) + rumble
    return out


def write_wav(samples: np.ndarray, path: Path) -> Path:
    data = (np.clip(samples, -1, 1) * 32767).astype("<i2")
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(data.tobytes())
    return path
