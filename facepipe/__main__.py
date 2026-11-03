"""Command line: python -m facepipe <command> ..."""

from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

from .config import ROOT, load_config


def _cfg(args):
    return load_config(args.config, language=getattr(args, "language", None))


def cmd_ideas(args):
    from .script import generate_ideas

    cfg = _cfg(args)
    topics_file = ROOT / "topics.txt"
    existing = topics_file.read_text(encoding="utf-8").splitlines() if topics_file.exists() else []
    ideas = generate_ideas(cfg, args.count, avoid=[t for t in existing if t.strip()])
    for idea in ideas:
        print(idea)
    if args.save:
        with open(topics_file, "a", encoding="utf-8") as f:
            f.write("\n".join(ideas) + "\n")
        print(f"\nAppended {len(ideas)} topics to {topics_file}")


def _schedule(cfg, args):
    from .pipeline import scheduled_times
    from .upload import next_slot

    if args.publish_at:
        return datetime.fromisoformat(args.publish_at).replace(tzinfo=ZoneInfo(cfg.timezone))
    if args.schedule:
        return next_slot(cfg, scheduled_times(cfg))
    return None


def cmd_make(args):
    from .pipeline import make_video, publish

    cfg = _cfg(args)
    result = make_video(cfg, args.topic, args.format, offline=args.offline,
                        script_path=Path(args.script) if args.script else None)
    if args.upload:
        publish(cfg, result, _schedule(cfg, args), args.format)


def cmd_batch(args):
    from .pipeline import make_video, publish

    cfg = _cfg(args)
    path = Path(args.topics)
    topics = [t.strip() for t in path.read_text(encoding="utf-8").splitlines() if t.strip()]
    done_file = path.with_suffix(".done.txt")
    done = set(done_file.read_text(encoding="utf-8").splitlines()) if done_file.exists() else set()
    todo = [t for t in topics if t not in done][: args.limit]
    print(f"{len(todo)} topics to make ({len(done)} already done)")
    for i, topic in enumerate(todo, 1):
        print(f"\n[{i}/{len(todo)}] {topic}")
        try:
            result = make_video(cfg, topic, args.format)
            if args.upload:
                publish(cfg, result, _schedule(cfg, args), args.format)
        except Exception as exc:  # keep the batch going; report at the end
            print(f"  FAILED: {exc}", file=sys.stderr)
            continue
        with open(done_file, "a", encoding="utf-8") as f:
            f.write(topic + "\n")


def cmd_upload(args):
    import json

    from .pipeline import Result, publish
    from .script import load_script

    cfg = _cfg(args)
    folder = Path(args.folder)
    meta = json.loads((folder / "metadata.json").read_text(encoding="utf-8"))
    result = Result(folder=folder, video=folder / "video.mp4", thumbnail=folder / "thumbnail.jpg",
                    script=load_script(folder / "script.json"))
    publish(cfg, result, _schedule(cfg, args), meta.get("format", "short"))


def cmd_auth(args):
    from .upload import credentials

    credentials()
    print("YouTube authorised; token saved.")


def main(argv=None):
    load_dotenv(ROOT / ".env")
    p = argparse.ArgumentParser(prog="facepipe", description="Faceless YouTube video pipeline")
    p.add_argument("--config", help="Path to channel YAML (default config/channel.yaml)")
    sub = p.add_subparsers(dest="command", required=True)

    def add_lang(sp):
        sp.add_argument("--language", choices=["en", "ta", "hi"], help="Override the config language")

    def add_publish(sp):
        sp.add_argument("--upload", action="store_true", help="Upload to YouTube when done")
        sp.add_argument("--schedule", action="store_true", help="Schedule into the next free publish slot")
        sp.add_argument("--publish-at", help="Exact local publish time, e.g. 2026-11-05T18:30")

    s = sub.add_parser("ideas", help="Generate topic ideas with Claude")
    s.add_argument("--count", type=int, default=20)
    s.add_argument("--save", action="store_true", help="Append to topics.txt")
    add_lang(s)
    s.set_defaults(func=cmd_ideas)

    s = sub.add_parser("make", help="Make one video")
    s.add_argument("topic", nargs="?")
    s.add_argument("--format", choices=["short", "long"], default="short")
    s.add_argument("--script", help="Reuse an existing script.json instead of calling Claude")
    s.add_argument("--offline", action="store_true", help="Dry run: sample script, silent voice, colour frames")
    add_lang(s)
    add_publish(s)
    s.set_defaults(func=cmd_make)

    s = sub.add_parser("batch", help="Make videos for every topic in a file")
    s.add_argument("topics", nargs="?", default=str(ROOT / "topics.txt"))
    s.add_argument("--format", choices=["short", "long"], default="short")
    s.add_argument("--limit", type=int, default=5)
    add_lang(s)
    add_publish(s)
    s.set_defaults(func=cmd_batch)

    s = sub.add_parser("upload", help="Upload an already-rendered output folder")
    s.add_argument("folder")
    add_publish(s)
    s.set_defaults(func=cmd_upload)

    s = sub.add_parser("auth", help="One-time YouTube sign-in")
    s.set_defaults(func=cmd_auth)

    args = p.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
