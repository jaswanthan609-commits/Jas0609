"""Second opinion on every script before it reaches you: a cheap, strict critic.

YouTube demonetises "inauthentic", templated content, and you approve drafts on a phone in a few
minutes, so a weak script must be stopped before the PR. Two checks:

1. Near-duplicate titles (free, local): a script whose title is too close to one we already made
   fails at once. Near-identical videos are the clearest sign of mass production.
2. Claude Haiku scores the hook, specificity, originality and policy risk. Below the bar, the
   script is rewritten once with the critic's notes; if it still fails, it is dropped.
"""

from __future__ import annotations

import difflib
import json
import re
from pathlib import Path

from pydantic import BaseModel, Field

from .config import ChannelConfig

PASS_SCORE = 7
CRITIC_MODEL = "claude-haiku-5-5"
DUPLICATE_RATIO = 0.82


class Critique(BaseModel):
    hook: int = Field(description="1-10: does the first scene grab attention and pay off the title at once?")
    specificity: int = Field(description="1-10: concrete examples, numbers, names and steps, rather than generic talk?")
    originality: int = Field(description="1-10: a distinct angle, not a template or a rehash of common videos?")
    policy_risk: int = Field(
        description="1-10 where 10 is safe: no misleading claims, made-up facts, unsafe advice for kids, "
        "financial advice or guaranteed returns, or clickbait the video doesn't deliver."
    )
    fixes: list[str] = Field(description="The most important changes, at most 5, each one sentence.")

    @property
    def score(self) -> int:
        return min(self.hook, self.specificity, self.originality, self.policy_risk)


def _norm(title: str) -> str:
    return re.sub(r"[^a-z0-9 ]+", "", title.lower()).strip()


def duplicate_of(title: str, previous: list[str]) -> str | None:
    t = _norm(title)
    for p in previous:
        if difflib.SequenceMatcher(None, t, _norm(p)).ratio() >= DUPLICATE_RATIO:
            return p
    return None


def previous_titles(cfg: ChannelConfig, exclude: Path | None = None) -> list[str]:
    titles = []
    for path in cfg.output_path.glob("*/script.json"):
        if exclude and path.resolve() == exclude.resolve():
            continue
        try:
            titles.append(json.loads(path.read_text(encoding="utf-8"))["title"])
        except (KeyError, json.JSONDecodeError):
            continue
    return titles


def critique(cfg: ChannelConfig, script) -> Critique:
    from .script import _parse

    body = "\n".join(f"{i + 1}. {s.narration}" for i, s in enumerate(script.scenes))
    prompt = (
        "You are a strict YouTube editor. Score this script for the channel described in your "
        "instructions. Be harsh: most first drafts deserve 5-7. Judge only what is written.\n\n"
        f"Title: {script.title}\nThumbnail text: {script.thumbnail_text}\n\nNarration by scene:\n{body}"
    )
    return _parse(cfg, prompt, Critique, max_tokens=3000, model=CRITIC_MODEL)


def notes_for_rewrite(c: Critique) -> str:
    return "An editor rejected the first draft. Fix all of these:\n- " + "\n- ".join(c.fixes)
