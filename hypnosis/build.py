"""Build personal self-hypnosis sessions: Kokoro voice (offline), a soft ambient pad, and a breathing-circle video.

Usage:  python hypnosis/build.py [session ...] [--voice-test]
Needs:  pip install kokoro-onnx soundfile numpy pillow ; ffmpeg on PATH
        KOKORO_DIR with kokoro-v1.0.onnx and voices-v1.0.bin (kokoro-onnx GitHub release "model-files-v1.0").
Output: hypnosis/out/<session>.mp4 and .m4a
"""
import os
import re
import subprocess
import sys
from pathlib import Path

import numpy as np
import soundfile as sf
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = Path(__file__).resolve().parent
SCRIPTS = HERE / "scripts"
OUT = HERE / "out"
WORK = OUT / "work"
MODELS = Path(os.environ.get("KOKORO_DIR", HERE / "models"))
SR = 24000

# Voice: a blend of two soft American female voices, slowed down. af_heart is Kokoro's most natural voice,
# af_nicole adds a breathy, close-mic quality. Override with HYPNO_VOICE="af_heart:1" etc.
VOICE = os.environ.get("HYPNO_VOICE", "af_heart:0.6,af_nicole:0.4")
SPEED = float(os.environ.get("HYPNO_SPEED", "0.82"))
LINE_GAP = 1.1      # seconds of quiet after each spoken line
PARA_GAP = 2.5      # extra quiet at a blank line
BREATH = 10.0       # one visual breath cycle: 4 s in, 6 s out (six breaths a minute)
W, H, FPS = 1920, 1080, 24

_kokoro = None


def kokoro():
    global _kokoro
    if _kokoro is None:
        from kokoro_onnx import Kokoro
        _kokoro = Kokoro(str(MODELS / "kokoro-v1.0.onnx"), str(MODELS / "voices-v1.0.bin"))
    return _kokoro


def voice_style(spec):
    k = kokoro()
    parts = [p.split(":") for p in spec.split(",")]
    total = sum(float(w) for _, w in parts)
    return sum(k.get_voice_style(n) * (float(w) / total) for n, w in parts)


def parse(name):
    """Return (meta, items) where items are ('say', text) or ('rest', seconds)."""
    meta, items = {}, []
    for raw in (SCRIPTS / f"{name}.txt").read_text().splitlines():
        line = raw.strip()
        if line.startswith("#"):
            continue
        if line.startswith("@include"):
            items += parse(line.split()[1])[1]
        elif line.startswith("@"):
            key, _, val = line[1:].partition(" ")
            meta[key] = val.strip() or True
        elif not line:
            items.append(("rest", PARA_GAP))
        elif m := re.fullmatch(r"\[pause (\d+(?:\.\d+)?)\]", line):
            items.append(("rest", float(m.group(1))))
        else:
            items.append(("say", line))
    return meta, items


def silence(sec):
    return np.zeros(int(sec * SR), dtype=np.float32)


def fade_edges(x, ms=15):
    n = min(int(SR * ms / 1000), len(x) // 2)
    if n:
        ramp = np.linspace(0, 1, n, dtype=np.float32)
        x[:n] *= ramp
        x[-n:] *= ramp[::-1]
    return x


def speak(items, style, lead_in=6.0):
    k = kokoro()
    chunks = [silence(lead_in)]
    for kind, val in items:
        if kind == "rest":
            chunks.append(silence(val))
            continue
        audio, sr = k.create(val, voice=style, speed=SPEED, lang="en-us")
        assert sr == SR
        chunks += [fade_edges(audio.astype(np.float32)), silence(LINE_GAP)]
    chunks.append(silence(8.0))
    return np.concatenate(chunks)


def ambient(seconds, seed=7):
    """Warm drone: soft sine chord (A2, E3, A3, C#4) with slow swells, plus quiet brown noise like distant surf."""
    rng = np.random.default_rng(seed)
    t = np.arange(int(seconds * SR)) / SR
    pad = np.zeros_like(t)
    for f, amp, lfo in [(110, 0.5, 0.031), (164.8, 0.32, 0.023), (220, 0.22, 0.041), (277.2, 0.12, 0.017)]:
        swell = 0.6 + 0.4 * np.sin(2 * np.pi * lfo * t + rng.uniform(0, 6.28))
        detune = np.sin(2 * np.pi * f * t) + np.sin(2 * np.pi * (f * 1.003) * t)
        pad += amp * swell * detune
    brown = np.cumsum(rng.normal(0, 1, len(t)))
    brown -= np.convolve(brown, np.ones(SR) / SR, mode="same")  # remove drift
    brown /= np.max(np.abs(brown)) + 1e-9
    waves = 0.5 + 0.5 * np.sin(2 * np.pi * t / BREATH - np.pi / 2)  # surf rises with the breath cycle
    mix = pad / np.max(np.abs(pad)) * 0.6 + brown * 0.4 * (0.4 + 0.6 * waves)
    fade = np.minimum(1, np.minimum(t / 8, (seconds - t) / 10))
    return (mix * fade * 0.9).astype(np.float32)


def render_loop(path):
    """One seamless 10 s breathing cycle: a glowing circle grows for 4 s, settles for 6 s, with slow drifting motes."""
    if path.exists():
        return
    frames = WORK / "loop"
    frames.mkdir(parents=True, exist_ok=True)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    cx, cy = W / 2, H / 2
    dist = np.hypot(xx - cx, yy - cy)
    top, bottom = np.array([14, 18, 40.0]), np.array([10, 42, 56.0])
    grad = (top + (bottom - top) * (yy / H)[..., None])
    vignette = np.clip(1 - (dist / (W * 0.75)) ** 2, 0.35, 1)[..., None]
    base = grad * vignette
    rng = np.random.default_rng(3)
    motes = [(rng.uniform(0, W), rng.uniform(0, H), rng.uniform(20, 90), rng.uniform(1.5, 4), rng.uniform(0, 6.28),
              rng.integers(1, 3)) for _ in range(46)]
    # Aurora: a few large soft colour clouds that orbit slowly; their paths close every 10 s so the loop is seamless.
    clouds = [((0.30, 0.35), (60, 40, 120.0), 520), ((0.72, 0.62), (20, 90, 110.0), 600),
              ((0.55, 0.25), (40, 70, 140.0), 460), ((0.25, 0.75), (30, 100, 90.0), 480)]
    n = int(BREATH * FPS)
    for i in range(n):
        t = i / FPS
        if t < 4:
            phase = 0.5 - 0.5 * np.cos(np.pi * t / 4)                 # inhale, ease in-out
        else:
            phase = 0.5 + 0.5 * np.cos(np.pi * (t - 4) / 6)           # longer exhale
        img = base.copy()
        for k, ((fx, fy), ccol, size) in enumerate(clouds):
            a = 2 * np.pi * t / BREATH + k * 1.7
            px, py = fx * W + 140 * np.cos(a), fy * H + 90 * np.sin(a)
            blob = np.exp(-((xx - px) ** 2 + (yy - py) ** 2) / (2 * size ** 2))
            img += blob[..., None] * np.array(ccol) * 0.32
        # Orb: no hard edge. Bright pearly core fading to a translucent rim, then a wide halo.
        r = 150 + 130 * phase
        core = np.clip(1 - (dist / r) ** 2, 0, 1) ** 0.6
        rim = np.exp(-((dist - r) ** 2) / (2 * 10.0 ** 2))
        halo = np.exp(-np.maximum(dist - r, 0) ** 2 / (2 * (70 + 50 * phase) ** 2))
        col = np.array([135, 178, 210.0])
        img += (core * (0.32 + 0.18 * phase))[..., None] * col
        img += (rim * 0.35)[..., None] * col + (halo * (0.30 + 0.15 * phase))[..., None] * col
        # Ripples drift outward during the slow exhale and fade away.
        if t >= 4:
            for lag in (0.0, 1.6, 3.2):
                u = (t - 4 - lag) / 6
                if 0 < u < 1:
                    rr = 290 + 420 * u
                    ring = np.exp(-((dist - rr) ** 2) / (2 * 4.0 ** 2)) * (1 - u) ** 1.5 * 0.5 * min(1, (BREATH - t) / 1.5)
                    img += ring[..., None] * col
        frame = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8))
        layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(layer)
        for x0, y0, rad, size, ph, loops in motes:
            a = 2 * np.pi * loops * t / BREATH + ph
            x, y = x0 + rad * np.cos(a), y0 + rad * 0.6 * np.sin(a)
            alpha = int(70 + 60 * np.sin(a * 0.5 + ph) ** 2)
            d.ellipse([x - size, y - size, x + size, y + size], fill=(200, 225, 240, alpha))
        layer = layer.filter(ImageFilter.GaussianBlur(1.6))
        frame = Image.alpha_composite(frame.convert("RGBA"), layer).convert("RGB")
        frame.save(frames / f"{i:04d}.png")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS), "-i", str(frames / "%04d.png"),
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18", str(path)], check=True)


def title_card(meta, path):
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    big = ImageFont.truetype(str(HERE / "fonts" / "BodoniModa-Italic-VF.ttf"), 120)
    small = ImageFont.truetype(str(HERE / "fonts" / "BodoniModa-VF.ttf"), 44)
    for text, font, y, a in [(meta["title"], big, H * 0.16, 235), (meta["subtitle"], small, H * 0.80, 200),
                             ("Headphones on. Never while driving.", small, H * 0.87, 150)]:
        w = d.textlength(text, font=font)
        d.text(((W - w) / 2, y), text, font=font, fill=(232, 240, 245, a))
    img.save(path)


def master(voice, seconds):
    """Mix voice over the pad and apply soft EQ (tamed sibilance), a small warm room, and loudness normalising."""
    pad = ambient(seconds)
    v = np.zeros_like(pad)
    v[: len(voice)] = voice
    raw = WORK / "mix_in.wav"
    sf.write(raw, np.stack([v, pad], axis=1), SR)
    out = WORK / "mix.wav"
    graph = ("[0:a]pan=mono|c0=c0,highpass=f=90,equalizer=f=5500:t=q:w=1.2:g=-5,lowpass=f=10500,"
             "aecho=0.85:0.6:45|85:0.18|0.10,acompressor=threshold=-22dB:ratio=2.5:attack=15:release=250[v];"
             "[0:a]pan=mono|c0=c1,volume=0.16[p];"
             "[v][p]amix=inputs=2:normalize=0,aformat=channel_layouts=stereo,loudnorm=I=-20:TP=-2:LRA=11[a]")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(raw), "-filter_complex", graph, "-map", "[a]",
                    "-ar", "48000", str(out)], check=True)
    return out


def build(name):
    meta, items = parse(name)
    print(f"[{name}] speaking {sum(1 for k, _ in items if k == 'say')} lines")
    voice = speak(items, voice_style(VOICE))
    seconds = len(voice) / SR
    print(f"[{name}] {seconds / 60:.1f} min")
    mix = master(voice, seconds)
    loop = WORK / "breath_loop.mp4"
    render_loop(loop)
    card = WORK / f"{name}_title.png"
    title_card(meta, card)
    OUT.mkdir(exist_ok=True)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(mix), "-c:a", "aac", "-b:a", "160k",
                    str(OUT / f"{name}.m4a")], check=True)
    # Loop the breathing cycle for the whole session, drift the hue slowly, fade the title in and out,
    # and fade to near-black in the last 20 seconds.
    vf = (f"[0:v]hue=h='12*sin(2*PI*t/300)',fade=t=in:st=0:d=4,fade=t=out:st={seconds - 6:.2f}:d=6[bg];"
          f"[1:v]format=rgba,fade=t=in:st=1:d=3:alpha=1,fade=t=out:st=16:d=5:alpha=1[tt];"
          f"[bg][tt]overlay=0:0:enable='lt(t,22)'[v]")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-stream_loop", "-1", "-i", str(loop),
                    "-loop", "1", "-framerate", str(FPS), "-i", str(card), "-i", str(mix),
                    "-filter_complex", vf, "-map", "[v]", "-map", "2:a", "-t", f"{seconds:.2f}",
                    "-c:v", "libx264", "-preset", "medium", "-crf", "26", "-pix_fmt", "yuv420p", "-r", str(FPS),
                    "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", str(OUT / f"{name}.mp4")], check=True)
    print(f"[{name}] done -> {OUT / name}.mp4")


def voice_test():
    """Short clips of candidate voices, to choose by ear."""
    line = ("Let your shoulders drop, just a little, on the next out breath. "
            "There is nothing you need to do well here. Just follow along, in your own way.")
    OUT.mkdir(parents=True, exist_ok=True)
    for spec in ["af_heart:0.6,af_nicole:0.4", "af_heart:1", "af_nicole:1", "bf_emma:1", "af_sky:0.5,af_heart:0.5"]:
        a, _ = kokoro().create(line, voice=voice_style(spec), speed=SPEED, lang="en-us")
        sf.write(OUT / f"voice-{spec.replace(':', '').replace(',', '+')}.wav", a, SR)


if __name__ == "__main__":
    WORK.mkdir(parents=True, exist_ok=True)
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if "--voice-test" in sys.argv:
        voice_test()
    for s in args or sorted(p.stem for p in SCRIPTS.glob("[0-9]*.txt")):
        build(s)
