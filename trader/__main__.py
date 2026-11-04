"""python -m trader run     one trading day (after the NSE close)
python -m trader report  print the scorecard"""

from __future__ import annotations

import os
import sys
from datetime import date

from dotenv import load_dotenv

from . import bot


def main(argv=None) -> None:
    argv = sys.argv[1:] if argv is None else argv
    load_dotenv(bot.ROOT / ".env")
    cfg = bot.load_config()
    command = argv[0] if argv else "report"
    if command == "run":
        tickers = list(dict.fromkeys(cfg.universe + [cfg.benchmark]))
        history, last = bot.fetch_history(tickers)
        if last != date.today():
            print(f"No NSE close for today (latest {last}); market holiday or data delay, skipping.")
        else:
            print(bot.run_day(cfg, history))
    report = (bot.DATA_DIR / "report.md")
    text = report.read_text(encoding="utf-8") if report.exists() else "No trading days yet."
    print(text)
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as f:
            f.write(text + "\n")


if __name__ == "__main__":
    main()
