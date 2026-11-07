"""Glow-up Shorts: an original cartoon character with a deadline, one small change a day, and the top comment
on yesterday's Short picks today's change.

Why this shape (2026-11-05): the owner pointed at a new Instagram page that got 115K-6.5M views on each of its
first 5 reels (142K followers). What carries it is the mechanics, not the drawing, so we reuse those and keep our
own character and premise:
  - one character, one deadline ("30 days to ...") so every episode has stakes;
  - a score bar on screen (days left, a % meter, Day N) that every episode moves;
  - the title is the outcome ("HE FINALLY SHOWERED"), and the set and the character never change;
  - the top comment on the last episode becomes the next episode (theirs: a 138K-like comment).

Draft: Claude writes the next episode from the series bible (config/series/<slug>.yaml), the story so far and the
top comment -> episode.json + script.json for the review PR. Render: render2d/ draws it in SVG with GSAP in
headless Chromium, the narrator is the channel voice, and the sound effects are made here.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Callable, Literal

import numpy as np
import yaml
from pydantic import BaseModel, Field

from .config import ROOT

RENDER2D = ROOT / "render2d"
SERIES_DIR = ROOT / "config" / "series"
SR = 44100
TITLE_SECONDS = 2.5     # the DAY N card (and yesterday's top comment) before the narrator starts
GAP = 0.18              # breath between narrator lines
ASK_SECONDS = 3.4       # the "what should he fix tomorrow?" card at the end

Mood = Literal["sleep", "sad", "shock", "neutral", "happy", "proud"]
Action = Literal["none", "alarm", "jolt", "glow"]
Place = Literal["bedroom", "bathroom", "gym", "shop", "kitchen", "barber", "outside"]


class Beat(BaseModel):
    text: str = Field(description="One narrator line, 3-9 words, plain spoken English. The last beat is the win.")
    mood: Mood = "neutral"
    action: Action = Field("none", description="glow on the beat where the meter goes up (exactly one per episode).")
    hl: list[str] = Field(default_factory=list, description="1-2 words from this line to colour yellow, upper case.")
    talk: bool = Field(False, description="True when the character himself says the line.")


class Episode(BaseModel):
    title: str = Field(description="The outcome in 2-5 words, upper case, past tense, e.g. 'HE WOKE UP BEFORE NOON'.")
    beats: list[Beat] = Field(description="4-6 beats, 12-18 seconds of narration in total.")
    glow_gain: float = Field(description="How much the meter rises today, 0.01-0.06. Bigger changes earn more.")
    place: Place = Field("bedroom", description="Where today's change happens; the set changes with it.")
    sign: str = Field(description="The sign gag he holds up, 'THING: VERDICT', max 18 characters, funny and kind, "
                      "e.g. 'BREATH: LEGAL', 'HAIR: SURRENDERED', 'SLEEP: 14 HOURS'.")
    sign_good: bool = Field(True, description="True for a green win sign, False for a red setback sign.")
    ask: str = Field(description="The closing question that invites tomorrow's comment, under 40 characters.")
    tags: list[str] = Field(default_factory=list)


def bible(slug: str) -> dict:
    return yaml.safe_load((SERIES_DIR / f"{slug}.yaml").read_text(encoding="utf-8"))


def state(out: Path) -> dict:
    """Where the series stands, from the approved episodes on disk (a drafts branch that was never merged
    leaves nothing on main): the last day, its meter, its folder and the story so far."""
    days = []
    for f in out.glob("*/episode.json"):
        ep = json.loads(f.read_text(encoding="utf-8"))
        ep["_folder"] = f.parent
        days.append(ep)
    if not days:
        return {"day": 0, "glow": 0.0, "story": [], "folder": None}
    days.sort(key=lambda e: e["day"])
    last = days[-1]
    return {"day": last["day"], "glow": last["glow"], "folder": last["_folder"],
            "story": [f"Day {e['day']}: {e['title']} ({e.get('place', 'bedroom')}; sign: {e.get('sign', '')})" for e in days]}


PENDING_DAYS = 3   # a drafted episode waits this long for approval before the day is drafted again


def daily(cfg, log=print) -> Path | None:
    """The autopilot's daily step for a series channel: draft the next episode once the last one is out.

    Day N+1 is only written after Day N is uploaded, so its top comment can pick the change. Returns the
    new script.json path, or None when there is nothing to do today (and says why)."""
    import os
    from datetime import date, datetime

    slug = cfg.series
    b, st = bible(slug), state(cfg.output_path)
    marker = ROOT / "topics" / f"{cfg.slug}.series.json"
    pending = json.loads(marker.read_text(encoding="utf-8")) if marker.exists() else {}
    if st["day"] >= b["days_total"]:
        log(f"[{cfg.slug}] the series is finished ({st['day']} days)")
        return None
    if pending.get("day", 0) > st["day"] and \
            (date.today() - date.fromisoformat(pending["drafted"])).days < PENDING_DAYS:
        log(f"[{cfg.slug}] Day {pending['day']} is waiting for approval; nothing new today")
        return None
    comment = None
    if st["day"]:
        meta_path = st["folder"] / "metadata.json"
        meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}
        rendered = meta.get("rendered_at")
        if not meta.get("video_id"):
            # Uploaded by hand (no video id here) or uploads not switched on: wait a day for a comment to be
            # read, then keep the series moving without one.
            if not rendered or (datetime.now() - datetime.fromisoformat(rendered)).days < 1:
                log(f"[{cfg.slug}] Day {st['day']} is not on YouTube yet; Day {st['day'] + 1} waits for its top comment")
                return None
        key = os.environ.get("YOUTUBE_API_KEY")
        if key and meta.get("video_id"):
            try:
                comment = top_comment(meta["video_id"], key, skip=tuple(b.get("skip_words", [])))
            except Exception as exc:  # no comment is fine: the bible's arc picks the change instead
                log(f"[{cfg.slug}] top comment unavailable: {exc}")
    day = st["day"] + 1
    folder = cfg.output_path / f"{datetime.now():%Y%m%d-%H%M%S}-short-day-{day:02d}"
    folder.mkdir(parents=True, exist_ok=True)
    data = draft(cfg, slug, folder, comment)
    (folder / "topic.txt").write_text(f"short\nDay {day}: {data['title']}\n", encoding="utf-8")
    marker.parent.mkdir(exist_ok=True)
    marker.write_text(json.dumps({"day": day, "drafted": date.today().isoformat()}), encoding="utf-8")
    log(f"[{cfg.slug}] Day {day}: {data['title']}" + (f" (from the comment \"{comment['text']}\")" if comment else ""))
    return folder / "script.json"


def top_comment(video_id: str, api_key: str, skip: tuple[str, ...] = ()) -> dict | None:
    """The most-liked top-level comment on a video (YouTube Data API, 1 quota unit)."""
    import requests

    r = requests.get("https://www.googleapis.com/youtube/v3/commentThreads", timeout=30, params={
        "part": "snippet", "videoId": video_id, "order": "relevance", "maxResults": 50, "textFormat": "plainText",
        "key": api_key})
    r.raise_for_status()
    best = None
    for it in r.json().get("items", []):
        c = it["snippet"]["topLevelComment"]["snippet"]
        text = " ".join(c["textDisplay"].split())
        if not text or len(text) > 140 or "http" in text or any(s in text.lower() for s in skip):
            continue
        if best is None or c.get("likeCount", 0) > best["likes_n"]:
            best = {"user": c.get("authorDisplayName", "viewer").lstrip("@")[:24], "text": text, "likes_n": c.get("likeCount", 0)}
    if best:
        n = best["likes_n"]
        best["likes"] = f"{n / 1000:.1f}K".replace(".0K", "K") if n >= 1000 else str(n)
    return best


def lint_episode(ep: dict) -> list[str]:
    """Free rule checks for a drafted episode (the Claude Code editor pass fixes what this lists)."""
    problems = []
    beats = ep.get("beats", [])
    if not 4 <= len(beats) <= 6:
        problems.append(f"{len(beats)} beats; write 4-6.")
    for i, b in enumerate(beats, 1):
        n = len(b["text"].split())
        if not 3 <= n <= 10:
            problems.append(f"Beat {i} has {n} words; keep each line 3-9 words: \"{b['text']}\"")
    glows = sum(b.get("action") == "glow" for b in beats)
    if glows != 1:
        problems.append(f"{glows} beats have action glow; exactly one (the win) should.")
    if not 2 <= len(ep.get("title", "").split()) <= 6:
        problems.append(f"Title \"{ep.get('title')}\" should be the outcome in 2-5 words.")
    sign = ep.get("sign", "")
    if ":" not in sign or len(sign) > 22:
        problems.append(f"Sign \"{sign}\" should read 'THING: VERDICT' in at most 18 characters.")
    if len(ep.get("ask", "")) > 40:
        problems.append("The closing question is over 40 characters.")
    if ep.get("comment") and not any(w.lower() in " ".join(b["text"] for b in beats).lower()
                                     for w in ep["comment"]["text"].split() if len(w) > 4):
        problems.append("The episode never answers yesterday's top comment; the first beat should name it.")
    return problems


def draft(cfg, slug: str, folder: Path, comment: dict | None = None) -> dict:
    from .script import VideoScript, _parse, save_script

    b, st = bible(slug), state(cfg.output_path)
    day = st["day"] + 1
    prompt = (f"Write Day {day} of {b['days_total']} of our original cartoon Shorts series.\n\n"
              f"Series bible:\n{yaml.safe_dump(b, allow_unicode=True)}\n"
              f"Story so far:\n" + ("\n".join(st["story"]) or "(this is the first episode)") +
              f"\nMeter now: {round(st['glow'] * 100)}%.\n" +
              (f"\nThe top comment on yesterday's episode, which today's change must answer: \"{comment['text']}\"\n"
               if comment else "") +
              "\nThe title is the outcome, as a big poster line ('HE TOUCHED GRASS'). Pick the place where the change "
              "happens. The sign is a deadpan label gag on the result. "
              "\nOne small, visible change today. Funny, warm, never cruel; he is likeable even at his worst. "
              "Narration is short spoken lines that land a joke or a turn every 3 seconds.")
    ep = _parse(cfg, prompt, Episode, max_tokens=3000)
    data = {"series": slug, "name": b["name"], "day": day, "days_total": b["days_total"], "meter": b["meter"],
            "premise": b["premise"], "glow_before": st["glow"], "glow": round(min(1.0, st["glow"] + ep.glow_gain), 3),
            "title": ep.title, "beats": [x.model_dump() for x in ep.beats], "comment": comment, "ask": ep.ask,
            "place": ep.place, "sign": ep.sign.upper()[:22], "sign_good": ep.sign_good,
            "seed": b.get("seed", 1)}
    (folder / "episode.json").write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    title = f"Day {day}: {ep.title.title()} | {b['premise'].title()}"
    save_script(VideoScript(title=title[:95], description=f"{b['premise'].capitalize()}. Day {day} of {b['days_total']}. "
                            "Comment what he should fix tomorrow: the top comment decides.\n\n#shorts #glowup",
                            tags=ep.tags + ["glow up", "animation", "shorts"], title_options=[], thumbnail_text="",
                            facts_to_check=[], scenes=[]), folder / "script.json")
    return data


# ---------- sound ----------
def _env(n: int, a: float, d: float) -> np.ndarray:
    t = np.arange(n) / SR
    return np.minimum(1, t / a) * np.exp(-t / d)


def _pop(f: float = 700) -> np.ndarray:
    n = int(.12 * SR); t = np.arange(n) / SR
    return np.sin(2 * np.pi * (f + 1800 * t) * t) * _env(n, .001, .035)


def _chime() -> np.ndarray:
    n = int(1.2 * SR); t = np.arange(n) / SR
    return sum(np.sin(2 * np.pi * f * t) * _env(n, .002, .35 + .1 * i) for i, f in enumerate((1318.5, 1568, 2093))) / 3


def _ring(dur: float) -> np.ndarray:
    n = int(dur * SR); t = np.arange(n) / SR
    return np.sin(2 * np.pi * 2400 * t) * (np.sin(2 * np.pi * 18 * t) > 0) * .5 * np.minimum(1, (dur - t) * 20)


def _whoosh(rng: np.random.Generator, dur: float = .3) -> np.ndarray:
    n = int(dur * SR); x = rng.standard_normal(n)
    y = np.convolve(x, np.ones(24) / 24, mode="same")
    return y * np.sin(np.linspace(0, np.pi, n)) ** 2


def _bed(n: int, rng: np.random.Generator) -> np.ndarray:
    """A light ukulele-ish pluck pattern so the Short is never silent between lines."""
    out = np.zeros(n); beat = 60 / 112 / 2
    prog = [(261.6, 329.6, 392.0), (220.0, 261.6, 329.6), (174.6, 220.0, 261.6), (196.0, 246.9, 293.7)]
    i = 0
    while i * beat * SR < n:
        chord = prog[(i // 8) % 4]; f = chord[i % 3] * (2 if i % 4 == 3 else 1)
        m = int(.4 * SR); t = np.arange(m) / SR
        s = (np.sin(2 * np.pi * f * t) + .3 * np.sin(4 * np.pi * f * t)) * _env(m, .003, .12)
        a = int(i * beat * SR); out[a:a + m] += s[: max(0, min(m, n - a))]
        i += 1
    return out * .06


def _place(buf: np.ndarray, t: float, sig: np.ndarray, gain: float = 1.0) -> None:
    a = int(t * SR); b = min(len(buf), a + len(sig))
    if a < len(buf):
        buf[a:b] += sig[: b - a] * gain


def _load(path: Path) -> np.ndarray:
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-f", "f32le", "-ac", "1", "-ar", str(SR), "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype="<f4").astype(np.float64)


def time_beats(ep: dict, lines: list[Path]) -> float:
    """Place each beat on the narrator's real line lengths; returns the episode length."""
    t = TITLE_SECONDS
    for b, f in zip(ep["beats"], lines):
        d = len(_load(f)) / SR
        b["t"], b["dur"] = round(t, 3), round(d + GAP, 3)
        t += d + GAP
    return round(t + ASK_SECONDS, 2)


def soundtrack(ep: dict, lines: list[Path], out: Path, seed: int = 1) -> Path:
    import wave

    rng = np.random.default_rng(seed)
    n = int(ep["duration"] * SR)
    voice, fx = np.zeros(n), np.zeros(n)
    for b, f in zip(ep["beats"], lines):
        _place(voice, b["t"], _load(f))
        _place(fx, b["t"] - .12, _whoosh(rng), .25)
        if b.get("action") == "alarm":
            _place(fx, b["t"], _ring(min(b["dur"], 1.6)), .12)
        if b.get("action") == "glow":
            _place(fx, b["t"], _chime(), .35)
        if b.get("action") == "jolt":
            _place(fx, b["t"], _pop(300), .5)
    _place(fx, .05, _pop(600), .5)
    _place(fx, ep["duration"] - ASK_SECONDS, _pop(900), .5)
    mix = voice + fx + _bed(n, rng)
    mix = mix / max(1e-9, np.abs(mix).max()) * .89
    pcm = (np.stack([mix, mix], axis=1) * 32767).astype("<i2")
    with wave.open(str(out), "wb") as w:          # stdlib only, so no extra dependency
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())
    return out


def render(folder: Path, synth: Callable[[str, Path], float], log=print) -> Path:
    """folder/episode.json -> folder/video.mp4 (1080x1920, 30 fps) with narration, effects and a light bed."""
    ep = json.loads((folder / "episode.json").read_text(encoding="utf-8"))
    work = folder / "work"; work.mkdir(exist_ok=True)
    lines = []
    for i, b in enumerate(ep["beats"]):
        p = work / f"line{i}.mp3"
        synth(b["text"], p)
        lines.append(p)
    ep["duration"] = time_beats(ep, lines)
    (work / "episode.json").write_text(json.dumps(ep), encoding="utf-8")
    log(f"  glow-up: day {ep['day']} '{ep['title']}' {ep['duration']} s")
    if not (RENDER2D / "node_modules").exists():
        raise RuntimeError("Run `npm install --prefix render2d` first.")
    subprocess.run(["node", str(RENDER2D / "capture.js"), str(work / "episode.json"), str(work / "picture.mp4")], check=True)
    soundtrack(ep, lines, work / "sound.wav", seed=ep.get("seed", 1) * 100 + ep["day"])
    video = folder / "video.mp4"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(work / "picture.mp4"), "-i", str(work / "sound.wav"),
                    "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-af", "loudnorm=I=-14:TP=-1.5", "-c:a", "aac",
                    "-b:a", "192k", "-shortest", "-movflags", "+faststart", str(video)], check=True)
    # the cover (DAY N + the outcome + the sign) is the first frame; keep it as the thumbnail too
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(work / "picture.mp4"), "-frames:v", "1", "-q:v", "3",
                    str(folder / "thumbnail.jpg")], check=True)
    ep_out = json.loads((folder / "episode.json").read_text(encoding="utf-8"))
    ep_out["duration"] = ep["duration"]
    (folder / "episode.json").write_text(json.dumps(ep_out, indent=2, ensure_ascii=False), encoding="utf-8")
    return video
