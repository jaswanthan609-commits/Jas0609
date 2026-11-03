# facepipe: faceless YouTube pipeline for three channels

Turns a topic into a finished, captioned YouTube video (long-form or Short), with a review step
before anything is rendered, then uploads it on a schedule and tracks each channel against its
monthly income target.

```
ideas ──► Claude script ──► YOU review + fact-check ──► voice ──► footage per scene
      ──► ffmpeg: clips + voice + captions + ducked music ──► thumbnail
      ──► YouTube upload (title, tags, scheduled slot) ──► stats vs target
```

## The three channels

One YAML file per channel in [`config/channels/`](config/channels):

| Channel | Config | Language | Voice | Footage | Target (base case, month 18) |
|---|---|---|---|---|---|
| AI Tools Explained | `ai-tools` | English, global | ElevenLabs | your screen recordings first, then stock | Rs 1.27 lakh/month |
| NRI Money Guide | `nri-money` | English, NRIs abroad | ElevenLabs | stock + charts | Rs 1.10 lakh/month |
| Paisa Simplified | `paisa-simplified` | Hindi, India | Sarvam Bulbul v3 | stock | Rs 0.80 lakh/month |

Change names, niches, voices, publish times and targets in those files. Add a channel by adding a
file. Tamil works too: set `language: ta`.

## Tools used

| Step | Tool | Cost |
|---|---|---|
| Script, title, tags, facts to check, topic ideas | Claude API (`claude-opus-5-5`) | about Rs 10-25 per script |
| Hindi/Tamil voice | [Sarvam Bulbul v3](https://docs.sarvam.ai/api-reference/text-to-speech/convert) | Rs 30 per 10,000 characters |
| English voice | [ElevenLabs](https://elevenlabs.io) | from $5/month |
| Free voice for testing | edge-tts (Microsoft neural voices) | free |
| Footage | your own clips, then [Pexels](https://www.pexels.com/api/), then [Pixabay](https://pixabay.com/api/docs/) | free |
| Assembly, captions, music ducking, loudness | ffmpeg + libass | free |
| Upload, scheduling, analytics | YouTube Data API v3 + YouTube Analytics API | free |

Ideas borrowed from [MoneyPrinterTurbo](https://github.com/harry0703/MoneyPrinterTurbo) (several
stock and voice providers), [OpenMontage](https://github.com/calesthio/OpenMontage) (approval
gates) and [youtube-automation-agent](https://github.com/darkzOGx/youtube-automation-agent)
(analytics feedback, fact checks).

## Setup

1. Install Python 3.11+ and ffmpeg with Noto fonts (`sudo apt install ffmpeg fonts-noto-core`,
   or `brew install ffmpeg` plus the fonts in [`assets/fonts`](assets/fonts/README.md)).
2. `pip install -r requirements.txt`
3. `cp .env.example .env` and add your keys. Only `ANTHROPIC_API_KEY` is needed to write scripts;
   the others switch on voice and footage.
4. Add royalty-free music to `assets/music/` (YouTube Audio Library is safest).
5. Check everything works with no keys at all:

```bash
python -m facepipe channels
python -m facepipe --channel paisa-simplified make --offline              # Short
python -m facepipe --channel paisa-simplified make --offline --format long
```

## Weekly workflow (per channel)

```bash
C="--channel nri-money"
python -m facepipe $C ideas --count 20 --save    # topic ideas -> topics/nri-money.txt
python -m facepipe $C batch --limit 3             # scripts for the next 3 topics (long-form)
python -m facepipe $C drafts                      # what's waiting for review
#   open each output/nri-money/<folder>/script.json, edit the narration, check every item in
#   facts_to_check, swap any visual_query, then set "reviewed": true
python -m facepipe $C render --reviewed --upload --schedule
python -m facepipe stats --all                    # last 28 days vs each channel's target
```

Other commands: `script "<topic>"` for one script, `render <script.json>` for one video,
`upload <folder> --publish-at 2026-11-08T18:30`, `make "<topic>" --no-review` to skip the review
(not recommended).

**Screen recordings (AI Tools channel):** save OBS recordings in `footage/ai-tools/` with
descriptive names (`chatgpt-custom-gpt-settings.mp4`). Scenes whose `visual_query` shares words
with a file name use that file; or set `"visual_query": "footage:chatgpt-custom-gpt-settings"` to
pick it exactly.

## YouTube setup

1. In [Google Cloud Console](https://console.cloud.google.com/), create a project and enable
   **YouTube Data API v3** and **YouTube Analytics API**.
2. Configure the OAuth consent screen (External; add yourself as a test user).
3. Create an OAuth client ID of type **Desktop app** and save it as `client_secret.json` here.
4. For each channel: `python -m facepipe --channel <name> auth` and pick that channel's account.

Until your Google Cloud project passes YouTube's
[API audit](https://support.google.com/youtube/contact/yt_api_form), uploads from it stay private.
Apply early; meanwhile upload `video.mp4` through YouTube Studio. The default quota allows about
6 uploads a day across all channels.

## Staying monetised

YouTube demonetises "inauthentic", mass-produced content and judges the whole channel by its
recent uploads. That is why `render` refuses scripts that are not marked reviewed. Edit every
script, check its facts, use your own recordings and examples where you can, and never publish
near-duplicates. Uploads are marked as containing synthetic (AI) voice.

## Layout

```
config/channels/*.yaml  one file per channel
facepipe/script.py      Claude: ideas and structured scripts (title, tags, facts_to_check, scenes)
facepipe/voice.py       Sarvam, ElevenLabs and edge-tts voiceover
facepipe/visuals.py     own footage, Pexels, Pixabay, offline placeholders
facepipe/captions.py    timed ASS captions for any script
facepipe/assemble.py    ffmpeg scene clips, concat, music ducking, loudness, thumbnail
facepipe/upload.py      YouTube OAuth per channel, resumable upload, scheduling
facepipe/stats.py       YouTube Analytics: views, watch hours, revenue, RPM vs target
facepipe/pipeline.py    draft -> review gate -> render -> publish
facepipe/__main__.py    CLI
tests/                  pytest, including an offline end-to-end render
```

Run tests with `pip install -r requirements-dev.txt && pytest`.
