import base64
import json
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from facepipe import pipeline, visuals, voice
from facepipe.captions import build_ass
from facepipe.config import list_channels, load_config
from facepipe.stats import report
from facepipe.upload import next_slot

TZ = ZoneInfo("Asia/Kolkata")
HAS_FFMPEG = shutil.which("ffmpeg") is not None


def test_three_english_channels_load():
    assert list_channels() == ["ai-tools", "kids-stories", "nri-money"]
    assert {load_config(c).language for c in list_channels()} == {"en"}
    kids = load_config("kids-stories")
    assert kids.made_for_kids and kids.visual_mode == "ai_images" and "Pip" in kids.characters
    assert kids.output_path.name == "kids-stories"
    assert load_config("ai-tools").footage_path.name == "ai-tools"


def test_kids_system_prompt_carries_characters_and_quality_rules():
    from facepipe.script import system_prompt

    text = system_prompt(load_config("kids-stories"))
    assert "image_prompt" in text and "orange fox cub" in text and "quality principles" in text
    assert "image_prompt" not in system_prompt(load_config("nri-money"))


def test_ai_image_request_and_response(tmp_path, monkeypatch):
    png = b"\x89PNG fake"
    sent = {}

    class Resp:
        def raise_for_status(self):
            pass

        def json(self):
            return {"outputs": [{"type": "text", "text": "ok"},
                                {"type": "image", "mime_type": "image/png", "data": base64.b64encode(png).decode()}]}

    def fake_post(url, json, headers, timeout):
        sent.update(url=url, body=json, headers=headers)
        return Resp()

    ref = tmp_path / "pip.png"
    ref.write_bytes(b"ref")
    monkeypatch.setenv("GEMINI_API_KEY", "g")
    monkeypatch.setattr(visuals.requests, "post", fake_post)
    cfg = load_config("kids-stories", character_refs=[str(ref)])
    out = visuals.ai_image(cfg, "Pip shares an apple", 1920, 1080, tmp_path / "scene")
    assert out.read_bytes() == png
    assert sent["headers"] == {"x-goog-api-key": "g"}
    assert sent["body"]["response_format"]["aspect_ratio"] == "16:9"
    assert [i["type"] for i in sent["body"]["input"]] == ["image", "text"]
    assert "watercolour" in sent["body"]["input"][-1]["text"]


def test_language_override_picks_matching_font():
    cfg = load_config("nri-money", language="ta")
    assert cfg.font_name == "Noto Sans Tamil"
    assert cfg.locale == "ta-IN"


def test_unknown_channel_and_language_rejected():
    with pytest.raises(ValueError):
        load_config("nope")
    with pytest.raises(ValueError):
        load_config("ai-tools", language="fr")


def test_next_slot_skips_taken_and_past_slots():
    cfg = load_config("nri-money", publish_times=["12:30", "18:30"])
    now = datetime(2026, 11, 3, 12, 0, tzinfo=TZ)  # 12:30 is under an hour away
    first = next_slot(cfg, [], now=now)
    assert first == datetime(2026, 11, 3, 18, 30, tzinfo=TZ)
    assert next_slot(cfg, [first], now=now) == datetime(2026, 11, 4, 12, 30, tzinfo=TZ)


def test_captions_cover_full_timeline(tmp_path):
    cfg = load_config("nri-money", language="hi")
    out = build_ass(cfg, [("नमस्ते दोस्तों आज हम पैसे की बात करेंगे", 4.0, "पैसा"), ("second scene text", 2.0, "")],
                    1080, 1920, tmp_path / "c.ass")
    text = out.read_text(encoding="utf-8")
    assert "Noto Sans Devanagari" in text
    assert "0:00:06.00" in text
    assert text.count("Headline,,") == 1


def test_split_keeps_pieces_under_limit():
    text = "पहला वाक्य है। " * 200
    pieces = voice._split(text, 300)
    assert all(len(p) <= 300 for p in pieces)
    assert "".join(pieces).replace(" ", "") == text.replace(" ", "")


def test_own_footage_matches_by_keywords(tmp_path):
    folder = tmp_path / "footage"
    folder.mkdir()
    for name in ["chatgpt-custom-gpt-settings.mp4", "notion-ai-summary.mp4", "notes.txt"]:
        (folder / name).write_bytes(b"x")
    cfg = load_config("ai-tools", footage_dir=str(folder))
    used = set()
    assert visuals.own_footage(cfg, "ChatGPT custom GPT settings page", used).name.startswith("chatgpt")
    assert visuals.own_footage(cfg, "footage:notion-ai-summary", used).name == "notion-ai-summary.mp4"
    assert visuals.own_footage(cfg, "sunset beach", used) is None


@pytest.mark.skipif(not HAS_FFMPEG, reason="ffmpeg not installed")
def test_sarvam_request_shape(tmp_path, monkeypatch):
    wav = tmp_path / "s.wav"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "anullsrc=r=22050:cl=mono",
                    "-t", "0.5", str(wav)], check=True)
    sent = []

    class Resp:
        def raise_for_status(self):
            pass

        def json(self):
            return {"request_id": "r", "audios": [base64.b64encode(wav.read_bytes()).decode()]}

    def fake_post(url, headers, json, timeout):
        sent.append((url, headers, json))
        return Resp()

    monkeypatch.setenv("SARVAM_API_KEY", "k")
    monkeypatch.setattr(voice.requests, "post", fake_post)
    cfg = load_config("nri-money", language="hi", voice_provider="sarvam", voice="ritu")
    seconds = voice.synthesize(cfg, "नमस्ते दोस्तों।", tmp_path / "v.mp3")
    url, headers, body = sent[0]
    assert url == "https://api.sarvam.ai/text-to-speech"
    assert headers == {"api-subscription-key": "k"}
    assert body["language_code"] == "hi-IN" and body["model"] == "bulbul:v3" and body["speaker"] == "ritu"
    assert 0.3 < seconds < 1.0


def test_stats_report_against_target():
    cfg = load_config("nri-money")  # target Rs 110,000
    text = report(cfg, {"start": "2026-10-01", "end": "2026-10-28", "views": 100000,
                        "estimatedMinutesWatched": 600000, "subscribersGained": 900, "subscribersLost": 100,
                        "estimatedRevenue": 55000.0})
    assert "RPM Rs 550" in text and "50% of target" in text and "200,000 a month" in text
    assert "not monetised" in report(cfg, {"start": "a", "end": "b", "views": 10})


@pytest.mark.skipif(not HAS_FFMPEG, reason="ffmpeg not installed")
def test_render_refuses_unreviewed_script(tmp_path):
    data = json.loads(pipeline.SAMPLE_SCRIPT.read_text(encoding="utf-8"))
    data["reviewed"] = False
    path = tmp_path / "script.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(pipeline.NotReviewed):
        pipeline.render(load_config("nri-money"), path, "short", offline=True)


@pytest.mark.skipif(not HAS_FFMPEG, reason="ffmpeg not installed")
@pytest.mark.parametrize("fmt,size", [("short", (1080, 1920)), ("long", (1920, 1080))])
def test_offline_end_to_end(tmp_path, fmt, size):
    cfg = load_config("kids-stories", output_dir=str(tmp_path), music_dir=str(tmp_path / "nomusic"))
    result = pipeline.make_offline(cfg, fmt, log=lambda *_: None)
    info = json.loads(subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,width,height", "-of", "json", str(result.video)],
        capture_output=True, text=True, check=True).stdout)
    video = next(s for s in info["streams"] if s["codec_type"] == "video")
    assert (video["width"], video["height"]) == size
    assert any(s["codec_type"] == "audio" for s in info["streams"])
    assert result.thumbnail.exists()
    with pytest.raises(RuntimeError, match="offline"):
        pipeline.publish(cfg, result, None)


def test_publish_approved_skips_already_published(tmp_path, monkeypatch):
    import facepipe.__main__ as cli

    out = tmp_path / "out"
    for name, meta in [("a", {"video_id": "abc"}), ("b", None)]:
        folder = out / name
        folder.mkdir(parents=True)
        shutil.copy(pipeline.SAMPLE_SCRIPT, folder / "script.json")
        if meta:
            (folder / "metadata.json").write_text(json.dumps(meta), encoding="utf-8")
    rendered = []
    monkeypatch.setattr(pipeline, "render", lambda cfg, path, require_review=True: rendered.append(path.parent.name))
    real_load = cli.load_config
    monkeypatch.setattr(cli, "load_config", lambda slug=None, **kw: real_load(slug, output_dir=str(out), **kw))
    cli.main(["--channel", "nri-money", "publish-approved"])
    assert rendered == ["b"]


def test_daily_tops_up_ideas_and_drafts(tmp_path, monkeypatch):
    import facepipe.__main__ as cli
    from facepipe import script as scriptmod

    monkeypatch.setattr(cli, "ROOT", tmp_path)
    monkeypatch.setattr(scriptmod, "generate_ideas", lambda cfg, n, avoid=None: [f"Topic {i}" for i in range(n)])
    drafted = []
    monkeypatch.setattr(pipeline, "draft_script", lambda cfg, topic, fmt: drafted.append((topic, fmt)))
    cli.main(["--channel", "ai-tools", "daily", "--long", "1", "--short", "1"])
    assert drafted == [("Topic 0", "long"), ("Topic 1", "short")]
    assert (tmp_path / "topics" / "ai-tools.done.txt").read_text().split("\n")[:2] == ["Topic 0", "Topic 1"]
