"""Script writing with the Claude API: topic ideas and full video scripts."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, Field

from .config import FORMATS, ChannelConfig


class Scene(BaseModel):
    narration: str = Field(description="What the voiceover says in this scene, in the channel language.")
    visual_query: str = Field(
        description="2-5 English keywords for stock footage search, e.g. 'indian rupee coins close up'."
    )
    on_screen_text: str = Field(default="", description="Optional short headline shown on screen.")
    image_prompt: str = Field(
        default="",
        description="Only for illustrated channels: a full English prompt for this scene's illustration.",
    )


class VideoScript(BaseModel):
    title: str = Field(description="YouTube title, under 90 characters, curiosity-driven, no clickbait lies.")
    description: str = Field(description="YouTube description with a hook line, summary and 3-5 hashtags.")
    tags: list[str] = Field(description="10-15 YouTube search tags, mixing channel language and English.")
    title_options: list[str] = Field(
        default_factory=list,
        description="3 other strong titles for the same video, each a different angle, for the reviewer to swap in.",
    )
    thumbnail_text: str = Field(description="2-4 punchy words for the thumbnail that add to the title, not repeat it.")
    facts_to_check: list[str] = Field(
        description="Every number, rule, date or claim in the narration that a human must verify before publishing."
    )
    scenes: list[Scene]
    reviewed: bool = Field(
        default=False,
        description="Always false. A human sets it to true after reading and fact-checking the script.",
    )


class TopicIdeas(BaseModel):
    topics: list[str]


SYSTEM = """You write scripts for a faceless YouTube channel.
Channel: {name}
Niche: {niche}
Audience: {audience}
Tone: {tone}
Language: write all narration, the title and the description in {language}. Use natural spoken
{language} the way a popular creator talks, not textbook language. Keep common English words
(like 'SIP', 'EMI', 'credit card') in English where locals would say them that way.
Visual queries are always English keywords, because stock libraries are searched in English.
Facts must be accurate. If a number is uncertain, say it approximately rather than inventing it.
Never promise guaranteed returns or give personalised financial or medical advice. For Indian
markets, stay educational: no specific buy or sell calls (SEBI rules for unregistered creators).
Make each video distinct: a specific angle, concrete examples and numbers, no filler or generic
intros. YouTube demonetises templated, mass-produced content, so avoid stock phrases.
Never put links or URLs in the description; the pipeline adds any links itself."""

FORMAT_BRIEF = {
    "short": (
        "a YouTube Short of about {seconds} seconds (roughly {words} spoken words). "
        "Open with a hook in the first 2 seconds that stops the scroll. Use 5-8 short scenes. "
        "It works as a trailer for the channel's long videos: end with one line inviting viewers to "
        "watch the full video on the channel."
    ),
    "long": (
        "a long-form YouTube video of about {minutes} minutes (roughly {words} spoken words). "
        "Open with a 15 second hook that promises the payoff, then deliver it in clear sections. "
        "Use 25-45 scenes of 10-20 seconds each. Ask viewers to subscribe once, mid-video."
    ),
    "deep": (
        "a calm, slow long-form YouTube video of about {minutes} minutes (roughly {words} spoken words) "
        "for people listening while falling asleep or relaxing. No hook, no cliffhangers, no calls to "
        "action except one gentle line at the start. Use 50-70 scenes of 25-40 seconds each, "
        "flowing chronologically, in a soft, even, descriptive tone."
    ),
}

PACKAGING = (
    " Packaging decides whether a video breaks out: the title and thumbnail earn the click, the first "
    "30 seconds keep the viewer. Title: under 60 characters, one clear promise or curiosity gap, specific "
    "(numbers, names, outcomes), and true to the video. The first scene must pay off the title's promise "
    "straight away: no greeting, no channel intro, no 'in this video'. Then keep giving viewers a reason "
    "to stay: tease what is coming next every minute or so."
)
FORMAT_BRIEF["short"] += PACKAGING
FORMAT_BRIEF["long"] += PACKAGING

WORDS_PER_SECOND = {"en": 2.5, "hi": 2.4, "ta": 2.0}
DEEP_PACE = 0.8  # deep videos are read slower


def _client():
    import anthropic

    return anthropic.Anthropic()


ILLUSTRATED = """
Every scene is shown as one illustration, so fill image_prompt for every scene: a complete,
self-contained English prompt describing the shot (who, what they are doing, setting, camera
angle, mood). Describe recurring characters exactly as in the character list every time they
appear, so they look the same in every image. No text or letters inside the images.
Art style for every image: {style}
Recurring characters:
{characters}"""


def system_prompt(cfg: ChannelConfig) -> str:
    text = SYSTEM.format(
        name=cfg.name, niche=cfg.niche, audience=cfg.audience, tone=cfg.tone, language=cfg.language_name
    )
    if cfg.visual_mode == "ai_images":
        text += ILLUSTRATED.format(style=cfg.image_style or "consistent", characters=cfg.characters or "none")
    if cfg.extra_guidelines:
        text += "\n\nChannel rules:\n" + cfg.extra_guidelines.strip()
    return text


# Models that accept the server-side refusal fallback (`fallbacks: "default"`).
FALLBACK_MODELS = {"claude-fable-5-1", "claude-opus-5-5", "claude-opus-5", "claude-sonnet-5-5"}


def _parse(cfg: ChannelConfig, prompt: str, schema: type[BaseModel], max_tokens: int = 16000, model: str | None = None):
    client = _client()
    model = model or cfg.claude_model
    extra = {}
    if model in FALLBACK_MODELS:
        # Server-side fallback: if a safety classifier declines, the API retries on a suitable model.
        extra = {"betas": ["server-side-fallback-2026-07-01"], "fallbacks": "default"}
    response = client.beta.messages.parse(
        model=model,
        max_tokens=max_tokens,
        system=system_prompt(cfg),
        messages=[{"role": "user", "content": prompt}],
        output_config={"effort": cfg.claude_effort},
        output_format=schema,
        # Long outputs exceed the SDK's default non-streaming limit; an explicit timeout allows them.
        timeout=1800 if max_tokens > 16000 else 600,
        **extra,
    )
    from . import budget

    served = getattr(response, "model", None) or model
    budget.record("claude", cfg.slug, budget.claude_cost(served, response.usage), model=served,
                  schema=schema.__name__, tokens_in=response.usage.input_tokens,
                  tokens_out=response.usage.output_tokens)
    if response.stop_reason == "refusal":
        raise RuntimeError(f"Claude declined this request: {response.stop_details}")
    if response.stop_reason == "max_tokens":
        raise RuntimeError("Script was cut off by max_tokens; raise it or shorten the format.")
    return response.parsed_output


def generate_ideas(
    cfg: ChannelConfig, count: int = 20, avoid: list[str] | None = None, inspiration: str = ""
) -> list[str]:
    avoid_text = ""
    if avoid:
        avoid_text = "\nDo not repeat these topics we already covered:\n- " + "\n- ".join(avoid[-150:])
    proven = ""
    if inspiration:
        proven = (
            "\nThese recent videos in our niche got far more views than their channels' size, so their "
            "topics and angles are proven to pull viewers:\n" + inspiration + "\nAt least half of the "
            "topics should use one of these proven angles with our own original take: a different example, "
            "a newer update, a deeper answer or the opposite view. Never copy a title."
        )
    prompt = (
        f"Give {count} specific video topics for this channel that people actively search for "
        f"and that suit a faceless format. Write each topic as a one-line working title in "
        f"{cfg.language_name}.{proven}{avoid_text}"
    )
    return _parse(cfg, prompt, TopicIdeas, max_tokens=4000).topics


def follow_up_topics(cfg: ChannelConfig, title: str, views: int, median: float, count: int = 3) -> list[str]:
    """Topics that ride a video of ours that took off."""
    prompt = (
        f"Our video \"{title}\" got {views:,} views, {views / max(median, 1):.0f}x our usual. Give {count} "
        f"follow-up video topics for the same viewers: a sequel or part 2, a deeper dive into the most "
        f"interesting part, and the next question these viewers will ask. Each must stand on its own. "
        f"Write each as a one-line working title in {cfg.language_name}."
    )
    return _parse(cfg, prompt, TopicIdeas, max_tokens=4000).topics


def write_script(cfg: ChannelConfig, topic: str, fmt: str = "short", notes: str = "") -> VideoScript:
    _, _, seconds = FORMATS[fmt]
    words = int(seconds * WORDS_PER_SECOND[cfg.language] * (DEEP_PACE if fmt == "deep" else 1))
    brief = FORMAT_BRIEF[fmt].format(seconds=seconds, minutes=round(seconds / 60), words=words)
    prompt = f"Write {brief}\n\nTopic: {topic}" + (f"\n\n{notes}" if notes else "")
    model = (cfg.claude_model_short or cfg.claude_model) if fmt == "short" else cfg.claude_model
    max_tokens = 32000 if fmt == "deep" else 16000
    return _parse(cfg, prompt, VideoScript, model=model, max_tokens=max_tokens)


def save_script(script: VideoScript, path: Path) -> None:
    path.write_text(script.model_dump_json(indent=2), encoding="utf-8")


def load_script(path: Path) -> VideoScript:
    return VideoScript.model_validate(json.loads(path.read_text(encoding="utf-8")))
