"""Hook library: the real opening lines of this week's breakout videos.

Self-scored hooks proved meaningless (the owner skipped a video the model rated 8/10), so the script
writer learns from openings that actually held viewers: for the top long outliers in a channel's
scan_topics, the first ~45 seconds of their captions are saved to research/hooks.json and shown to
Claude as examples of structure (never to copy). Same idea as transcribing top posts' openings in
Instagram research tools, done for YouTube on public captions.

Caption fetching can be refused from cloud IPs; then the library just keeps last week's entries.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

from .breakout import RESEARCH_DIR

HOOKS_FILE = RESEARCH_DIR / "hooks.json"
SECONDS = 45


def opening(video_id: str, seconds: int = SECONDS) -> str | None:
    try:
        from youtube_transcript_api import YouTubeTranscriptApi

        fetched = YouTubeTranscriptApi().fetch(video_id, languages=["en", "en-US", "en-GB"])
    except Exception as exc:  # no captions, blocked IP, library missing
        print(f"  hooks: no captions for {video_id}: {type(exc).__name__}")
        return None
    text = " ".join(s.text.replace("\n", " ") for s in fetched if s.start < seconds)
    return " ".join(text.split()) or None


def load() -> dict:
    return json.loads(HOOKS_FILE.read_text(encoding="utf-8")) if HOOKS_FILE.exists() else {"hooks": []}


def refresh(outliers: list[dict], per_run: int = 12) -> int:
    """Add openings for the biggest long outliers we don't have yet. Returns how many were added."""
    data = load()
    have = {h["id"] for h in data["hooks"]}
    added = 0
    for o in sorted((o for o in outliers if o.get("long") and o["id"] not in have), key=lambda o: -o["views"]):
        if added >= per_run:
            break
        text = opening(o["id"])
        if text:
            data["hooks"].append({"id": o["id"], "seed": o["seed"], "title": o["title"], "views": o["views"],
                                  "subscribers": o["subscribers"], "opening": text})
            added += 1
    data["hooks"] = sorted(data["hooks"], key=lambda h: -h["views"])[:200]
    data["updated"] = datetime.now(timezone.utc).date().isoformat()
    RESEARCH_DIR.mkdir(exist_ok=True)
    HOOKS_FILE.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return added


def examples(topics: list[str], limit: int = 5) -> str:
    wanted = {t.lower() for t in topics}
    picked = [h for h in load()["hooks"] if h["seed"].lower() in wanted][:limit]
    if not picked:
        return ""
    lines = [f"- \"{h['title']}\" ({h['views']:,} views on a {h['subscribers']:,}-subscriber channel) opened with: "
             f"\"{h['opening'][:400]}\"" for h in picked]
    return ("These are the real first 45 seconds of recent breakout videos in this area. Study how they open "
            "(where they drop the viewer, what detail comes first, when the question lands) and use the same "
            "kind of structure for our own story. Never copy their words or topic.\n" + "\n".join(lines))
