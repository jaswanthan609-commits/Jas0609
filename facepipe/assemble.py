"""Video assembly with ffmpeg: scene clips + voiceover + captions + background music."""

from __future__ import annotations

import random
from pathlib import Path

from .config import ChannelConfig
from .media import run

FPS = 30


def scene_clip(visual: Path, seconds: float, width: int, height: int, out: Path, fade: float = 0.0) -> Path:
    """Fit a stock clip or still image to the frame (cover + crop) for exactly `seconds`.

    fade > 0 fades the clip in from and out to near-black over `fade` seconds: sleep videos never cut,
    so a drowsy viewer is not jolted by a sudden change of picture.
    """
    cover = (
        f"scale={width}:{height}:force_original_aspect_ratio=increase,"
        f"crop={width}:{height},setsar=1"
    )
    if visual.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}:
        frames = max(1, int(seconds * FPS))
        # Slow Ken Burns zoom so stills don't look static, spread over the whole scene (a fixed step
        # finished zooming after 6 s and then sat still, which is worst on 40 s sleep scenes).
        step = 0.12 / frames
        vf = (
            f"scale={width * 2}:{height * 2}:force_original_aspect_ratio=increase,crop={width * 2}:{height * 2},"
            f"zoompan=z='min(zoom+{step:.6f},1.12)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
            f":d={frames}:s={width}x{height}:fps={FPS},setsar=1"
        )
    else:
        vf = f"{cover},fps={FPS}"
    if fade > 0:
        f = min(fade, seconds / 3)
        vf += f",fade=t=in:st=0:d={f:.2f},fade=t=out:st={seconds - f:.2f}:d={f:.2f}"
    if visual.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}:
        cmd = ["ffmpeg", "-y", "-loop", "1", "-i", str(visual), "-vf", vf]
    else:
        # Loop short clips so they always cover the narration.
        cmd = ["ffmpeg", "-y", "-stream_loop", "-1", "-i", str(visual), "-vf", vf]
    cmd += [
        "-t", f"{seconds:.3f}", "-an", "-c:v", "libx264", "-preset", "veryfast",
        "-crf", "20", "-pix_fmt", "yuv420p", str(out),
    ]
    run(cmd)
    return out


def concat(paths: list[Path], out: Path, audio: bool) -> Path:
    listing = out.with_suffix(".txt")
    listing.write_text("".join(f"file '{p.resolve()}'\n" for p in paths), encoding="utf-8")
    codec = ["-c:a", "libmp3lame", "-q:a", "2"] if audio else ["-c", "copy"]
    run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(listing), *codec, str(out)])
    return out


def pick_music(cfg: ChannelConfig) -> Path | None:
    tracks = [p for p in cfg.music_path.glob("*") if p.suffix.lower() in {".mp3", ".m4a", ".wav", ".ogg"}]
    return random.choice(tracks) if tracks else None


def final_render(
    cfg: ChannelConfig,
    video: Path,
    voice: Path,
    subtitles: Path | None,
    out: Path,
    music: Path | None,
) -> Path:
    if subtitles:
        fonts_dir = (cfg.music_path.parent / "fonts").resolve()
        sub_path = str(subtitles.resolve()).replace("\\", "/").replace(":", "\\:").replace("'", "\\'")
        sub_filter = f"ass='{sub_path}':fontsdir='{fonts_dir}'"
    else:
        sub_filter = "null"
    cmd = ["ffmpeg", "-y", "-i", str(video), "-i", str(voice)]
    if music:
        cmd += ["-stream_loop", "-1", "-i", str(music)]
        # Duck the music under the voice so narration stays clear.
        audio = (
            f"[2:a]volume={cfg.music_volume}[bg];"
            "[1:a]asplit=2[vo][sc];"
            "[bg][sc]sidechaincompress=threshold=0.03:ratio=8:attack=20:release=400[duck];"
            "[vo][duck]amix=inputs=2:duration=first:normalize=0,loudnorm=I=-14:TP=-1.5[a]"
        )
    else:
        audio = "[1:a]loudnorm=I=-14:TP=-1.5[a]"
    cmd += [
        "-filter_complex", f"[0:v]{sub_filter}[v];{audio}",
        "-map", "[v]", "-map", "[a]",
        "-c:v", "libx264", "-preset", "medium", "-crf", "19", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", str(out),
    ]
    run(cmd)
    return out


def thumbnail(video: Path, text: str, cfg: ChannelConfig, out: Path, width: int, height: int, at: float = 1.0) -> Path:
    """Grab a frame from the caption-free video and stamp big thumbnail text on it.

    Long-form thumbnails are 1280x720 (YouTube's recommended size, well under the 2 MB limit).
    """
    words = text.replace("\\", "").replace("'", "").replace(":", " ").replace("%", " percent").split()
    # Two lines when the text is long, sized so the longest line fits the frame width.
    lines = [" ".join(words)] if len(" ".join(words)) <= 12 else [
        " ".join(words[: (len(words) + 1) // 2]), " ".join(words[(len(words) + 1) // 2 :])
    ]
    longest = max(len(line) for line in lines) or 1
    size = int(min(height / 7, width * 1.6 / longest))
    filters = []
    for i, line in enumerate(lines):
        y = f"(h-{len(lines)}*{size}*1.15)/2+{i}*{size}*1.15"
        filters.append(
            f"drawtext=text='{line}':font='{cfg.font_name}':fontcolor=yellow:fontsize={size}:"
            f"borderw={max(4, size // 12)}:bordercolor=black:x=(w-text_w)/2:y={y}"
        )
    if width > height:
        filters.append("scale=1280:720")
    run(["ffmpeg", "-y", "-ss", f"{at}", "-i", str(video), "-frames:v", "1", "-q:v", "3",
         "-vf", ",".join(filters), str(out)])
    return out
