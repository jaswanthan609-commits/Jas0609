"""End-to-end: topic -> script (you review it) -> voice -> visuals -> captions -> video -> upload."""

from __future__ import annotations

import json
import re
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from . import affiliate, assemble, captions, script as scriptmod, visuals, voice
from .config import FORMATS, ChannelConfig
from .media import require_ffmpeg

SAMPLE_SCRIPT = Path(__file__).parent / "sample_script.json"


class NotReviewed(RuntimeError):
    pass


class Rejected(RuntimeError):
    """The critic or the duplicate check stopped a script before it reached review."""


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


def _new_folder(cfg: ChannelConfig, fmt: str, name: str) -> Path:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    folder = cfg.output_path / f"{stamp}-{fmt}-{_slug(name)}"
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def draft_script(cfg: ChannelConfig, topic: str, fmt: str = "short", log=print, use_critic: bool = True) -> Path:
    """Step 1: Claude writes the script into a new folder. Returns the script.json path for review.

    With use_critic, a near-duplicate title or a weak script is rewritten once, then dropped
    (raises Rejected) rather than sent for approval.
    """
    from . import critic

    if fmt == "ambience":  # no narration: a scene and music spec instead of a script
        from . import ambience

        previous = critic.previous_titles(cfg)
        folder = _new_folder(cfg, fmt, topic)
        seed = int(datetime.now().strftime("%Y%m%d%H%M%S")) % 1_000_003
        spec = ambience.draft(cfg, topic, folder, seed)
        dup = critic.duplicate_of(spec.title, previous)
        if dup:
            spec = ambience.draft(cfg, topic, folder, seed, notes=f"Too close to our earlier \"{dup}\"; pick a clearly different scene and title.")
        (folder / "topic.txt").write_text(f"{fmt}\n{topic}\n", encoding="utf-8")
        log(f"  Title: {spec.title}")
        return folder / "script.json"

    log(f"[{cfg.slug}] Writing {fmt} script with {cfg.claude_model}: {topic}")
    vs = scriptmod.write_script(cfg, topic, fmt)
    review = None
    if use_critic:
        previous = critic.previous_titles(cfg)
        for attempt in (1, 2):
            dup = critic.duplicate_of(vs.title, previous)
            problems = [] if dup else critic.lint(vs, fmt)
            if dup:
                notes = f"The title is too close to an earlier video, \"{dup}\". Take a clearly different angle."
            elif problems:
                log("  lint: " + " | ".join(problems))
                notes = "An editor rejected the first draft. Fix all of these:\n- " + "\n- ".join(problems)
                if attempt == 2:  # rule problems after a rewrite: keep it, the reviewer sees them in the PR
                    review = critic.critique(cfg, vs, fmt)
                    break
            else:
                review = critic.critique(cfg, vs, fmt)
                log(f"  critic: hook {review.hook}, specific {review.specificity}, original {review.originality}, "
                    f"policy {review.policy_risk}")
                if review.score >= critic.PASS_SCORE:
                    break
                notes = critic.notes_for_rewrite(review)
            if attempt == 2:
                raise Rejected(f"dropped after rewrite: {dup and 'duplicate of ' + dup or (review.fixes if review else problems)}")
            log("  rewriting with the critic's notes")
            vs = scriptmod.write_script(cfg, topic, fmt, notes=notes)
    folder = _new_folder(cfg, fmt, topic)
    path = folder / "script.json"
    scriptmod.save_script(vs, path)
    (folder / "topic.txt").write_text(f"{fmt}\n{topic}\n", encoding="utf-8")
    if review:
        (folder / "critic.json").write_text(review.model_dump_json(indent=2), encoding="utf-8")
    log(f"  Title: {vs.title}  ({len(vs.scenes)} scenes)")
    log(f"  Facts to check: {len(vs.facts_to_check)}")
    log(f"  Review it, set \"reviewed\": true, then: python -m facepipe --channel {cfg.slug} render {path}")
    return path


def _stamp(seconds: float) -> str:
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def with_chapters(description: str, scenes, timeline) -> str:
    """YouTube chapters (first at 0:00, at least 3, each 10 s+) from the scenes' chapter titles."""
    marks, t = [], 0.0
    for scene, (_, seconds, _) in zip(scenes, timeline):
        if scene.chapter and (not marks or t - marks[-1][0] >= 10):
            marks.append((0.0 if not marks else t, scene.chapter))
        t += seconds
    if len(marks) < 3:
        return description
    return description + "\n\nChapters\n" + "\n".join(f"{_stamp(t)} {title}" for t, title in marks)


def render(
    cfg: ChannelConfig,
    script_path: Path,
    fmt: str | None = None,
    offline: bool = False,
    require_review: bool = True,
    log=print,
) -> Result:
    """Step 2: turn a (reviewed) script.json into video.mp4 + thumbnail.jpg in the same folder."""
    require_ffmpeg()
    vs = scriptmod.load_script(script_path)
    if require_review and not vs.reviewed:
        raise NotReviewed(
            f"{script_path} is not marked reviewed. Read it, check facts_to_check, "
            'then set "reviewed": true (or pass --no-review).'
        )
    folder = script_path.parent
    topic_file = folder / "topic.txt"
    if fmt is None:
        fmt = topic_file.read_text(encoding="utf-8").split("\n")[0] if topic_file.exists() else "short"
    width, height, _ = FORMATS[fmt]
    if fmt == "ambience":
        return _render_ambience(cfg, folder, vs, offline, log)
    work = folder / "work"
    if work.exists():
        shutil.rmtree(work)
    work.mkdir()
    log(f"[{cfg.slug}] Rendering {fmt}: {vs.title}")

    used: set = set()
    voice_parts, clip_parts, timeline = [], [], []
    for i, scene in enumerate(vs.scenes):
        audio = work / f"voice_{i:03d}.mp3"
        if offline:
            seconds = voice.synthesize_placeholder(scene.narration, audio)
        else:
            seconds = voice.synthesize(cfg, scene.narration, audio)
        voice_parts.append(audio)

        stem = work / f"visual_{i:03d}"
        if offline:
            visual = None
        elif cfg.visual_mode == "ai_images":
            visual = visuals.ai_image(cfg, scene.image_prompt or scene.visual_query, width, height, stem)
        elif cfg.visual_mode == "public_art":
            visual = visuals.public_art(cfg, scene.visual_query, width, height, stem, used)
        else:
            visual = visuals.fetch(cfg, scene.visual_query, width, height, stem, used)
        if visual is None:
            if not offline:
                log(f"  no footage for '{scene.visual_query}', using placeholder; fix before publishing")
            visual = visuals.placeholder(i, width, height, stem)
        clip_parts.append(assemble.scene_clip(visual, seconds, width, height, work / f"clip_{i:03d}.mp4",
                                              fade=cfg.dissolve))
        timeline.append((scene.narration, seconds, scene.on_screen_text))
        log(f"  scene {i + 1}/{len(vs.scenes)}: {seconds:.1f}s  {visual.name}")

    voice_track = assemble.concat(voice_parts, work / "voice.mp3", audio=True)
    silent_video = assemble.concat(clip_parts, work / "video.mp4", audio=False)
    if cfg.burn_captions:
        subs = captions.build_ass(cfg, timeline, width, height, work / "captions.ass")
    else:  # no words on the picture; YouTube shows the uploaded captions.srt if the viewer wants them
        subs = None
        captions.build_srt(timeline, folder / "captions.srt")
    music = assemble.pick_music(cfg)
    if music is None:
        log("  no music in assets/music, rendering voice only")
    final = assemble.final_render(cfg, silent_video, voice_track, subs, folder / "video.mp4", music)
    thumb = assemble.thumbnail(silent_video, vs.thumbnail_text, cfg, folder / "thumbnail.jpg", width, height)
    from . import listen

    if not offline and listen.listen(final):
        log("  listened: audio_report.json written")

    meta_path = folder / "metadata.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}
    spoken = " ".join([vs.title, *(scene.narration for scene in vs.scenes)])
    description = affiliate.with_links(cfg, with_chapters(vs.description, vs.scenes, timeline), spoken)
    meta.update(
        channel=cfg.slug, title=vs.title, description=description, tags=vs.tags, format=fmt,
        language=cfg.language, duration=round(sum(t[1] for t in timeline), 1),
        rendered_at=datetime.now().isoformat(timespec="seconds"), offline=offline,
    )
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    log(f"  Done: {final}")
    return Result(folder=folder, video=final, thumbnail=thumb, script=vs)


def _render_ambience(cfg: ChannelConfig, folder: Path, vs, offline: bool, log) -> Result:
    from . import ambience

    video, thumb = ambience.render(cfg, folder, seconds=60 if offline else None, log=log)
    from . import listen

    if listen.listen(video):
        log("  listened: audio_report.json written")
    meta_path = folder / "metadata.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}
    description = affiliate.with_links(cfg, vs.description, vs.title)
    meta.update(channel=cfg.slug, title=vs.title, description=description, tags=vs.tags, format="ambience",
                language=cfg.language, duration=FORMATS["ambience"][2],
                rendered_at=datetime.now().isoformat(timespec="seconds"), offline=offline)
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    log(f"  Done: {video}")
    return Result(folder=folder, video=video, thumbnail=thumb, script=vs)


def make_offline(cfg: ChannelConfig, fmt: str = "short", log=print) -> Result:
    """Dry run with the bundled sample script, silent voice and colour frames. Needs only ffmpeg."""
    folder = _new_folder(cfg, fmt, "offline-sample")
    path = folder / "script.json"
    shutil.copy(SAMPLE_SCRIPT, path)
    return render(cfg, path, fmt, offline=True, require_review=False, log=log)


def publish(cfg: ChannelConfig, result: Result, publish_at: datetime | None, log=print) -> Result:
    from . import upload

    meta_path = result.folder / "metadata.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    if meta.get("offline"):
        raise RuntimeError("This is an offline dry-run render; it can't be uploaded.")
    when = f" scheduled for {publish_at:%Y-%m-%d %H:%M %Z}" if publish_at else ""
    log(f"[{cfg.slug}] Uploading to YouTube{when}")
    result.video_id = upload.upload(
        cfg,
        result.video,
        result.script.title,
        meta.get("description") or result.script.description,
        result.script.tags,
        publish_at=publish_at,
        thumbnail=result.thumbnail,
        is_short=meta.get("format") == "short",
    )
    result.publish_at = publish_at
    meta.update(video_id=result.video_id, publish_at=publish_at.isoformat() if publish_at else None)
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    log(f"  Uploaded: https://youtu.be/{result.video_id}")
    return result


def load_result(folder: Path) -> Result:
    return Result(
        folder=folder,
        video=folder / "video.mp4",
        thumbnail=folder / "thumbnail.jpg",
        script=scriptmod.load_script(folder / "script.json"),
    )


def scheduled_times(cfg: ChannelConfig) -> list[datetime]:
    """Publish times already used by earlier uploads of this channel."""
    taken = []
    for meta in cfg.output_path.glob("*/metadata.json"):
        value = json.loads(meta.read_text(encoding="utf-8")).get("publish_at")
        if value:
            taken.append(datetime.fromisoformat(value))
    return taken


def drafts(cfg: ChannelConfig, reviewed: bool | None = None) -> list[Path]:
    """Script folders that have not been rendered yet, optionally filtered by review state."""
    out = []
    for path in sorted(cfg.output_path.glob("*/script.json")):
        if (path.parent / "video.mp4").exists():
            continue
        if reviewed is not None and scriptmod.load_script(path).reviewed != reviewed:
            continue
        out.append(path)
    return out
