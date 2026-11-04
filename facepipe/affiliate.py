"""Affiliate links in video descriptions: income that doesn't wait for the YouTube Partner Program.

Each channel lists its links in its config under `affiliate_links`. A link is added to a video's
description when its `always` flag is set or one of its `keywords` appears in the title or narration.
Links with an empty url are skipped, so a channel earns nothing here until you paste in your own
referral or affiliate links after signing up. Made for Kids videos never get links.
"""

from __future__ import annotations

from .config import ChannelConfig

DISCLOSURE = "Some links below are affiliate links: I may earn a small commission at no extra cost to you."
MAX_LINKS = 3


def pick(cfg: ChannelConfig, text: str) -> list[dict]:
    if cfg.made_for_kids:
        return []
    text = text.lower()
    chosen = []
    for link in cfg.affiliate_links:
        if not (link.get("url") or "").strip():
            continue
        keywords = [k.lower() for k in link.get("keywords", [])]
        if link.get("always") or any(k in text for k in keywords):
            chosen.append(link)
    return chosen[:MAX_LINKS]


def with_links(cfg: ChannelConfig, description: str, text: str) -> str:
    """The description with matching affiliate links and the disclosure added near the top."""
    links = pick(cfg, text)
    if not links:
        return description
    lines = [f"{link['label']}: {link['url'].strip()}" for link in links]
    block = "\n".join([DISCLOSURE, *lines])
    hook, _, rest = description.partition("\n")
    return f"{hook}\n\n{block}\n\n{rest.lstrip()}".rstrip() if rest else f"{hook}\n\n{block}"
