# facepipe: faceless YouTube pipeline for three channels

Turns a topic into a finished, captioned English YouTube video (long-form or Short), with a review step
before anything is rendered, then uploads it on a schedule and tracks each channel against its
monthly income target.

```
ideas ──► Claude script ──► YOU review + fact-check ──► voice ──► footage per scene
      ──► ffmpeg: clips + voice + captions + ducked music ──► thumbnail
      ──► YouTube upload (title, tags, scheduled slot) ──► stats vs target
```

## The three channels (all English)

One YAML file per channel in [`config/channels/`](config/channels):

| Channel | Config | Viewers | Visuals | Main income | Target (base case, month 18) |
|---|---|---|---|---|---|
| AI Tools Explained | `ai-tools` | global, aim 30%+ US/UK | your screen recordings, then stock | ads + AI-tool affiliates | Rs 1.27 lakh/month |
| NRI Money Guide | `nri-money` | Indians abroad + global | stock footage + charts | ads + referrals | Rs 1.10 lakh/month |
| Moonlit Story Garden | `kids-stories` | children 3-7 (US/UK/global), Made for Kids | AI illustrations with recurring characters | ads (low RPM) + later licensing, books | Rs 0.60 lakh/month |

Change names, niches, voices, characters, publish times and targets in those files. Add a channel
by adding a file. Hindi and Tamil still work (`language: hi` / `ta`, `voice_provider: sarvam`).

**Kids channel rules:** it is marked Made for Kids (required by law for content aimed at
children: no personalised ads, comments off). YouTube removes low-quality kids channels from the
Partner Program, so its config tells Claude to follow YouTube's quality principles: one real lesson
per story, kindness, no pranks or scary scenes, no product pushing, original stories only.
Generate one reference picture per character once, save it in `assets/characters/`, and list it
under `character_refs` so the characters look the same in every video.

## Tools used

| Step | Tool | Cost |
|---|---|---|
| Script, title, tags, facts to check, topic ideas | Claude API (`claude-opus-5-5`) | about Rs 10-25 per script |
| Hindi/Tamil voice | [Sarvam Bulbul v3](https://docs.sarvam.ai/api-reference/text-to-speech/convert) | Rs 30 per 10,000 characters |
| English voice | [ElevenLabs](https://elevenlabs.io) | from $5/month |
| Free voice for testing | edge-tts (Microsoft neural voices) | free |
| Footage | your own clips, then [Pexels](https://www.pexels.com/api/), then [Pixabay](https://pixabay.com/api/docs/) | free |
| Illustrations (kids channel) | [Google Nano Banana](https://ai.google.dev/gemini-api/docs/image-generation) image model, with character reference images | a few rupees per image |
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
python -m facepipe --channel kids-stories make --offline                  # Short
python -m facepipe --channel kids-stories make --offline --format long
```

## Weekly workflow (per channel)

```bash
C="--channel kids-stories"
python -m facepipe $C ideas --count 20 --save    # topic ideas -> topics/kids-stories.txt
python -m facepipe $C batch --limit 3             # scripts for the next 3 topics (long-form)
python -m facepipe $C drafts                      # what's waiting for review
#   open each output/kids-stories/<folder>/script.json, edit the narration, check every item in
#   facts_to_check, adjust any image_prompt or visual_query, then set "reviewed": true
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

## Autopilot on GitHub (5 minutes a day from your phone)

Three workflows in [`.github/workflows`](.github/workflows) run everything without your computer:

| Workflow | When | What it does |
|---|---|---|
| `drafts.yml` | daily 06:00 IST | Tops up topic ideas, drafts today's scripts (AI tools and NRI money: 1 long + 1 Short each; kids: 1 story on Monday, Shorts Mon/Wed/Fri) and opens a "Drafts for <date>" pull request listing each title and the facts to check |
| `publish.yml` | when you merge a drafts PR | Renders every merged script, uploads it into the next free slot (once `UPLOAD_ENABLED` is on), keeps the videos as a 7-day download, and records the video ids |
| `stats.yml` | Mondays | Views, watch hours, revenue and RPM against each channel's target, on the run's summary page |

Your daily job: open the drafts PR in the GitHub app, delete any script folder you would not
publish, tick the facts, merge. Merging is the approval.

One-time setup (repository Settings):

1. **Secrets and variables > Actions > Secrets:** `ANTHROPIC_API_KEY`, `PEXELS_API_KEY`,
   `PIXABAY_API_KEY`, `GEMINI_API_KEY` (kids illustrations); later `YOUTUBE_CLIENT_SECRET_JSON`
   (the contents of client_secret.json) and `YT_TOKEN_AI_TOOLS`, `YT_TOKEN_NRI_MONEY`,
   `YT_TOKEN_KIDS_STORIES` (the contents of tokens/<channel>.json after `auth` on your computer).
2. **Variables:** `UPLOAD_ENABLED` = `true` once the YouTube secrets are in.
3. **Actions > General:** allow GitHub Actions to create pull requests.

Budget profile: the channel configs use `claude-sonnet-5-5` for long scripts, `claude-haiku-5-5`
for Shorts and free edge-tts voices, which keeps the whole run near $40 for 90 days. Switch
`voice_provider` to `elevenlabs` and `claude_model` to `claude-opus-5-5` once the channels earn.

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
facepipe/visuals.py     own footage, Pexels, Pixabay, AI illustrations, offline placeholders
facepipe/captions.py    timed ASS captions for any script
facepipe/assemble.py    ffmpeg scene clips, concat, music ducking, loudness, thumbnail
facepipe/upload.py      YouTube OAuth per channel, resumable upload, scheduling
facepipe/stats.py       YouTube Analytics: views, watch hours, revenue, RPM vs target
facepipe/pipeline.py    draft -> review gate -> render -> publish
facepipe/__main__.py    CLI
tests/                  pytest, including an offline end-to-end render
```

Run tests with `pip install -r requirements-dev.txt && pytest`.
