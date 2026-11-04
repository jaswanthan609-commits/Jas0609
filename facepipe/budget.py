"""Self-funding budget: the autopilot only spends what it has.

Money in:  the starting budget (config/autopilot.yaml) plus a share of the YouTube ad revenue the
           channels have earned since the autopilot started (ledger/revenue.json, written weekly by
           `stats --save-revenue`).
Money out: every Claude call and AI image is logged to ledger/spend.jsonl with its cost.

Each morning `plan` decides which channels draft today. It keeps a steady pace (the money left
spread over `runway_days`), checks the last 7 days' spending against that pace, drafts the cheapest
and most important channels first, and opens new channels once earnings pass their unlock level.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import yaml

from .config import ROOT

AUTOPILOT = ROOT / "config" / "autopilot.yaml"
LEDGER_DIR = ROOT / "ledger"
DAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]

# USD per million tokens (input, output), Claude API list prices.
PRICES = {
    "claude-fable-5-1": (10.0, 50.0),
    "claude-opus-5-5": (4.0, 20.0),
    "claude-opus-5": (5.0, 25.0),
    "claude-sonnet-5-5": (2.0, 10.0),
    "claude-sonnet-5": (2.0, 10.0),
    "claude-haiku-5-5": (0.10, 0.50),
}


@dataclass
class ChannelPlan:
    slug: str
    long_days: list[str] = field(default_factory=lambda: list(DAYS))
    short_days: list[str] = field(default_factory=lambda: list(DAYS))
    est_long_usd: float = 0.15
    est_short_usd: float = 0.02
    unlock_at_usd: float = 0.0  # lifetime earnings needed before this channel starts
    paused: bool = False


@dataclass
class Autopilot:
    started: date
    starting_budget_usd: float
    reinvest_share: float
    runway_days: int
    usd_inr: float
    image_usd: float
    channels: list[ChannelPlan]


def load(path: Path = AUTOPILOT) -> Autopilot:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    started = raw["started"]
    return Autopilot(
        started=started if isinstance(started, date) else date.fromisoformat(str(started)),
        starting_budget_usd=float(raw["starting_budget_usd"]),
        reinvest_share=float(raw.get("reinvest_share", 1.0)),
        runway_days=int(raw.get("runway_days", 60)),
        usd_inr=float(raw.get("usd_inr", 88)),
        image_usd=float(raw.get("image_usd", 0.07)),
        channels=[ChannelPlan(**c) for c in raw["channels"]],
    )


def active_channels(ap: Autopilot | None = None) -> list[str]:
    """Channels the autopilot runs (in config/autopilot.yaml and not paused)."""
    ap = ap or load()
    return [ch.slug for ch in ap.channels if not ch.paused]


def image_cost() -> float:
    try:
        return load().image_usd
    except FileNotFoundError:
        return 0.07


def _ledger(name: str) -> Path:
    LEDGER_DIR.mkdir(exist_ok=True)
    return LEDGER_DIR / name


def claude_cost(model: str, usage) -> float:
    price_in, price_out = PRICES.get(model, PRICES["claude-opus-5-5"])
    tokens_in = (getattr(usage, "input_tokens", 0) or 0) + (getattr(usage, "cache_creation_input_tokens", 0) or 0)
    tokens_in += (getattr(usage, "cache_read_input_tokens", 0) or 0) * 0.1
    tokens_out = getattr(usage, "output_tokens", 0) or 0
    return (tokens_in * price_in + tokens_out * price_out) / 1_000_000


def record(kind: str, channel: str, usd: float, **details) -> None:
    """Append one cost to ledger/spend.jsonl."""
    entry = {"at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "kind": kind,
             "channel": channel, "usd": round(usd, 5), **details}
    with open(_ledger("spend.jsonl"), "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


def spend_entries() -> list[dict]:
    path = LEDGER_DIR / "spend.jsonl"
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def spent(since: datetime | None = None) -> float:
    total = 0.0
    for e in spend_entries():
        if since is None or datetime.fromisoformat(e["at"]) >= since:
            total += e["usd"]
    return total


def earned_inr() -> dict[str, float]:
    """Lifetime ad revenue per channel since the autopilot started, as last saved by stats."""
    path = LEDGER_DIR / "revenue.json"
    if not path.exists():
        return {}
    return {slug: float(v.get("revenue_inr", 0)) for slug, v in json.loads(path.read_text(encoding="utf-8")).items()}


def save_revenue(slug: str, revenue_inr: float, since: str, until: str) -> None:
    path = _ledger("revenue.json")
    data = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    data[slug] = {"revenue_inr": round(revenue_inr, 2), "since": since, "until": until}
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def earned_usd(ap: Autopilot) -> float:
    return sum(earned_inr().values()) / ap.usd_inr


def available(ap: Autopilot) -> float:
    """Money the autopilot may still spend: start + reinvested earnings - spent."""
    return ap.starting_budget_usd + ap.reinvest_share * earned_usd(ap) - spent()


@dataclass
class Today:
    jobs: list[tuple[str, int, int]]  # (channel slug, long scripts, shorts)
    notes: list[str]
    available_usd: float
    weekly_allowance_usd: float


def plan(ap: Autopilot, today: date | None = None, now: datetime | None = None) -> Today:
    today = today or date.today()
    now = now or datetime.now(timezone.utc)
    day = DAYS[today.weekday()]
    left = available(ap)
    earned = earned_usd(ap)
    weekly = max(left, 0) / max(ap.runway_days, 1) * 7
    this_week = spent(since=now - timedelta(days=7))
    room = weekly - this_week
    notes = [
        f"money left ${left:.2f} (start ${ap.starting_budget_usd:.0f} + {ap.reinvest_share:.0%} of "
        f"${earned:.2f} earned - ${spent():.2f} spent)",
        f"pace ${weekly:.2f}/week; spent ${this_week:.2f} in the last 7 days; room today ${room:.2f}",
    ]
    jobs = []
    if left <= 0:
        notes.append("out of money: nothing drafted until earnings come in")
        return Today(jobs, notes, left, weekly)
    for ch in ap.channels:
        if ch.paused:
            continue
        if earned < ch.unlock_at_usd:
            notes.append(f"{ch.slug}: locked until earnings reach ${ch.unlock_at_usd:.0f}")
            continue
        n_long = 1 if day in ch.long_days else 0
        n_short = 1 if day in ch.short_days else 0
        cost = n_long * ch.est_long_usd + n_short * ch.est_short_usd
        if not cost:
            continue
        if cost > room and n_long:
            # Drop the long video first; Shorts are cheap and keep the channel active.
            n_long, cost = 0, n_short * ch.est_short_usd
        if not cost or cost > room:
            notes.append(f"{ch.slug}: skipped today to stay on pace")
            continue
        room -= cost
        jobs.append((ch.slug, n_long, n_short))
    return Today(jobs, notes, left, weekly)
