"""One trading day: fetch prices, ask Claude for orders, fill them at the close with fees, log it.

State lives in trading/state.json, every order and daily value in trading/journal.jsonl, and the
scorecard in trading/report.md. GitHub runs this on weekdays after the NSE close.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "config" / "trader.yaml"
DATA_DIR = ROOT / "trading"


class Order(BaseModel):
    ticker: str = Field(description="One ticker from the universe, e.g. 'ITC.NS'.")
    action: Literal["buy", "sell"]
    shares: int = Field(description="Whole number of shares, at least 1.")
    reason: str = Field(description="One sentence: why, based on the data given.")


class Decision(BaseModel):
    view: str = Field(description="Two sentences on the market today, from the data given.")
    orders: list[Order] = Field(description="Orders for today; an empty list means hold everything.")


SYSTEM = """You manage a small paper-trading portfolio of Indian stocks and ETFs (NSE, delivery only:
no F&O, no intraday, no short selling, no leverage). Your goal is to beat simply buying and holding
the Nifty 50 ETF (NIFTYBEES) after fees, without large losses.
Fees are real and matter a lot at this size: every sale costs about Rs 16 flat plus 0.1%, every
purchase about 0.12%. Trading too often is the most common way to lose to the index, so trade only
when the data gives a clear reason, and holding is a valid choice. Keep each holding under {max_share:.0%}
of the portfolio. Use only the data provided; do not invent news. Shares are whole numbers."""


@dataclass
class Config:
    started: date
    starting_cash: float
    benchmark: str
    model: str
    max_share: float
    review_after_days: int
    beat_by: float
    max_drawdown: float
    fees: dict
    universe: list[str]


def load_config(path: Path = CONFIG) -> Config:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    started = raw["started"]
    return Config(
        started=started if isinstance(started, date) else date.fromisoformat(str(started)),
        starting_cash=float(raw["starting_cash_inr"]),
        benchmark=raw["benchmark"],
        model=raw["model"],
        max_share=float(raw["max_position_share"]),
        review_after_days=int(raw["review_after_days"]),
        beat_by=float(raw["pass_rule"]["beat_benchmark_by_pct"]),
        max_drawdown=float(raw["pass_rule"]["max_drawdown_pct"]),
        fees=raw["fees"],
        universe=list(raw["universe"]),
    )


# ---------- market data ----------

def fetch_history(tickers: list[str], days: int = 120) -> tuple[dict[str, list[float]], date | None]:
    """Daily closes per ticker, oldest first, and the date of the latest close (Yahoo Finance)."""
    import yfinance as yf

    data = yf.download(tickers, period=f"{days}d", interval="1d", progress=False, auto_adjust=False,
                       group_by="column", threads=False)
    closes = data["Close"]
    out = {}
    for t in tickers:
        if t in closes:
            series = [float(x) for x in closes[t].dropna().tolist()]
            if len(series) >= 30:
                out[t] = series
    last = closes.index[-1].date() if len(closes.index) else None
    return out, last


def _ret(series: list[float], n: int) -> float:
    return (series[-1] / series[-1 - n] - 1) * 100 if len(series) > n else 0.0


def _rsi(series: list[float], n: int = 14) -> float:
    gains = losses = 0.0
    for a, b in zip(series[-n - 1 : -1], series[-n:]):
        change = b - a
        gains += max(change, 0)
        losses += max(-change, 0)
    if losses == 0:
        return 100.0
    rs = gains / losses
    return 100 - 100 / (1 + rs)


def _vol(series: list[float], n: int = 20) -> float:
    rets = [b / a - 1 for a, b in zip(series[-n - 1 : -1], series[-n:])]
    mean = sum(rets) / len(rets)
    return math.sqrt(sum((r - mean) ** 2 for r in rets) / len(rets)) * math.sqrt(252) * 100


def features(history: dict[str, list[float]]) -> dict[str, dict]:
    out = {}
    for t, s in history.items():
        ma50 = sum(s[-50:]) / min(len(s), 50)
        out[t] = {
            "price": round(s[-1], 2),
            "ret_5d_pct": round(_ret(s, 5), 2),
            "ret_20d_pct": round(_ret(s, 20), 2),
            "ret_60d_pct": round(_ret(s, 60), 2),
            "vs_50d_avg_pct": round((s[-1] / ma50 - 1) * 100, 2),
            "rsi_14": round(_rsi(s), 1),
            "volatility_pct": round(_vol(s), 1),
        }
    return out


# ---------- portfolio ----------

def _path(name: str) -> Path:
    DATA_DIR.mkdir(exist_ok=True)
    return DATA_DIR / name


def load_state(cfg: Config, prices: dict[str, float]) -> dict:
    path = DATA_DIR / "state.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    bench_price = prices[cfg.benchmark]
    units = int(cfg.starting_cash // (bench_price * (1 + cfg.fees["buy_pct"] / 100)))
    bench_cash = cfg.starting_cash - units * bench_price * (1 + cfg.fees["buy_pct"] / 100)
    return {"cash": cfg.starting_cash, "positions": {}, "fees_paid": 0.0, "trades": 0,
            "peak": cfg.starting_cash, "max_drawdown_pct": 0.0,
            "benchmark": {"units": units, "cash": round(bench_cash, 2), "start_price": bench_price}}


def save_state(state: dict) -> None:
    _path("state.json").write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def value(state: dict, prices: dict[str, float]) -> float:
    held = sum(p["shares"] * prices.get(t, p["avg_price"]) for t, p in state["positions"].items())
    return state["cash"] + held


def benchmark_value(state: dict, prices: dict[str, float], cfg: Config) -> float:
    b = state["benchmark"]
    return b["cash"] + b["units"] * prices.get(cfg.benchmark, b["start_price"])


def execute(cfg: Config, state: dict, orders: list[Order], prices: dict[str, float]) -> list[dict]:
    """Fill valid orders at today's close; refuse anything unaffordable, oversized or unknown."""
    fills = []
    sold_today = set()
    for o in sorted(orders, key=lambda o: o.action != "sell"):  # sells first, to free cash
        price = prices.get(o.ticker)
        result = {"ticker": o.ticker, "action": o.action, "shares": o.shares, "reason": o.reason}
        if price is None or o.ticker not in cfg.universe or o.shares < 1:
            fills.append({**result, "status": "rejected: unknown ticker or bad size"})
            continue
        pos = state["positions"].get(o.ticker)
        if o.action == "sell":
            if not pos or pos["shares"] < o.shares:
                fills.append({**result, "status": "rejected: not held"})
                continue
            gross = o.shares * price
            fee = gross * cfg.fees["sell_pct"] / 100 + (0 if o.ticker in sold_today else cfg.fees["sell_flat_inr"])
            sold_today.add(o.ticker)
            state["cash"] += gross - fee
            pos["shares"] -= o.shares
            if pos["shares"] == 0:
                del state["positions"][o.ticker]
        else:
            gross = o.shares * price
            fee = gross * cfg.fees["buy_pct"] / 100
            if gross + fee > state["cash"]:
                fills.append({**result, "status": "rejected: not enough cash"})
                continue
            after = (pos["shares"] if pos else 0) * price + gross
            if after > cfg.max_share * value(state, prices) + price:  # one share of slack
                fills.append({**result, "status": "rejected: position too large"})
                continue
            state["cash"] -= gross + fee
            if pos:
                pos["avg_price"] = (pos["avg_price"] * pos["shares"] + gross) / (pos["shares"] + o.shares)
                pos["shares"] += o.shares
            else:
                state["positions"][o.ticker] = {"shares": o.shares, "avg_price": price}
        state["fees_paid"] += fee
        state["trades"] += 1
        fills.append({**result, "price": round(price, 2), "fee": round(fee, 2), "status": "filled"})
    state["cash"] = round(state["cash"], 2)
    return fills


# ---------- Claude ----------

def ask_claude(cfg: Config, state: dict, feats: dict[str, dict], prices: dict[str, float]) -> Decision:
    import anthropic

    holdings = {t: {"shares": p["shares"], "avg_price": round(p["avg_price"], 2),
                    "value": round(p["shares"] * prices.get(t, p["avg_price"]), 2)}
                for t, p in state["positions"].items()}
    prompt = (
        f"Date: {date.today().isoformat()}\n"
        f"Cash: Rs {state['cash']:.2f}\nPortfolio value: Rs {value(state, prices):.2f}\n"
        f"Holdings: {json.dumps(holdings)}\n"
        f"Orders you place now are filled at the next trading day's close, not today's.\n"
        f"Market data per ticker (price in Rs; returns, distance from 50-day average, RSI, annual volatility):\n"
        f"{json.dumps(feats, indent=1)}\n\nDecide today's orders."
    )
    client = anthropic.Anthropic()
    response = client.beta.messages.parse(
        model=cfg.model,
        max_tokens=4000,
        system=SYSTEM.format(max_share=cfg.max_share),
        messages=[{"role": "user", "content": prompt}],
        output_config={"effort": "medium"},
        output_format=Decision,
    )
    try:
        from facepipe import budget

        budget.record("claude", "paper-trader", budget.claude_cost(cfg.model, response.usage), model=cfg.model)
    except Exception:  # the trader also works without the video pipeline's ledger
        pass
    if response.stop_reason == "refusal" or response.parsed_output is None:
        return Decision(view=f"No decision ({response.stop_reason}); holding.", orders=[])
    return response.parsed_output


# ---------- one day ----------

def run_day(cfg: Config, history: dict[str, list[float]], decide=ask_claude, today: date | None = None) -> dict:
    """Fill yesterday's orders at today's close, then decide new orders for tomorrow.

    Orders are never filled at the same close Claude just saw: that would be look-ahead, a common
    reason backtests look better than real trading.
    """
    today = today or date.today()
    prices = {t: s[-1] for t, s in history.items()}
    if cfg.benchmark not in prices:
        raise RuntimeError(f"No price for the benchmark {cfg.benchmark}; skipping today.")
    state = load_state(cfg, prices)
    if state.get("last_day") == today.isoformat():
        return {"skipped": "already ran today"}
    pending = [Order(**o) for o in state.pop("pending", [])]
    fills = execute(cfg, state, pending, prices)
    decision = decide(cfg, state, features(history), prices)
    state["pending"] = [o.model_dump() for o in decision.orders]
    total = value(state, prices)
    state["peak"] = max(state["peak"], total)
    state["max_drawdown_pct"] = round(max(state["max_drawdown_pct"], (1 - total / state["peak"]) * 100), 2)
    state["last_day"] = today.isoformat()
    save_state(state)
    entry = {"day": today.isoformat(), "view": decision.view, "fills": fills,
             "orders_for_next_day": state["pending"],
             "value": round(total, 2), "benchmark_value": round(benchmark_value(state, prices, cfg), 2),
             "cash": state["cash"]}
    with open(_path("journal.jsonl"), "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")
    _path("report.md").write_text(report(cfg, state, prices, today) + "\n", encoding="utf-8")
    return entry


def verdict(cfg: Config, state: dict, prices: dict[str, float], today: date) -> tuple[str, float, float]:
    bot = (value(state, prices) / cfg.starting_cash - 1) * 100
    bench = (benchmark_value(state, prices, cfg) / cfg.starting_cash - 1) * 100
    days = (today - cfg.started).days
    if days < cfg.review_after_days:
        return f"testing: day {days} of {cfg.review_after_days}", bot, bench
    passed = bot - bench >= cfg.beat_by and state["max_drawdown_pct"] <= cfg.max_drawdown
    if passed:
        return "PASSED: beat the Nifty after fees with limited losses; real money can be considered", bot, bench
    return "FAILED: did not beat holding the Nifty after fees; keep the money in videos or an index fund", bot, bench


def report(cfg: Config, state: dict, prices: dict[str, float], today: date) -> str:
    status, bot, bench = verdict(cfg, state, prices, today)
    lines = [
        f"# Paper-trading scorecard ({today.isoformat()})",
        "",
        f"**{status}**",
        "",
        "| | Bot | Hold the Nifty |",
        "|---|---|---|",
        f"| Value | Rs {value(state, prices):,.0f} | Rs {benchmark_value(state, prices, cfg):,.0f} |",
        f"| Return | {bot:+.2f}% | {bench:+.2f}% |",
        "",
        f"Started with Rs {cfg.starting_cash:,.0f} on {cfg.started}. Trades: {state['trades']}, "
        f"fees paid: Rs {state['fees_paid']:,.0f}, worst drop from peak: {state['max_drawdown_pct']:.1f}%.",
        "",
        "Holdings: " + (", ".join(f"{t} x{p['shares']}" for t, p in state["positions"].items()) or "cash only")
        + f"; cash Rs {state['cash']:,.0f}.",
        "",
        f"Pass rule: beat holding the Nifty by {cfg.beat_by:g}+ points after fees, with no drop over "
        f"{cfg.max_drawdown:g}% from peak, after {cfg.review_after_days} days. Paper money only.",
    ]
    return "\n".join(lines)
