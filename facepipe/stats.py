"""Channel results against the monthly target, from the YouTube Analytics API (last 28 days)."""

from __future__ import annotations

from datetime import date, timedelta

from .config import ChannelConfig

METRICS = "views,estimatedMinutesWatched,subscribersGained,subscribersLost"
MONEY = "estimatedRevenue"


def last_28_days(cfg: ChannelConfig) -> dict:
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError

    from .upload import credentials

    analytics = build("youtubeAnalytics", "v2", credentials=credentials(cfg))
    end = date.today() - timedelta(days=2)  # analytics lag about 2 days
    start = end - timedelta(days=27)
    query = dict(ids="channel==MINE", startDate=start.isoformat(), endDate=end.isoformat(), currency="INR")
    try:
        resp = analytics.reports().query(metrics=f"{METRICS},{MONEY}", **query).execute()
    except HttpError:
        # Revenue is only available once the channel is monetised.
        resp = analytics.reports().query(metrics=METRICS, **query).execute()
    headers = [h["name"] for h in resp.get("columnHeaders", [])]
    row = (resp.get("rows") or [[0] * len(headers)])[0]
    data = dict(zip(headers, row))
    data["start"], data["end"] = start.isoformat(), end.isoformat()
    return data


def report(cfg: ChannelConfig, data: dict) -> str:
    views = int(data.get("views", 0))
    hours = data.get("estimatedMinutesWatched", 0) / 60
    subs = int(data.get("subscribersGained", 0) - data.get("subscribersLost", 0))
    lines = [
        f"{cfg.name} ({cfg.slug})  {data['start']} to {data['end']}",
        f"  views {views:,}   watch hours {hours:,.0f}   net subscribers {subs:+,}",
    ]
    if MONEY in data:
        revenue = data[MONEY]
        rpm = revenue / views * 1000 if views else 0
        line = f"  ad revenue Rs {revenue:,.0f}   RPM Rs {rpm:,.0f}"
        if cfg.monthly_target_inr:
            line += f"   target Rs {cfg.monthly_target_inr:,} ({revenue / cfg.monthly_target_inr:.0%} of target)"
            if rpm:
                needed = cfg.monthly_target_inr / rpm * 1000
                line += f"\n  views needed at this RPM: {needed:,.0f} a month ({views / needed:.0%} there)"
        lines.append(line)
    else:
        lines.append("  not monetised yet: aim for 1,000 subscribers and 4,000 watch hours in 12 months")
    return "\n".join(lines)
