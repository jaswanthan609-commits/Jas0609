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
    assert list_channels() == ["ai-tools", "cozy-hours", "kids-stories", "nri-money", "sleepy-history",
                               "what-really-happened"]
    assert load_config("sleepy-history").long_format == "sleep"
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
    # 2026-11-04 line-up from the cross-niche scan; NRI money paused.
    monday = budget.plan(ap, today=date(2026, 11, 9))
    assert monday.jobs == [("sleepy-history", 1, 0)]
    tuesday = budget.plan(ap, today=date(2026, 11, 10))
    assert tuesday.jobs == [("what-really-happened", 1, 1), ("cozy-hours", 1, 0)]
    sunday = budget.plan(ap, today=date(2026, 11, 15))
    assert sunday.jobs == [("cozy-hours", 1, 0)]
    assert budget.active_channels(ap) == ["sleepy-history", "what-really-happened", "cozy-hours"]
    assert "kids-stories" not in [ch.slug for ch in ap.channels]

    # Earnings gates still work if a channel sets one.
    ap.channels[0].unlock_at_usd = 50
    assert budget.plan(ap, today=date(2026, 11, 9)).jobs == []
    budget.save_revenue("nri-money", 60 * ap.usd_inr, "2026-11-04", "2026-12-20")
    assert ("sleepy-history", 1, 0) in budget.plan(ap, today=date(2026, 11, 9)).jobs
    assert budget.available(ap) == pytest.approx(130)


def test_budget_slows_down_and_stops():
    from datetime import date

    from facepipe import budget

    ap = _autopilot()
    from datetime import timedelta, timezone

    later = datetime.now(timezone.utc) + timedelta(days=10)  # the big spend was over a week ago
    budget.record("claude", "nri-money", 69.0)  # $1 left -> about $0.12 a week
    tight = budget.plan(ap, today=date(2026, 11, 10), now=later)
    # the expensive long video is dropped first; the Short and the near-free ambience video stay
    assert tight.jobs == [("what-really-happened", 0, 1), ("cozy-hours", 1, 0)]
    budget.record("claude", "nri-money", 5.0)
    broke = budget.plan(ap, today=date(2026, 11, 10), now=later)
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


# ---------- paper trader ----------

def _trader(tmp_path, monkeypatch):
    from trader import bot

    monkeypatch.setattr(bot, "DATA_DIR", tmp_path / "trading")
    return bot, bot.load_config()


def _history(prices: dict[str, float], days: int = 60) -> dict[str, list[float]]:
    return {t: [p * (0.9 + 0.1 * i / (days - 1)) for i in range(days)] for t, p in prices.items()}


def test_trader_fills_with_fees_and_refuses_bad_orders(tmp_path, monkeypatch):
    bot, cfg = _trader(tmp_path, monkeypatch)
    hist = _history({"NIFTYBEES.NS": 280, "ITC.NS": 420, "GOLDBEES.NS": 80})
    orders = [
        bot.Order(ticker="ITC.NS", action="buy", shares=5, reason="test"),       # Rs 2,100: under 35%
        bot.Order(ticker="GOLDBEES.NS", action="buy", shares=100, reason="x"),   # Rs 8,000: too much
        bot.Order(ticker="TSLA", action="buy", shares=1, reason="x"),            # not in universe
        bot.Order(ticker="SBIN.NS", action="sell", shares=1, reason="x"),        # not held
    ]
    from datetime import timedelta

    first = bot.run_day(cfg, hist, decide=lambda *a: bot.Decision(view="v", orders=orders), today=cfg.started)
    assert first["fills"] == [] and len(first["orders_for_next_day"]) == 4  # no look-ahead fills
    entry = bot.run_day(cfg, hist, decide=lambda *a: bot.Decision(view="v", orders=[]),
                        today=cfg.started + timedelta(days=1))
    status = [f["status"].split(":")[0] for f in entry["fills"]]
    assert status == ["rejected", "filled", "rejected", "rejected"]  # sells first, then buys in order
    state = json.loads((tmp_path / "trading" / "state.json").read_text())
    assert state["positions"]["ITC.NS"]["shares"] == 5
    assert state["cash"] == pytest.approx(7000 - 2100 * 1.0012, abs=0.01)
    assert state["benchmark"]["units"] == 24
    again = bot.run_day(cfg, hist, decide=lambda *a: 1 / 0, today=cfg.started + timedelta(days=1))
    assert again == {"skipped": "already ran today"}


def test_trader_sell_pays_flat_fee_and_verdict(tmp_path, monkeypatch):
    from datetime import timedelta

    bot, cfg = _trader(tmp_path, monkeypatch)
    hist = _history({"NIFTYBEES.NS": 280, "ITC.NS": 420})
    buy = [bot.Order(ticker="ITC.NS", action="buy", shares=5, reason="b")]
    sell = [bot.Order(ticker="ITC.NS", action="sell", shares=5, reason="s")]
    bot.run_day(cfg, hist, decide=lambda *a: bot.Decision(view="v", orders=buy), today=cfg.started)
    bot.run_day(cfg, hist, decide=lambda *a: bot.Decision(view="v", orders=sell), today=cfg.started + timedelta(days=1))
    later = cfg.started + timedelta(days=31)
    entry = bot.run_day(cfg, hist, decide=lambda *a: bot.Decision(view="v", orders=[]), today=later)
    assert entry["fills"][0]["fee"] == pytest.approx(2100 * 0.00105 + 15.93, abs=0.01)
    report = (tmp_path / "trading" / "report.md").read_text()
    assert "FAILED" in report  # round trip at the same price only loses fees
    assert bot.features(hist)["ITC.NS"]["rsi_14"] == 100.0


def test_critic_rewrites_then_drops_weak_scripts(tmp_path, monkeypatch):
    from facepipe import critic, script as scriptmod

    sample = scriptmod.load_script(pipeline.SAMPLE_SCRIPT)
    cfg = load_config("ai-tools", output_dir=str(tmp_path / "out"))
    writes = []
    monkeypatch.setattr(scriptmod, "write_script", lambda c, t, f, notes="": writes.append(notes) or sample)
    weak = critic.Critique(hook=4, specificity=8, originality=8, policy_risk=9, fixes=["Stronger first line"])
    strong = critic.Critique(hook=8, specificity=8, originality=8, policy_risk=9, fixes=[])
    verdicts = [weak, strong]
    monkeypatch.setattr(critic, "lint", lambda s, f="long": [])
    monkeypatch.setattr(critic, "critique", lambda c, s, f="long": verdicts.pop(0))
    path = pipeline.draft_script(cfg, "topic", "short", log=lambda *a: None)
    assert writes == ["", critic.notes_for_rewrite(weak)]
    assert json.loads((path.parent / "critic.json").read_text())["hook"] == 8

    # Same title again: duplicate, rewrite still duplicate -> dropped without spending on the critic.
    monkeypatch.setattr(critic, "critique", lambda c, s, f="long": 1 / 0)
    with pytest.raises(pipeline.Rejected):
        pipeline.draft_script(cfg, "topic", "short", log=lambda *a: None)


def test_duplicate_titles_detected():
    from facepipe.critic import duplicate_of

    assert duplicate_of("5 Free AI Tools That Save Hours!", ["5 free AI tools that save hours"])
    assert duplicate_of("How NRIs pay less tax in 2027", ["5 free AI tools that save hours"]) is None


def test_voice_falls_back_to_edge(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setitem(voice.PROVIDERS, "kokoro", lambda c, t, o: 1 / 0)
    monkeypatch.setattr(voice, "_edge", lambda c, t, o: calls.append(c.voice_name) or o.write_bytes(b""))
    monkeypatch.setattr(voice, "duration", lambda p: 1.5)
    cfg = load_config("ai-tools", voice_provider="kokoro", voice="am_michael", fallback_voice="en-US-AndrewNeural")
    assert voice.synthesize(cfg, "hi", tmp_path / "a.mp3") == 1.5
    assert calls == ["en-US-AndrewNeural"]


def test_affiliate_links_match_and_disclose():
    from facepipe import affiliate

    cfg = load_config("nri-money", affiliate_links=[
        {"label": "Wise", "url": "https://wise.example/ref", "keywords": ["send money"]},
        {"label": "Empty", "url": "", "always": True},
        {"label": "Other", "url": "https://other.example", "keywords": ["nre account"]},
    ])
    out = affiliate.with_links(cfg, "Hook line.\nSummary here.\n#nri", "How to send money home cheaply")
    lines = out.split("\n")
    assert lines[0] == "Hook line." and affiliate.DISCLOSURE in out
    assert "Wise: https://wise.example/ref" in out and "Empty" not in out and "Other" not in out
    assert out.index("Wise:") < out.index("Summary here.")
    # Nothing matches: description unchanged. Made for Kids: never any links.
    assert affiliate.with_links(cfg, "Hook.\nBody", "tax filing") == "Hook.\nBody"
    kids = load_config("kids-stories", affiliate_links=[{"label": "X", "url": "https://x", "always": True}])
    assert affiliate.with_links(kids, "Hook.", "anything") == "Hook."


def test_shipped_affiliate_links_start_empty():
    for slug in ["nri-money", "sleepy-history"]:
        cfg = load_config(slug)
        assert cfg.affiliate_links and all(link["url"] == "" for link in cfg.affiliate_links)


# --- 2026-11 rework: formats, lint, captions, chapters, scan, music ---

def test_new_channels_load():
    from facepipe.config import load_config

    for slug in ("sleepy-history", "what-really-happened", "cozy-hours"):
        cfg = load_config(slug)
        assert cfg.scan_topics
    assert load_config("sleepy-history").burn_captions is False


def test_lint_flags_greeting_and_passes_cold_open():
    from facepipe.critic import lint
    from facepipe.script import Scene, VideoScript

    def vs(first):
        return VideoScript(title="How a Poor Boy Beat Lay's in India", description="", tags=[], thumbnail_text="",
                           facts_to_check=[], scenes=[Scene(narration=first, visual_query="x"),
                                                      Scene(narration="In 2019 Ravi Kumar sold 40 packets.", visual_query="x")])
    assert any("greeting" in p for p in lint(vs("Welcome back to the channel, today we look at chips."), "story"))
    good = "At 4:12 in the morning in Indore, a 23-year-old made a call that would cost Lay's 900 crore rupees."
    assert lint(vs(good), "story") == []


def test_srt_and_chapters(tmp_path):
    from facepipe.captions import build_srt
    from facepipe.pipeline import with_chapters
    from facepipe.script import Scene

    timeline = [("one two three", 12.0, ""), ("four five", 15.0, ""), ("six", 20.0, ""), ("seven", 5.0, "")]
    srt = build_srt(timeline, tmp_path / "c.srt").read_text()
    assert srt.startswith("1\n00:00:00,000 --> ")
    scenes = [Scene(narration=n, visual_query="x", chapter=c) for (n, _, _), c in zip(timeline, ["Dawn", "Market", "Dusk", ""])]
    desc = with_chapters("About", scenes, timeline)
    assert "0:00 Dawn" in desc and "0:12 Market" in desc and "0:27 Dusk" in desc


def test_music_loops_seamlessly():
    import numpy as np

    from facepipe import music

    x = music.compose("D", "major", 70, bars=4, texture="rain_fire", seed=2)
    assert x.shape[1] == 2 and np.max(np.abs(x)) <= 1.0
    typical = np.abs(np.diff(x, axis=0)).mean()
    assert np.abs(x[-1] - x[0]).max() < 20 * typical + 0.05


def test_sample_credits_and_fallback(tmp_path, monkeypatch):
    """CC BY samples must be credited; without the sample sets the music falls back to synthesis."""
    monkeypatch.setenv("FACEPIPE_SAMPLES", str(tmp_path))
    from facepipe import music, samples

    assert not samples.available()
    assert any("Greg Sullivan" in c and "CC BY 3.0" in c for c in samples.credits())
    x = music.compose("F", "major", 72, bars=2, texture="none", seed=3, style="jazz")
    assert x.shape[1] == 2 and abs(x).max() <= 1.0


def test_lint_flags_ai_words():
    from facepipe.critic import lint
    from facepipe.script import Scene, VideoScript

    s = VideoScript(title="The Roman lamp", description="", tags=[], thumbnail_text="", facts_to_check=[], scenes=[
        Scene(narration="Rome's lamps are a testament to a vibrant, intricate tapestry of life.", visual_query="lamp")])
    assert any("AI-written" in p for p in lint(s, "sleep"))
