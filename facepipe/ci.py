"""GitHub Actions helper: write the YouTube secrets to disk for every channel.

Reads SECRETS_JSON (the workflow passes `toJSON(secrets)`) and writes client_secret.json plus
tokens/<channel>.json for each YT_TOKEN_<CHANNEL> secret, e.g. YT_TOKEN_SLEEPY_HISTORY. A new
channel then only needs its secret added, not a workflow change.
"""

from __future__ import annotations

import json
import os

from .config import ROOT, list_channels


def main() -> None:
    secrets = json.loads(os.environ.get("SECRETS_JSON") or "{}")
    if secrets.get("YOUTUBE_CLIENT_SECRET_JSON"):
        (ROOT / "client_secret.json").write_text(secrets["YOUTUBE_CLIENT_SECRET_JSON"], encoding="utf-8")
    tokens = ROOT / "tokens"
    tokens.mkdir(exist_ok=True)
    found = []
    for slug in list_channels():
        value = secrets.get("YT_TOKEN_" + slug.upper().replace("-", "_"))
        if value:
            (tokens / f"{slug}.json").write_text(value, encoding="utf-8")
            found.append(slug)
    print("YouTube tokens for: " + (", ".join(found) or "none"))


if __name__ == "__main__":
    main()
