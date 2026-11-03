"""End-to-end: topic -> script -> voice -> visuals -> captions -> final video -> (upload)."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from . import assemble, captions, script as scriptmod, visuals, voice
from .config import FORMATS, ChannelConfig
from .media import require_ffmpeg

SAMPLE_SCRIPT = Path(__file__).parent / "sample_script.json"


@dataclass
class Result:
    folder: Path
    video: Path
    thumbnail: Path
    script: scriptmod.VideoScript
    video_id: str | None = None
    publish_at: datetime | None = None


def _slug(text: str) -> str:
    ascii_part = re.sub(r"[^a-zA-Z0-9]+", "-", text).strip("-").lower()[:40]
    return ascii_part or "video"


def make_video(
    cfg: ChannelConfig,
    topic: str | None,
    fmt: str = "short",
    offline: bool = False,
    script_path: Path | None = None,
    log=print,
) -> Result:
    """Build one finished video. offline=True needs no API keys or network (for testing)."""
    require_ffmpeg()
    width, height, _ = FORMATS[fmt]

    # 1. Script
    if script_path:
        vs = scriptmod.load_script(script_path)
    elif offline:
        vs = scriptmod.load_script(SAMPLE_SCRIPT)
    else:
        if not topic:
            raise ValueError("A topic is required unless --script or --offline is given.")
        log(f"Writing {fmt} script with {cfg.claude_model}: {topic}")
        vs = scriptmod.write_script(cfg, topic, fmt)

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    folder = cfg.output_path / f"{stamp}-{fmt}-{_slug(topic or vs.title)}"
    work = folder / "work"
    work.mkdir(parents=True, exist_ok=True)
    scriptmod.save_script(vs, folder / "script.json")
    log(f"Title: {vs.title}  ({len(vs.scenes)} scenes) -> {folder}")

    # 2-3. Voice and visuals per scene
    used_ids: set[int] = set()
    voice_parts, clip_parts, timeline = [], [], []
    for i, scene in enumerate(vs.scenes):
        audio = work / f"voice_{i:03d}.mp3"
        if offline:
            seconds = voice.synthesize_placeholder(scene.narration, audio)
        else:
            seconds = voice.synthesize(cfg, scene.narration, audio)
        voice_parts.append(audio)

        stem = work / f"visual_{i:03d}"
        visual = None if offline else visuals.fetch_stock(scene.visual_query, width, height, stem, used_ids)
        if visual is None:
            if not offline:
                log(f"  no stock result for '{scene.visual_query}', using placeholder")
            visual = visuals.placeholder(i, width, height, stem)
        clip_parts.append(assemble.scene_clip(visual, seconds, width, height, work / f"clip_{i:03d}.mp4"))
        timeline.append((scene.narration, seconds, scene.on_screen_text))
        log(f"  scene {i + 1}/{len(vs.scenes)}: {seconds:.1f}s")

    # 4. Assemble
    voice_track = assemble.concat(voice_parts, work / "voice.mp3", audio=True)
    silent_video = assemble.concat(clip_parts, work / "video.mp4", audio=False)
    subs = captions.build_ass(cfg, timeline, width, height, work / "captions.ass")
    music = assemble.pick_music(cfg)
    if music is None:
        log("  no music in assets/music, rendering voice only")
    final = assemble.final_render(cfg, silent_video, voice_track, subs, folder / "video.mp4", music)
    thumb = assemble.thumbnail(silent_video, vs.thumbnail_text, cfg, folder / "thumbnail.jpg", width, height)

    (folder / "metadata.json").write_text(
        json.dumps(
            {"title": vs.title, "description": vs.description, "tags": vs.tags, "format": fmt,
             "language": cfg.language, "topic": topic, "duration": sum(t[1] for t in timeline)},
            ensure_ascii=False, indent=2,
        ),
        encoding="utf-8",
    )
    log(f"Done: {final}")
    return Result(folder=folder, video=final, thumbnail=thumb, script=vs)


def publish(cfg: ChannelConfig, result: Result, publish_at: datetime | None, fmt: str, log=print) -> Result:
    from . import upload

    log(f"Uploading to YouTube{f' scheduled for {publish_at:%Y-%m-%d %H:%M %Z}' if publish_at else ''}")
    result.video_id = upload.upload(
        cfg,
        result.video,
        result.script.title,
        result.script.description,
        result.script.tags,
        publish_at=publish_at,
        thumbnail=result.thumbnail,
        is_short=fmt == "short",
    )
    result.publish_at = publish_at
    meta_path = result.folder / "metadata.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    meta.update(video_id=result.video_id, publish_at=publish_at.isoformat() if publish_at else None)
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    log(f"Uploaded: https://youtu.be/{result.video_id}")
    return result


def scheduled_times(cfg: ChannelConfig) -> list[datetime]:
    """Publish times already used by earlier uploads in the output folder."""
    taken = []
    for meta in cfg.output_path.glob("*/metadata.json"):
        value = json.loads(meta.read_text(encoding="utf-8")).get("publish_at")
        if value:
            taken.append(datetime.fromisoformat(value))
    return taken
