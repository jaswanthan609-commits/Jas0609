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

from .config import FORMATS, ROOT, list_channels, load_config


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


def _remaining_topics(cfg) -> list[str]:
    path = _topics_file(cfg)
    topics = [t.strip() for t in path.read_text(encoding="utf-8").splitlines() if t.strip()] if path.exists() else []
    done_file = path.with_suffix(".done.txt")
    done = set(done_file.read_text(encoding="utf-8").splitlines()) if done_file.exists() else set()
    return [t for t in topics if t not in done]


def cmd_daily(cfg, args):
    """Unattended daily run (GitHub Actions): top up topic ideas, then draft today's scripts."""
    from .pipeline import draft_script
    from .script import generate_ideas

    path = _topics_file(cfg)
    need = args.long + args.short
    if len(_remaining_topics(cfg)) < need * 3:
        from .breakout import inspiration_text, load_outliers

        existing = [t for t in path.read_text(encoding="utf-8").splitlines() if t.strip()] if path.exists() else []
        ideas = generate_ideas(cfg, 20, avoid=existing, inspiration=inspiration_text(load_outliers(cfg)))
        with open(path, "a", encoding="utf-8") as f:
            f.write("\n".join(ideas) + "\n")
        print(f"[{cfg.slug}] added {len(ideas)} topic ideas")
    from .pipeline import Rejected

    todo = _remaining_topics(cfg)[:need]
    done_file = path.with_suffix(".done.txt")
    for i, topic in enumerate(todo):
        fmt = cfg.long_format if i < args.long else "short"
        try:
            draft_script(cfg, topic, fmt)
        except Rejected as exc:  # the topic is used up either way; tomorrow brings a new one
            print(f"[{cfg.slug}] REJECTED {topic}: {exc}")
        with open(done_file, "a", encoding="utf-8") as f:
            f.write(topic + "\n")


def cmd_breakout(cfg, args):
    """Refresh breakout research (weekly) and queue follow-ups for our own winners (daily)."""
    import os

    from . import breakout, budget
    from .script import follow_up_topics

    if not os.environ.get("YOUTUBE_API_KEY"):
        print("breakout: no YOUTUBE_API_KEY, skipped")
        return
    # Only research channels the autopilot runs: each search spends YouTube API quota.
    slugs = budget.active_channels() if args.all else [cfg.slug]
    for slug in slugs:
        c = load_config(slug)
        try:
            if args.force or breakout.outliers_stale(c):
                found = breakout.find_outliers(c)
                breakout.save_outliers(c, found)
                top = found[0] if found else None
                print(f"[{slug}] {len(found)} outliers saved" + (f"; top: {top['title']} ({top['score']}x)" if top else ""))
            for w in breakout.find_winners(c):
                topics = follow_up_topics(c, w["title"], w["views"], w["median"])
                breakout.push_topics_first(_topics_file(c), topics)
                breakout.mark_followed_up(w)
                print(f"[{slug}] WINNER {w['title']}: {w['views']:,} views ({w['views'] / max(w['median'], 1):.0f}x median); "
                      f"queued {len(topics)} follow-ups")
        except Exception as exc:  # research must never block the day's drafts
            print(f"[{slug}] breakout failed: {exc}", file=sys.stderr)


def cmd_scan(cfg, args):
    """Weekly cross-niche outlier scan -> research/scan.json (which areas small channels are winning)."""
    import os

    from . import scan

    if not os.environ.get("YOUTUBE_API_KEY"):
        print("scan: no YOUTUBE_API_KEY, skipped")
        return
    if not args.force and not scan.stale():
        print("scan: this week's scan is saved; --force to rerun")
        return
    try:
        result = scan.scan(days=args.days)
    except Exception as exc:  # research must never block the day's drafts
        print(f"scan failed: {exc}", file=sys.stderr)
        return
    scan.save(result)
    from . import hooks

    print(f"hooks: {hooks.refresh(result['outliers'])} new breakout openings saved")
    text = scan.report(result)
    print(text)
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as f:
            f.write("```\n" + text + "\n```\n")


def cmd_autopilot(cfg, args):
    """Unattended daily run: decide what today's budget allows, then draft it."""
    import os

    from . import budget

    ap = budget.load()
    today = budget.plan(ap)
    lines = ["Budget:"] + [f"  {n}" for n in today.notes]
    lines.append("Today: " + (", ".join(f"{s} ({l} long, {sh} short)" for s, l, sh in today.jobs) or "nothing"))
    print("\n".join(lines))
    failed = 0
    if not args.dry_run:
        for slug, n_long, n_short in today.jobs:
            c = load_config(slug)
            try:
                cmd_daily(c, argparse.Namespace(long=n_long, short=n_short))
            except Exception as exc:  # one channel failing shouldn't stop the others
                failed += 1
                print(f"FAILED {slug}: {exc}", file=sys.stderr)
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as f:
            f.write("```\n" + "\n".join(lines) + "\n```\n")
    if failed:
        sys.exit(f"{failed} channel(s) failed")


def cmd_budget(cfg, args):
    from . import budget

    ap = budget.load()
    by_channel: dict[str, float] = {}
    for e in budget.spend_entries():
        by_channel[e["channel"]] = by_channel.get(e["channel"], 0) + e["usd"]
    print(f"Started {ap.started}: ${ap.starting_budget_usd:.2f}")
    print(f"Spent ${budget.spent():.2f}: " + ", ".join(f"{k} ${v:.2f}" for k, v in sorted(by_channel.items())))
    earned = budget.earned_inr()
    print(f"Earned Rs {sum(earned.values()):,.0f} (${budget.earned_usd(ap):.2f}): "
          + ", ".join(f"{k} Rs {v:,.0f}" for k, v in sorted(earned.items())))
    print(f"Available ${budget.available(ap):.2f}")
    for note in budget.plan(ap).notes:
        print(f"  {note}")


def cmd_publish_approved(cfg, args):
    """Render and upload every script that reached main (merging the drafts PR = approval)."""
    import json

    from .pipeline import publish, render

    slugs = list_channels() if args.all else [cfg.slug]
    failed = 0
    for slug in slugs:
        c = load_config(slug)
        for path in sorted(c.output_path.glob("*/script.json")):
            meta_path = path.parent / "metadata.json"
            meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}
            if meta.get("video_id") or (meta.get("rendered_at") and not args.upload):
                continue
            try:
                result = render(c, path, require_review=False)
                if args.upload:
                    publish(c, result, _schedule(c, args))
            except Exception as exc:  # keep going; the summary shows what failed
                failed += 1
                print(f"FAILED {path}: {exc}", file=sys.stderr)
    if failed:
        sys.exit(f"{failed} video(s) failed")


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
        if not (ROOT / "tokens" / f"{slug}.json").exists() and args.all:
            print(f"{slug}: no YouTube token yet, skipped\n")
            continue
        print(report(c, last_28_days(c)))
        if args.save_revenue:
            from . import budget
            from .stats import revenue_since

            since = budget.load().started
            inr, until = revenue_since(c, since)
            budget.save_revenue(slug, inr, since.isoformat(), until)
            print(f"  earned since {since}: Rs {inr:,.0f} (saved for the budget)")
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
    s.add_argument("--format", choices=list(FORMATS), default="long")
    s.set_defaults(func=cmd_script)

    s = sub.add_parser("batch", help="Write scripts for the next topics in topics/<channel>.txt")
    s.add_argument("topics", nargs="?", help="Topics file (default topics/<channel>.txt)")
    s.add_argument("--format", choices=list(FORMATS), default="long")
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
    s.add_argument("--format", choices=list(FORMATS), default="short")
    s.add_argument("--offline", action="store_true", help="Dry run: sample script, silent voice, colour frames")
    s.add_argument("--no-review", action="store_true", help="Render without stopping for review")
    add_publish(s)
    s.set_defaults(func=cmd_make)

    s = sub.add_parser("daily", help="Unattended: top up ideas and draft today's scripts")
    s.add_argument("--long", type=int, default=1, help="Long-form scripts to draft")
    s.add_argument("--short", type=int, default=1, help="Shorts scripts to draft")
    s.set_defaults(func=cmd_daily)

    s = sub.add_parser("breakout", help="Find breakout videos in the niche and follow up our own winners")
    s.add_argument("--all", action="store_true", help="All channels")
    s.add_argument("--force", action="store_true", help="Refresh outliers even if this week's are saved")
    s.set_defaults(func=cmd_breakout)

    s = sub.add_parser("scan", help="Weekly: rank which areas small and new channels are breaking out in")
    s.add_argument("--force", action="store_true", help="Rerun even if this week's scan is saved")
    s.add_argument("--days", type=int, help="Look back this many days (default from config/scan.yaml)")
    s.set_defaults(func=cmd_scan)

    s = sub.add_parser("autopilot", help="Unattended: draft whatever today's budget allows, across all channels")
    s.add_argument("--dry-run", action="store_true", help="Show the plan without drafting")
    s.set_defaults(func=cmd_autopilot)

    sub.add_parser("budget", help="Money spent, earned and left").set_defaults(func=cmd_budget)

    s = sub.add_parser("publish-approved", help="Render (and upload) every approved, unpublished script")
    s.add_argument("--all", action="store_true", help="All channels")
    add_publish(s)
    s.set_defaults(func=cmd_publish_approved)

    s = sub.add_parser("upload", help="Upload an already-rendered output folder")
    s.add_argument("folder")
    add_publish(s)
    s.set_defaults(func=cmd_upload)

    sub.add_parser("auth", help="One-time YouTube sign-in for this channel").set_defaults(func=cmd_auth)

    s = sub.add_parser("stats", help="Last 28 days against the monthly target")
    s.add_argument("--all", action="store_true", help="All channels")
    s.add_argument("--save-revenue", action="store_true", help="Save earnings since the autopilot start for the budget")
    s.set_defaults(func=cmd_stats)

    args = p.parse_args(argv)
    needs_channel = args.command not in {"channels", "autopilot", "budget", "scan"} and not (
        args.command in {"stats", "publish-approved", "breakout"} and args.all
    )
    cfg = load_config(args.channel, language=args.language) if needs_channel else None
    args.func(cfg, args)


if __name__ == "__main__":
    main()
