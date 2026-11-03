"""Command line: python -m facepipe --channel <name> <command> ...

Typical week for one channel:
  ideas --save          20 topic ideas appended to topics/<channel>.txt
  batch --limit 7       scripts for the next 7 topics, saved as drafts
  drafts                list drafts; edit each script.json, check facts, set "reviewed": true
  render --reviewed --upload --schedule
                        render every reviewed draft and schedule it into the next free slots
  stats                 last 28 days against the channel's monthly target
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

from .config import ROOT, list_channels, load_config


def _topics_file(cfg) -> Path:
    path = ROOT / "topics" / f"{cfg.slug}.txt"
    path.parent.mkdir(exist_ok=True)
    return path


def _schedule(cfg, args):
    from .pipeline import scheduled_times
    from .upload import next_slot

    if getattr(args, "publish_at", None):
        return datetime.fromisoformat(args.publish_at).replace(tzinfo=ZoneInfo(cfg.timezone))
    if getattr(args, "schedule", False):
        return next_slot(cfg, scheduled_times(cfg))
    return None


def cmd_channels(cfg, args):
    for slug in list_channels():
        c = load_config(slug)
        print(f"{slug:20} {c.language}  {c.voice_provider:10}  target Rs {c.monthly_target_inr:,}/month  {c.name}")


def cmd_ideas(cfg, args):
    from .script import generate_ideas

    path = _topics_file(cfg)
    existing = [t for t in path.read_text(encoding="utf-8").splitlines() if t.strip()] if path.exists() else []
    ideas = generate_ideas(cfg, args.count, avoid=existing)
    print("\n".join(ideas))
    if args.save:
        with open(path, "a", encoding="utf-8") as f:
            f.write("\n".join(ideas) + "\n")
        print(f"\nAppended {len(ideas)} topics to {path}")


def cmd_script(cfg, args):
    from .pipeline import draft_script

    draft_script(cfg, args.topic, args.format)


def cmd_make(cfg, args):
    from .pipeline import draft_script, make_offline, publish, render

    if args.offline:
        make_offline(cfg, args.format)
        return
    if not args.topic:
        sys.exit("Give a topic, or --offline for a dry run.")
    path = draft_script(cfg, args.topic, args.format)
    if not args.no_review:
        return
    result = render(cfg, path, args.format, require_review=False)
    if args.upload:
        publish(cfg, result, _schedule(cfg, args))


def cmd_batch(cfg, args):
    from .pipeline import draft_script

    path = Path(args.topics) if args.topics else _topics_file(cfg)
    if not path.exists():
        sys.exit(f"No topics file at {path}. Run: python -m facepipe --channel {cfg.slug} ideas --save")
    topics = [t.strip() for t in path.read_text(encoding="utf-8").splitlines() if t.strip()]
    done_file = path.with_suffix(".done.txt")
    done = set(done_file.read_text(encoding="utf-8").splitlines()) if done_file.exists() else set()
    todo = [t for t in topics if t not in done][: args.limit]
    print(f"{len(todo)} topics to script ({len(done)} already done)")
    failed = 0
    for i, topic in enumerate(todo, 1):
        print(f"\n[{i}/{len(todo)}]")
        try:
            draft_script(cfg, topic, args.format)
        except Exception as exc:  # keep the batch going; report at the end
            failed += 1
            print(f"  FAILED: {exc}", file=sys.stderr)
            continue
        with open(done_file, "a", encoding="utf-8") as f:
            f.write(topic + "\n")
    if failed:
        sys.exit(f"{failed} topic(s) failed")


def cmd_drafts(cfg, args):
    from .pipeline import drafts
    from .script import load_script

    paths = drafts(cfg)
    if not paths:
        print("No unrendered drafts.")
    for path in paths:
        vs = load_script(path)
        state = "reviewed" if vs.reviewed else "NEEDS REVIEW"
        print(f"{state:13} {path.relative_to(ROOT)}  {vs.title}  ({len(vs.facts_to_check)} facts to check)")


def cmd_render(cfg, args):
    from .pipeline import NotReviewed, drafts, publish, render

    paths = [Path(p) for p in args.scripts]
    if args.reviewed:
        paths += drafts(cfg, reviewed=True)
    if not paths:
        sys.exit("Nothing to render. Pass script.json paths or --reviewed.")
    failed = 0
    for path in paths:
        try:
            result = render(cfg, path, require_review=not args.no_review)
            if args.upload:
                publish(cfg, result, _schedule(cfg, args))
        except NotReviewed as exc:
            failed += 1
            print(str(exc), file=sys.stderr)
        except Exception as exc:
            failed += 1
            print(f"FAILED {path}: {exc}", file=sys.stderr)
    if failed:
        sys.exit(f"{failed} of {len(paths)} failed")


def cmd_upload(cfg, args):
    from .pipeline import load_result, publish

    publish(cfg, load_result(Path(args.folder)), _schedule(cfg, args))


def cmd_auth(cfg, args):
    from .upload import credentials

    credentials(cfg)
    print(f"YouTube authorised for {cfg.slug}; token saved in tokens/{cfg.slug}.json")


def cmd_stats(cfg, args):
    from .stats import last_28_days, report

    slugs = list_channels() if args.all else [cfg.slug]
    for slug in slugs:
        c = load_config(slug)
        print(report(c, last_28_days(c)))
        print()


def main(argv=None):
    load_dotenv(ROOT / ".env")
    p = argparse.ArgumentParser(prog="facepipe", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--channel", help=f"Channel config name: {', '.join(list_channels())}")
    p.add_argument("--language", choices=["en", "ta", "hi"], help="Override the channel language")
    sub = p.add_subparsers(dest="command", required=True)

    def add_publish(sp):
        sp.add_argument("--upload", action="store_true", help="Upload to YouTube when rendered")
        sp.add_argument("--schedule", action="store_true", help="Schedule into the next free publish slot")
        sp.add_argument("--publish-at", help="Exact local publish time, e.g. 2026-11-05T18:30")

    sub.add_parser("channels", help="List channel configs").set_defaults(func=cmd_channels)

    s = sub.add_parser("ideas", help="Generate topic ideas with Claude")
    s.add_argument("--count", type=int, default=20)
    s.add_argument("--save", action="store_true", help="Append to topics/<channel>.txt")
    s.set_defaults(func=cmd_ideas)

    s = sub.add_parser("script", help="Write one script for review")
    s.add_argument("topic")
    s.add_argument("--format", choices=["short", "long"], default="long")
    s.set_defaults(func=cmd_script)

    s = sub.add_parser("batch", help="Write scripts for the next topics in topics/<channel>.txt")
    s.add_argument("topics", nargs="?", help="Topics file (default topics/<channel>.txt)")
    s.add_argument("--format", choices=["short", "long"], default="long")
    s.add_argument("--limit", type=int, default=7)
    s.set_defaults(func=cmd_batch)

    sub.add_parser("drafts", help="List scripts waiting for review or render").set_defaults(func=cmd_drafts)

    s = sub.add_parser("render", help="Render reviewed scripts into videos")
    s.add_argument("scripts", nargs="*", help="script.json paths")
    s.add_argument("--reviewed", action="store_true", help="Render every reviewed, unrendered draft")
    s.add_argument("--no-review", action="store_true", help="Skip the reviewed check (not recommended)")
    add_publish(s)
    s.set_defaults(func=cmd_render)

    s = sub.add_parser("make", help="Script and stop for review; or render straight away with --no-review")
    s.add_argument("topic", nargs="?")
    s.add_argument("--format", choices=["short", "long"], default="short")
    s.add_argument("--offline", action="store_true", help="Dry run: sample script, silent voice, colour frames")
    s.add_argument("--no-review", action="store_true", help="Render without stopping for review")
    add_publish(s)
    s.set_defaults(func=cmd_make)

    s = sub.add_parser("upload", help="Upload an already-rendered output folder")
    s.add_argument("folder")
    add_publish(s)
    s.set_defaults(func=cmd_upload)

    sub.add_parser("auth", help="One-time YouTube sign-in for this channel").set_defaults(func=cmd_auth)

    s = sub.add_parser("stats", help="Last 28 days against the monthly target")
    s.add_argument("--all", action="store_true", help="All channels")
    s.set_defaults(func=cmd_stats)

    args = p.parse_args(argv)
    needs_channel = args.command not in {"channels"} and not (args.command == "stats" and args.all)
    cfg = load_config(args.channel, language=args.language) if needs_channel else None
    args.func(cfg, args)


if __name__ == "__main__":
    main()
