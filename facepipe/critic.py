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


SLOW = {"deep", "sleep"}
WEAK_OPENERS = ("welcome", "hey guys", "hi everyone", "hello everyone", "in this video", "today we",
                "today i", "have you ever wondered", "let's dive", "let us dive", "before we start",
                "don't forget to subscribe", "make sure to subscribe")
FILLER = ("in today's video", "without further ado", "fast forward", "little did they know",
          "buckle up", "game changer", "let that sink in", "delve")


def hook_score(line: str) -> tuple[int, str, str]:
    """Rule-based hook score from youtube-agent-skill (MIT, facepipe/vendor/ytagent)."""
    from .vendor.ytagent import hookscore

    parts, verdict, _, _ = hookscore.score(line)
    weakest = min(parts, key=parts.get)
    return verdict, weakest.lower(), hookscore.FIX[weakest]


def lint(script, fmt: str = "long") -> list[str]:
    """Free, rule-based checks that need no model: the things a viewer skips on in the first seconds.

    Self-scored hooks proved meaningless (2026-11-04: the owner skipped a video the model scored 8/10),
    so hard rules from what top videos do come first and the model critic second.
    """
    problems = []
    title = script.title.strip()
    if len(title) > (100 if fmt in SLOW else 70):
        problems.append(f"The title is {len(title)} characters; keep it under {100 if fmt in SLOW else 70}.")
    if not script.scenes:
        return problems + ["The script has no scenes."]
    first = script.scenes[0].narration.strip().lower()
    whole = " ".join(s.narration for s in script.scenes).lower()
    if fmt not in SLOW:
        if first.startswith(WEAK_OPENERS):
            problems.append("The first line is a greeting or 'in this video'. Start inside the story's most dramatic moment.")
        opening = " ".join(s.narration for s in script.scenes[:2])
        if not re.search(r"\d|[A-Z][a-z]+ [A-Z][a-z]+", opening):
            problems.append("The first 2 scenes have no number, date or named person. Open with one specific, real detail.")
        if len(first.split()) > 40:
            problems.append("The first scene runs over 40 words. The cold open must land in one or two short sentences.")
        verdict, weakest, fix = hook_score(script.scenes[0].narration)
        if verdict < 40:  # only clearly dead hooks: a strong real cold open scored 47 in testing
            problems.append(f"The opening line scores {verdict}/100 as a hook (weakest: {weakest}): {fix}.")
    else:
        for word in ("shocking", "you won't believe", "insane", "!"):
            if word in whole:
                problems.append(f"Sleep scripts must stay calm: remove '{word}'.")
                break
    for phrase in FILLER:
        if phrase in whole:
            problems.append(f"Cut the stock phrase '{phrase}'; it marks templated content.")
    return problems


def critique(cfg: ChannelConfig, script, fmt: str = "long") -> Critique:
    from .script import _parse

    body = "\n".join(f"{i + 1}. {s.narration}" for i, s in enumerate(script.scenes))
    if fmt in SLOW:
        rules = ("This is a calm video people fall asleep to. Score 'hook' as: does the opening set a warm, "
                 "vivid scene and promise a gentle journey (no drama or cliffhangers expected). ")
    else:
        rules = ("Score 'hook' as: would a viewer scrolling past stop and stay for the first 30 seconds? "
                 "Anything that opens with context, a greeting or a vague claim is 4 or below. ")
    prompt = (
        "You are a strict YouTube editor. Score this script for the channel described in your "
        "instructions. Be harsh: most first drafts deserve 5-7. Judge only what is written. "
        f"{rules}\n\n"
        f"Title: {script.title}\nThumbnail text: {script.thumbnail_text}\n\nNarration by scene:\n{body}"
    )
    return _parse(cfg, prompt, Critique, max_tokens=3000, model=CRITIC_MODEL)


def notes_for_rewrite(c: Critique) -> str:
    return "An editor rejected the first draft. Fix all of these:\n- " + "\n- ".join(c.fixes)
