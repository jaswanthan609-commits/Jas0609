"""Cozy Hours: 90-minute ambience videos (a unique 3D scene loop + original music), no narration.

Draft: Claude picks a scene and packaging from what is breaking out (research/scan.json) -> ambience.json
plus a script.json (title, description, tags) for the review PR. Render: render3d/capture.js draws a
seamless 3D loop in headless Chromium, facepipe.music writes an original seamless piece, and ffmpeg
repeats both to full length without re-encoding the picture.

Why this shape (2026-11-04 scan, 44 breakout scene/instrumental ambience videos from channels under
100K subscribers, 21 of them from channels under a year old): median length 129 minutes (middle half
117-192), median 661K views on a median 6.6K-subscriber channel. Their titles: autumn 66%, emoji 61%,
cozy 57%, jazz 52%, a "|" separator 52%, a use (study/sleep/relax) 50%, fire 32%, rain 18%.
YouTube demonetises reused or repetitive ambience, so every upload gets its own scene and its own music.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from . import assemble, music
from .config import FORMATS, ROOT, ChannelConfig
from .media import run

RENDER3D = ROOT / "render3d"


class AmbienceSpec(BaseModel):
    title: str = Field(description="YouTube title, 60-95 characters, in the shape of breakout ambience titles: "
                       "season + place + music + '|' + mood/use, with one or two emoji, e.g. 'Autumn Fireplace Jazz | "
                       "Cozy Crackling Fire Ambience' or 'Rainy Autumn Night by the Window 🍂 Soft Jazz for Sleep & Study'.")
    description: str = Field(description="Calm description: what the viewer will see and hear, what it is good for "
                             "(sleep, study, reading), and 3-5 hashtags. Mention the music is original.")
    tags: list[str] = Field(description="10-15 YouTube search tags.")
    title_options: list[str] = Field(default_factory=list, description="3 other titles, each a different angle.")
    thumbnail_text: str = Field(description="0-3 words for the thumbnail, often empty for ambience; e.g. 'RAINY NIGHT'.")
    weather: Literal["rain", "snow", "clear", "autumn", "autumn_rain"] = Field(
        description="autumn = falling leaves outside; autumn_rain = leaves and rain.")
    time: Literal["night", "dusk", "dawn"]
    light: Literal["candle", "lamp"]
    fire: bool = Field(description="A warm fireplace glow from the side of the room.")
    outside: Literal["city", "forest", "sea", "village"]
    wall: str = Field(description="Wall colour as #rrggbb, dark and muted.")
    accent: str = Field(description="Curtain and book accent colour as #rrggbb.")
    wood: str = Field(description="Wood colour as #rrggbb.")
    props: list[Literal["books", "mug", "plant"]]
    key: Literal["C", "D", "Eb", "E", "F", "G", "A", "Bb"]
    mode: Literal["major", "minor", "dorian"]
    bpm: int = Field(description="56-76: slow and calm.")
    texture: Literal["rain", "fire", "rain_fire", "none"] = Field(description="Sound bed under the music; match the scene.")
    style: Literal["jazz", "piano"] = Field(description="jazz = brushed drums, walking bass, jazz piano (52% of breakout "
                                            "scene ambience titles say jazz); piano = solo soft piano.")


def draft(cfg: ChannelConfig, topic: str, folder: Path, seed: int, notes: str = "") -> AmbienceSpec:
    from .script import VideoScript, _parse, save_script

    prompt = (f"Design one ambience video for this channel: a single cozy window-nook scene with music. "
              f"Idea: {topic}\nMake the scene, weather, light and music fit the idea and each other."
              + (f"\n\n{notes}" if notes else ""))
    spec = _parse(cfg, prompt, AmbienceSpec, max_tokens=3000)
    if spec.style == "jazz":  # CC BY needs the credit in the description
        from . import samples
        spec.description = spec.description.rstrip() + "\n\nMusic: an original composition for this video. Instrument samples:\n" \
            + "\n".join(f"- {c}" for c in samples.credits())
    data = spec.model_dump() | {"seed": seed}
    (folder / "ambience.json").write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    save_script(VideoScript(title=spec.title, description=spec.description, tags=spec.tags,
                            title_options=spec.title_options, thumbnail_text=spec.thumbnail_text,
                            facts_to_check=[], scenes=[]), folder / "script.json")
    return spec


def _node_env() -> dict:
    import os

    env = dict(os.environ)
    if not (RENDER3D / "node_modules").exists():
        raise RuntimeError("Run `npm install --prefix render3d && npx --prefix render3d playwright install chromium` first.")
    return env


def render_loop(spec: dict, out: Path) -> Path:
    scene = {k: spec[k] for k in ("weather", "time", "light", "fire", "outside", "wall", "accent", "wood", "props", "seed")}
    scene.update(loop=12, fps=24)
    subprocess.run(["node", str(RENDER3D / "capture.js"), json.dumps(scene), str(out)], check=True, env=_node_env())
    return out


def render(cfg: ChannelConfig, folder: Path, seconds: int | None = None, log=print) -> tuple[Path, Path]:
    """Render folder/video.mp4 and folder/thumbnail.jpg from folder/ambience.json."""
    spec = json.loads((folder / "ambience.json").read_text(encoding="utf-8"))
    seconds = seconds or FORMATS["ambience"][2]
    work = folder / "work"
    shutil.rmtree(work, ignore_errors=True)
    work.mkdir()
    log(f"[{cfg.slug}] Ambience: 3D loop ({spec['weather']}, {spec['time']}, {spec['light']}, {spec['outside']})")
    loop = render_loop(spec, work / "loop.mp4")
    log(f"  music: {spec['key']} {spec['mode']} {spec['bpm']} bpm, {spec['texture']}")
    if spec.get("style", "jazz") == "jazz":
        from . import samples
        samples.fetch(log=log)
    track = music.compose(spec["key"], spec["mode"], spec["bpm"], bars=72, texture=spec["texture"], seed=spec["seed"],
                          style=spec.get("style", "jazz"))
    wav = music.write_wav(track, work / "music.wav")
    video = folder / "video.mp4"
    run(["ffmpeg", "-y", "-stream_loop", "-1", "-i", str(loop), "-stream_loop", "-1", "-i", str(wav),
         "-t", str(seconds), "-map", "0:v", "-map", "1:a", "-c:v", "copy",
         "-af", f"afade=t=in:d=4,afade=t=out:st={seconds - 6}:d=6,loudnorm=I=-20:TP=-2",
         "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(video)])
    width, height, _ = FORMATS["ambience"]
    thumb = folder / "thumbnail.jpg"
    if spec.get("thumbnail_text", "").strip():
        assemble.thumbnail(loop, spec["thumbnail_text"], cfg, thumb, width, height, at=2.0)
    else:
        run(["ffmpeg", "-y", "-ss", "2", "-i", str(loop), "-frames:v", "1", "-q:v", "3", "-vf", "scale=1280:720", str(thumb)])
    return video, thumb
