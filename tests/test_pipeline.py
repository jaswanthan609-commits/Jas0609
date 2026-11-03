import shutil
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from facepipe.captions import build_ass
from facepipe.config import load_config
from facepipe.upload import next_slot

TZ = ZoneInfo("Asia/Kolkata")


def test_config_defaults_and_language_override():
    cfg = load_config(language="ta")
    assert cfg.voice_name.startswith("ta-IN")
    assert cfg.font_name == "Noto Sans Tamil"


def test_config_rejects_unknown_language():
    with pytest.raises(ValueError):
        load_config(language="fr")


def test_next_slot_skips_taken_and_past_slots():
    cfg = load_config(publish_times=["12:30", "18:30"], timezone="Asia/Kolkata")
    now = datetime(2026, 11, 3, 12, 0, tzinfo=TZ)  # 12:30 is under an hour away
    first = next_slot(cfg, [], now=now)
    assert first == datetime(2026, 11, 3, 18, 30, tzinfo=TZ)
    second = next_slot(cfg, [first], now=now)
    assert second == datetime(2026, 11, 4, 12, 30, tzinfo=TZ)


def test_captions_cover_full_timeline(tmp_path):
    cfg = load_config(language="hi")
    out = build_ass(cfg, [("नमस्ते दोस्तों आज हम पैसे की बात करेंगे", 4.0, "पैसा"), ("second scene text", 2.0, "")],
                    1080, 1920, tmp_path / "c.ass")
    text = out.read_text(encoding="utf-8")
    assert "Noto Sans Devanagari" in text
    assert "0:00:06.00" in text  # last caption ends at total duration
    assert text.count("Headline,,") == 1


@pytest.mark.skipif(not shutil.which("ffmpeg"), reason="ffmpeg not installed")
@pytest.mark.parametrize("fmt,size", [("short", (1080, 1920)), ("long", (1920, 1080))])
def test_offline_end_to_end(tmp_path, fmt, size):
    import json, subprocess
    from facepipe.pipeline import make_video

    cfg = load_config(output_dir=str(tmp_path), music_dir=str(tmp_path / "nomusic"))
    result = make_video(cfg, None, fmt, offline=True, log=lambda *_: None)
    info = json.loads(subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,width,height", "-of", "json", str(result.video)],
        capture_output=True, text=True, check=True).stdout)
    video = next(s for s in info["streams"] if s["codec_type"] == "video")
    assert (video["width"], video["height"]) == size
    assert any(s["codec_type"] == "audio" for s in info["streams"])
    assert result.thumbnail.exists()
