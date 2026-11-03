"""YouTube Data API v3 upload with title, tags, thumbnail and scheduled publishing.

Setup (one time):
1. In Google Cloud Console, create a project and enable "YouTube Data API v3".
2. Create an OAuth client ID of type "Desktop app" and download it as client_secret.json
   into the repo root (or set YOUTUBE_CLIENT_SECRETS to its path).
3. Run `python -m facepipe --channel <name> auth` once per channel. It opens a browser: sign in and
   pick that channel's YouTube account (brand account). The token is saved as tokens/<name>.json.

Note: until your Google Cloud project passes YouTube's API audit, videos uploaded through the
API by unverified projects are locked to private. Apply for the audit early.
"""

from __future__ import annotations

import os
from datetime import datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from .config import ROOT, ChannelConfig

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube",
    "https://www.googleapis.com/auth/yt-analytics.readonly",
    "https://www.googleapis.com/auth/yt-analytics-monetary.readonly",
]


def _paths(cfg: ChannelConfig) -> tuple[Path, Path]:
    secrets = Path(os.environ.get("YOUTUBE_CLIENT_SECRETS", ROOT / "client_secret.json"))
    token = ROOT / "tokens" / f"{cfg.slug}.json"
    token.parent.mkdir(exist_ok=True)
    return secrets, token


def credentials(cfg: ChannelConfig):
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow

    secrets, token = _paths(cfg)
    creds = Credentials.from_authorized_user_file(str(token), SCOPES) if token.exists() else None
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    elif not creds or not creds.valid:
        if os.environ.get("CI"):
            raise RuntimeError(f"No valid YouTube token for {cfg.slug} in CI. Add the YT_TOKEN secret (see README).")
        if not secrets.exists():
            raise RuntimeError(f"Missing {secrets}. See the YouTube setup steps in README.md.")
        creds = InstalledAppFlow.from_client_secrets_file(str(secrets), SCOPES).run_local_server(port=0)
    token.write_text(creds.to_json(), encoding="utf-8")
    return creds


def next_slot(cfg: ChannelConfig, taken: list[datetime], now: datetime | None = None) -> datetime:
    """Next free daily publish slot from cfg.publish_times, at least 1 hour from now."""
    tz = ZoneInfo(cfg.timezone)
    now = (now or datetime.now(tz)).astimezone(tz)
    taken_set = {t.astimezone(tz).replace(second=0, microsecond=0) for t in taken}
    slots = sorted(time.fromisoformat(s) for s in cfg.publish_times)
    day = now.date()
    for _ in range(366):
        for slot in slots:
            candidate = datetime.combine(day, slot, tzinfo=tz)
            if candidate >= now + timedelta(hours=1) and candidate not in taken_set:
                return candidate
        day += timedelta(days=1)
    raise RuntimeError("No free publish slot within a year.")


def upload(
    cfg: ChannelConfig,
    video: Path,
    title: str,
    description: str,
    tags: list[str],
    publish_at: datetime | None = None,
    thumbnail: Path | None = None,
    is_short: bool = False,
) -> str:
    """Upload and return the video id. With publish_at the video stays private until then."""
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload

    youtube = build("youtube", "v3", credentials=credentials(cfg))
    if is_short and "#shorts" not in description.lower():
        description = f"{description}\n\n#shorts"
    all_tags = list(dict.fromkeys([*tags, *cfg.default_tags]))
    # YouTube caps tags at 500 characters in total.
    while all_tags and sum(len(t) + 2 for t in all_tags) > 480:
        all_tags.pop()
    status = {
        "privacyStatus": "private" if publish_at else "public",
        "selfDeclaredMadeForKids": cfg.made_for_kids,
        "containsSyntheticMedia": True,  # AI voice/visuals disclosure
    }
    if publish_at:
        status["publishAt"] = publish_at.astimezone(ZoneInfo("UTC")).strftime("%Y-%m-%dT%H:%M:%SZ")
    body = {
        "snippet": {
            "title": title[:100],
            "description": description[:5000],
            "tags": all_tags,
            "categoryId": cfg.category_id,
            "defaultLanguage": cfg.language,
            "defaultAudioLanguage": cfg.language,
        },
        "status": status,
    }
    request = youtube.videos().insert(
        part="snippet,status",
        body=body,
        media_body=MediaFileUpload(str(video), chunksize=8 * 1024 * 1024, resumable=True),
    )
    response = None
    while response is None:
        progress, response = request.next_chunk()
        if progress:
            print(f"  upload {int(progress.progress() * 100)}%")
    video_id = response["id"]
    if thumbnail and thumbnail.exists():
        try:
            youtube.thumbnails().set(videoId=video_id, media_body=MediaFileUpload(str(thumbnail))).execute()
        except Exception as exc:  # custom thumbnails need a verified channel
            print(f"  thumbnail skipped: {exc}")
    return video_id
