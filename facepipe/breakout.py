"""Breakout engine: copy what is already working, then double down on our own winners.

1. Outliers (weekly): search YouTube for recent videos in each channel's niche and score them by
   views / subscribers. A video with 20x more views than its channel has subscribers proves the
   topic and angle, not the channel's size. The best ones go to research/<channel>.json and Claude
   uses them as inspiration (same proven angle, our own original take) when it writes topic ideas.
2. Winners (daily): check the views of our own published videos. A video that reaches
   `WINNER_RATIO` x the channel's median views after 2 days is a winner: Claude writes follow-up
   topics (a sequel, a deeper dive, the next question viewers ask) and they jump to the front of
   the topic queue.

Uses the public YouTube Data API with YOUTUBE_API_KEY (free from Google Cloud). Search costs 100
quota units of the free 10,000 a day, so outliers are refreshed once a week.
"""

from __future__ import annotations

import json
import statistics
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

from .config import ROOT, ChannelConfig, env

API = "https://www.googleapis.com/youtube/v3"
RESEARCH_DIR = ROOT / "research"
WINNER_RATIO = 3.0
MIN_WINNER_VIEWS = 500
MIN_AGE = timedelta(days=2)


def _get(path: str, **params) -> dict:
    params["key"] = env("YOUTUBE_API_KEY")
    r = requests.get(f"{API}/{path}", params=params, timeout=30)
    r.raise_for_status()
    return r.json()


def _chunks(items: list, n: int = 50):
    for i in range(0, len(items), n):
        yield items[i : i + n]


def video_stats(ids: list[str]) -> dict[str, dict]:
    out = {}
    for chunk in _chunks(ids):
        data = _get("videos", part="snippet,statistics", id=",".join(chunk), maxResults=50)
        for v in data.get("items", []):
            out[v["id"]] = {
                "title": v["snippet"]["title"],
                "channel_id": v["snippet"]["channelId"],
                "channel": v["snippet"].get("channelTitle", ""),
                "published": v["snippet"]["publishedAt"],
                "views": int(v["statistics"].get("viewCount", 0)),
            }
    return out


def subscribers(channel_ids: list[str]) -> dict[str, int]:
    out = {}
    for chunk in _chunks(sorted(set(channel_ids))):
        data = _get("channels", part="statistics", id=",".join(chunk), maxResults=50)
        for c in data.get("items", []):
            out[c["id"]] = int(c["statistics"].get("subscriberCount", 0) or 0)
    return out


def find_outliers(cfg: ChannelConfig, days: int = 45, per_query: int = 25, keep: int = 15) -> list[dict]:
    after = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")
    ids = []
    for query in cfg.research_queries or cfg.default_tags[:3]:
        data = _get("search", part="id", q=query, type="video", order="viewCount", publishedAfter=after,
                    relevanceLanguage=cfg.language, maxResults=per_query,
                    safeSearch="strict" if cfg.made_for_kids else "none")
        ids += [i["id"]["videoId"] for i in data.get("items", []) if i.get("id", {}).get("videoId")]
    stats = video_stats(list(dict.fromkeys(ids)))
    subs = subscribers([s["channel_id"] for s in stats.values()])
    scored = []
    for vid, s in stats.items():
        n_subs = subs.get(s["channel_id"], 0)
        s.update(id=vid, subscribers=n_subs, score=round(s["views"] / max(n_subs, 1000), 1))
        scored.append(s)
    scored.sort(key=lambda s: s["score"], reverse=True)
    return scored[:keep]


def save_outliers(cfg: ChannelConfig, outliers: list[dict]) -> Path:
    RESEARCH_DIR.mkdir(exist_ok=True)
    path = RESEARCH_DIR / f"{cfg.slug}.json"
    payload = {"updated": datetime.now(timezone.utc).date().isoformat(), "outliers": outliers}
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def load_outliers(cfg: ChannelConfig) -> list[dict]:
    """This channel's own outliers plus the weekly cross-niche scan's outliers for its scan_topics."""
    from . import scan

    path = RESEARCH_DIR / f"{cfg.slug}.json"
    own = json.loads(path.read_text(encoding="utf-8")).get("outliers", []) if path.exists() else []
    seen = {o["id"] for o in own}
    extra = [o for o in scan.outliers_for(cfg.scan_topics) if o["id"] not in seen]
    return sorted(own + extra, key=lambda o: o["score"], reverse=True)


def outliers_stale(cfg: ChannelConfig, max_age_days: int = 7) -> bool:
    path = RESEARCH_DIR / f"{cfg.slug}.json"
    if not path.exists():
        return True
    updated = json.loads(path.read_text(encoding="utf-8")).get("updated", "2000-01-01")
    return datetime.fromisoformat(updated).date() <= (datetime.now(timezone.utc) - timedelta(days=max_age_days)).date()


def inspiration_text(outliers: list[dict], limit: int = 10) -> str:
    lines = [f"- \"{o['title']}\": {o['views']:,} views on a channel with {o['subscribers']:,} subscribers"
             for o in outliers[:limit]]
    return "\n".join(lines)


def _published(cfg: ChannelConfig) -> list[tuple[Path, dict]]:
    out = []
    for meta_path in sorted(cfg.output_path.glob("*/metadata.json")):
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        if meta.get("video_id"):
            out.append((meta_path, meta))
    return out


def find_winners(cfg: ChannelConfig, now: datetime | None = None) -> list[dict]:
    """Our videos at least 2 days old with WINNER_RATIO x the channel's median views, not yet followed up."""
    now = now or datetime.now(timezone.utc)
    published = _published(cfg)
    if len(published) < 3:
        return []
    stats = video_stats([m["video_id"] for _, m in published])
    views = [s["views"] for s in stats.values()]
    median = statistics.median(views) if views else 0
    winners = []
    for meta_path, meta in published:
        s = stats.get(meta["video_id"])
        if not s or meta.get("followed_up"):
            continue
        age = now - datetime.fromisoformat(s["published"].replace("Z", "+00:00"))
        if age >= MIN_AGE and s["views"] >= max(MIN_WINNER_VIEWS, WINNER_RATIO * median):
            winners.append({**s, "id": meta["video_id"], "format": meta.get("format"),
                            "median": median, "meta_path": meta_path})
    return winners


def mark_followed_up(winner: dict) -> None:
    path = winner["meta_path"]
    meta = json.loads(path.read_text(encoding="utf-8"))
    meta["followed_up"] = datetime.now(timezone.utc).date().isoformat()
    meta["views_at_follow_up"] = winner["views"]
    path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")


def push_topics_first(topics_file: Path, topics: list[str]) -> None:
    """Put follow-up topics at the front of the queue."""
    existing = topics_file.read_text(encoding="utf-8") if topics_file.exists() else ""
    topics_file.write_text("\n".join(topics) + "\n" + existing, encoding="utf-8")
