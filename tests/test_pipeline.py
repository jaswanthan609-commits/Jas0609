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


@pytest.fixture(autouse=True)
def isolated_ledger(tmp_path, monkeypatch):
    """Keep test spending out of the real ledger/."""
    from facepipe import budget

    monkeypatch.setattr(budget, "LEDGER_DIR", tmp_path / "ledger")
    from facepipe import breakout

    monkeypatch.setattr(breakout, "RESEARCH_DIR", tmp_path / "research")


def test_english_channels_load():
    assert list_channels() == ["ai-tools", "kids-stories", "nri-money", "sleepy-history"]
    assert load_config("sleepy-history").long_format == "deep"
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
    from facepipe import budget

    assert [e["kind"] for e in budget.spend_entries()] == ["image"]


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
    monkeypatch.setattr(scriptmod, "generate_ideas", lambda cfg, n, avoid=None, **kw: [f"Topic {i}" for i in range(n)])
    drafted = []
    monkeypatch.setattr(pipeline, "draft_script", lambda cfg, topic, fmt: drafted.append((topic, fmt)))
    cli.main(["--channel", "ai-tools", "daily", "--long", "1", "--short", "1"])
    assert drafted == [("Topic 0", "long"), ("Topic 1", "short")]
    assert (tmp_path / "topics" / "ai-tools.done.txt").read_text().split("\n")[:2] == ["Topic 0", "Topic 1"]


def _autopilot(**kw):
    from facepipe import budget

    ap = budget.load()
    for k, v in kw.items():
        setattr(ap, k, v)
    return ap


def test_budget_plan_by_weekday_and_unlock():
    from datetime import date

    from facepipe import budget

    ap = _autopilot()
    monday = budget.plan(ap, today=date(2026, 11, 9))
    assert monday.jobs == [("ai-tools", 1, 1), ("nri-money", 1, 1), ("kids-stories", 1, 1)]
    tuesday = budget.plan(ap, today=date(2026, 11, 10))
    assert [j[0] for j in tuesday.jobs] == ["ai-tools", "nri-money"]
    assert any("sleepy-history: locked" in n for n in tuesday.notes)

    budget.save_revenue("ai-tools", 60 * ap.usd_inr, "2026-11-04", "2026-12-20")
    unlocked = budget.plan(ap, today=date(2026, 11, 10))
    assert ("sleepy-history", 1, 0) in unlocked.jobs
    assert budget.available(ap) == pytest.approx(130)


def test_budget_slows_down_and_stops():
    from datetime import date

    from facepipe import budget

    ap = _autopilot()
    from datetime import timedelta, timezone

    later = datetime.now(timezone.utc) + timedelta(days=10)  # the big spend was over a week ago
    budget.record("claude", "ai-tools", 66.0)  # $4 left -> about $0.47 a week
    tight = budget.plan(ap, today=date(2026, 11, 9), now=later)
    assert ("ai-tools", 1, 1) in tight.jobs
    assert all(slug != "kids-stories" or n_long == 0 for slug, n_long, _ in tight.jobs)
    budget.record("claude", "ai-tools", 5.0)
    broke = budget.plan(ap, today=date(2026, 11, 9), now=later)
    assert broke.jobs == [] and "out of money" in broke.notes[-1]


def test_claude_cost_from_usage():
    from types import SimpleNamespace

    from facepipe import budget

    usage = SimpleNamespace(input_tokens=1_000_000, output_tokens=100_000)
    assert budget.claude_cost("claude-sonnet-5-5", usage) == pytest.approx(3.0)
    assert budget.claude_cost("claude-haiku-5-5", usage) == pytest.approx(0.15)


def test_ci_writes_token_per_channel(tmp_path, monkeypatch):
    import facepipe.ci as ci

    monkeypatch.setattr(ci, "ROOT", tmp_path)
    monkeypatch.setenv("SECRETS_JSON", json.dumps({"YT_TOKEN_SLEEPY_HISTORY": "{}", "YOUTUBE_CLIENT_SECRET_JSON": "{}"}))
    ci.main()
    assert (tmp_path / "tokens" / "sleepy-history.json").exists() and (tmp_path / "client_secret.json").exists()


def _fake_youtube(monkeypatch, videos, subs):
    from facepipe import breakout

    def fake_get(path, **params):
        if path == "search":
            return {"items": [{"id": {"videoId": v}} for v in videos]}
        if path == "videos":
            ids = params["id"].split(",")
            return {"items": [{"id": i, "snippet": {"title": videos[i][0], "channelId": videos[i][1],
                                                    "publishedAt": videos[i][3]},
                               "statistics": {"viewCount": str(videos[i][2])}} for i in ids if i in videos]}
        if path == "channels":
            return {"items": [{"id": c, "statistics": {"subscriberCount": str(n)}} for c, n in subs.items()]}
        raise AssertionError(path)

    monkeypatch.setattr(breakout, "_get", fake_get)


def test_outliers_rank_by_views_per_subscriber(monkeypatch):
    from facepipe import breakout

    old = "2026-10-01T00:00:00Z"
    _fake_youtube(monkeypatch, {"a": ("Big channel hit", "c1", 900_000, old), "b": ("Small channel breakout", "c2", 400_000, old)},
                  {"c1": 2_000_000, "c2": 5_000})
    cfg = load_config("ai-tools")
    found = breakout.find_outliers(cfg)
    assert [o["id"] for o in found] == ["b", "a"] and found[0]["score"] == 80.0
    breakout.save_outliers(cfg, found)
    assert not breakout.outliers_stale(cfg)
    assert '"Small channel breakout": 400,000 views on a channel with 5,000 subscribers' in breakout.inspiration_text(found)


def test_winner_gets_follow_ups_first(tmp_path, monkeypatch):
    import facepipe.__main__ as cli
    from facepipe import breakout, script as scriptmod

    monkeypatch.setattr(cli, "ROOT", tmp_path)
    monkeypatch.setenv("YOUTUBE_API_KEY", "k")
    cfg = load_config("nri-money", output_dir=str(tmp_path / "out"))
    monkeypatch.setattr(cli, "load_config", lambda slug=None, **kw: cfg)
    old = "2026-10-01T00:00:00Z"
    videos = {}
    for i, views in enumerate([100, 120, 90, 5000]):
        folder = tmp_path / "out" / f"v{i}"
        folder.mkdir(parents=True)
        (folder / "metadata.json").write_text(json.dumps({"video_id": f"v{i}", "format": "long"}))
        videos[f"v{i}"] = (f"Video {i}", "me", views, old)
    _fake_youtube(monkeypatch, videos, {"me": 50})
    monkeypatch.setattr(breakout, "outliers_stale", lambda c: False)
    asked = []
    monkeypatch.setattr(scriptmod, "follow_up_topics", lambda c, t, v, m: asked.append(t) or ["Part 2", "Deeper"])
    topics = tmp_path / "topics" / "nri-money.txt"
    topics.parent.mkdir()
    topics.write_text("Old topic\n")
    cli.main(["--channel", "nri-money", "breakout"])
    assert asked == ["Video 3"]
    assert topics.read_text().splitlines()[:3] == ["Part 2", "Deeper", "Old topic"]
    cli.main(["--channel", "nri-money", "breakout"])  # already followed up: nothing new
    assert asked == ["Video 3"]


def test_ideas_prompt_uses_breakout_inspiration(monkeypatch):
    from facepipe import script as scriptmod

    seen = {}
    monkeypatch.setattr(scriptmod, "_parse", lambda cfg, prompt, schema, max_tokens=0, model=None: seen.update(p=prompt) or scriptmod.TopicIdeas(topics=["x"]))
    scriptmod.generate_ideas(load_config("ai-tools"), 5, inspiration='- "Hit": 1 views')
    assert "proven angles" in seen["p"] and '"Hit"' in seen["p"]
