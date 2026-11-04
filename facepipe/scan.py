"""Niche-agnostic outlier scan: what is breaking records on YouTube right now, for small channels.

Breakout research (breakout.py) only looks inside a channel's own niche. This scan looks across many
seed searches (config/scan.yaml) once a week and ranks whole areas by how many young or small
channels got a breakout video there. That is how the line-up was picked (2026-11-04), and the weekly
rerun keeps it honest: if an area cools down or a new one appears, research/scan.json shows it.

An outlier is a video with >= MIN_VIEWS views, >= MIN_RATIO x views per subscriber, from a channel with
fewer than MAX_SUBS subscribers. "Young" means the channel was created within YOUNG_DAYS days.
Cost: 100 quota units per seed (search) + ~1 per 50 videos/channels. 40 seeds ~ 4,100 of 10,000 a day.
"""

from __future__ import annotations

import json
import re
from collections import defaultdict
from datetime import datetime, timedelta, timezone

import yaml

from .breakout import RESEARCH_DIR, _chunks, _get
from .config import ROOT

SCAN_CONFIG = ROOT / "config" / "scan.yaml"
SCAN_FILE = RESEARCH_DIR / "scan.json"
MIN_VIEWS = 100_000
MIN_RATIO = 5.0
MAX_SUBS = 100_000
YOUNG_DAYS = 365


def _seconds(iso: str) -> int:
    m = re.match(r"P(?:(\d+)D)?T?(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", iso or "PT0S")
    d, h, mi, s = (int(x or 0) for x in m.groups())
    return d * 86400 + h * 3600 + mi * 60 + s


def load_seeds() -> dict:
    return yaml.safe_load(SCAN_CONFIG.read_text(encoding="utf-8")) or {}


def scan(days: int | None = None, seeds: list[str] | None = None) -> dict:
    conf = load_seeds()
    days = days or conf.get("days", 90)
    seeds = seeds or conf.get("seeds", [])
    after = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")
    rows: dict[str, dict] = {}
    for q in seeds:
        try:
            data = _get("search", part="id", q=q, type="video", order="viewCount", publishedAfter=after,
                        relevanceLanguage=conf.get("language", "en"), maxResults=50)
        except Exception as exc:  # quota or network: keep what we have
            print(f"scan: search '{q}' failed: {exc}")
            break
        for it in data.get("items", []):
            vid = it.get("id", {}).get("videoId")
            if vid and vid not in rows:
                rows[vid] = {"id": vid, "seed": q}
    for chunk in _chunks(list(rows)):
        for v in _get("videos", part="snippet,statistics,contentDetails", id=",".join(chunk)).get("items", []):
            rows[v["id"]].update(
                title=v["snippet"]["title"], channel=v["snippet"].get("channelTitle", ""),
                channel_id=v["snippet"]["channelId"], published=v["snippet"]["publishedAt"][:10],
                views=int(v["statistics"].get("viewCount", 0)), seconds=_seconds(v["contentDetails"].get("duration")))
    channels: dict[str, dict] = {}
    ids = sorted({r["channel_id"] for r in rows.values() if "channel_id" in r})
    for chunk in _chunks(ids):
        for c in _get("channels", part="snippet,statistics", id=",".join(chunk)).get("items", []):
            channels[c["id"]] = {"subscribers": int(c["statistics"].get("subscriberCount", 0) or 0),
                                 "born": c["snippet"]["publishedAt"][:10]}
    young_after = (datetime.now(timezone.utc) - timedelta(days=YOUNG_DAYS)).date().isoformat()
    outliers = []
    for r in rows.values():
        if "channel_id" not in r:
            continue
        r.update(channels.get(r["channel_id"], {"subscribers": 0, "born": "2000-01-01"}))
        r["score"] = round(r["views"] / max(r["subscribers"], 1000), 1)
        r["young"] = r["born"] >= young_after
        r["long"] = r["seconds"] >= 180
        if r["views"] >= MIN_VIEWS and r["score"] >= MIN_RATIO and r["subscribers"] < MAX_SUBS:
            outliers.append(r)
    outliers.sort(key=lambda r: r["views"], reverse=True)
    by_seed = defaultdict(list)
    for r in outliers:
        by_seed[r["seed"]].append(r)
    ranking = sorted(
        ({"seed": s, "outliers": len(v), "long": sum(r["long"] for r in v), "young": sum(r["young"] for r in v),
          "median_minutes": sorted(r["seconds"] for r in v)[len(v) // 2] // 60,
          "top": v[0]["title"], "top_views": v[0]["views"]} for s, v in by_seed.items()),
        key=lambda x: (x["young"] + x["long"], x["outliers"]), reverse=True)
    return {"updated": datetime.now(timezone.utc).date().isoformat(), "days": days, "videos_checked": len(rows),
            "ranking": ranking, "outliers": [o for v in by_seed.values() for o in v[:40]]}


def save(result: dict) -> None:
    RESEARCH_DIR.mkdir(exist_ok=True)
    SCAN_FILE.write_text(json.dumps(result, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")


def stale(max_age_days: int = 7) -> bool:
    if not SCAN_FILE.exists():
        return True
    updated = json.loads(SCAN_FILE.read_text(encoding="utf-8")).get("updated", "2000-01-01")
    return datetime.fromisoformat(updated).date() <= (datetime.now(timezone.utc) - timedelta(days=max_age_days)).date()


def outliers_for(topics: list[str]) -> list[dict]:
    """Scan outliers whose seed is one of a channel's scan_topics, in the breakout.py shape."""
    if not topics or not SCAN_FILE.exists():
        return []
    wanted = {t.lower() for t in topics}
    data = json.loads(SCAN_FILE.read_text(encoding="utf-8"))
    return [o for o in data.get("outliers", []) if o["seed"].lower() in wanted]


def report(result: dict, limit: int = 15) -> str:
    lines = [f"Scan {result['updated']}: {result['videos_checked']} videos from the last {result['days']} days",
             f"{'area':32} outliers long young  median  top"]
    for r in result["ranking"][:limit]:
        lines.append(f"{r['seed'][:32]:32} {r['outliers']:8} {r['long']:4} {r['young']:5}  {r['median_minutes']:4}m  "
                     f"{r['top'][:60]} ({r['top_views']:,})")
    return "\n".join(lines)
