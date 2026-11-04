# facepipe: self-funding faceless YouTube pipeline

Turns a topic into a finished, captioned English YouTube video (long-form or Short), with a review step
before anything is rendered, then uploads it on a schedule and tracks each channel against its
monthly income target.

```
ideas ──► Claude script ──► YOU review + fact-check ──► voice ──► footage per scene
      ──► ffmpeg: clips + voice + captions + ducked music ──► thumbnail
      ──► YouTube upload (title, tags, scheduled slot) ──► stats vs target
```

## The channels (all English)

One YAML file per channel in [`config/channels/`](config/channels):

| Channel | Config | Viewers | Visuals | Main income | Target (base case, month 18) |
|---|---|---|---|---|---|
| AI Tools Explained | `ai-tools` | global, aim 30%+ US/UK | your screen recordings, then stock | ads + AI-tool affiliates | Rs 1.27 lakh/month |
| NRI Money Guide | `nri-money` | Indians abroad + global | stock footage + charts | ads + referrals | Rs 1.10 lakh/month |
| Moonlit Story Garden | `kids-stories` | children 3-7 (US/UK/global), Made for Kids | AI illustrations with recurring characters | ads (low RPM) + later licensing, books | Rs 0.60 lakh/month |
| Slow History for Sleep | `sleepy-history` | adults who fall asleep to calm videos (US/UK) | stock footage, 30-minute videos | ads (long watch time) | opens after $50 earned |

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
| `drafts.yml` | daily 06:00 IST | Runs `autopilot`: works out the money left, drafts only what today's budget allows (see below), saves the spending ledger, and opens a "Drafts for <date>" pull request listing each title and the facts to check |
| `publish.yml` | when you merge a drafts PR | Renders every merged script, uploads it into the next free slot (once `UPLOAD_ENABLED` is on), keeps the videos as a 7-day download, and records the video ids |
| `stats.yml` | Mondays | Views, watch hours and revenue per channel; saves earnings since the start to `ledger/revenue.json`, which tops up the budget |

Your daily job: open the drafts PR in the GitHub app, delete any script folder you would not
publish, tick the facts, merge. Merging is the approval.

After adding the secrets, run **Actions > Smoke test > Run workflow** once: it makes one real Short
without uploading (about $0.02) and checks YouTube and market data access. Download the video from
the run to judge the quality before the autopilot starts.

One-time setup (repository Settings):

1. **Secrets and variables > Actions > Secrets:** `ANTHROPIC_API_KEY`, `YOUTUBE_API_KEY`, `PEXELS_API_KEY`,
   `PIXABAY_API_KEY`, `GEMINI_API_KEY` (kids illustrations); later `YOUTUBE_CLIENT_SECRET_JSON`
   (the contents of client_secret.json) and one `YT_TOKEN_<CHANNEL>` per channel, e.g.
   `YT_TOKEN_AI_TOOLS`, `YT_TOKEN_SLEEPY_HISTORY` (the contents of tokens/<channel>.json after
   `auth` on your computer). A new channel needs only its secret, not a workflow change.
2. **Variables:** `UPLOAD_ENABLED` = `true` once the YouTube secrets are in.
3. **Actions > General:** allow GitHub Actions to create pull requests.
4. **Anthropic Console > Limits:** set a monthly spend limit as a safety net.

## Breakout engine

Most of a channel's views come from a few videos that break out. `python -m facepipe breakout --all`
runs every morning before drafting:

1. **Copy what is proven (weekly).** It searches YouTube for each channel's `research_queries` and
   ranks recent videos by views per subscriber. A video with 50x more views than its channel has
   subscribers proves the topic, not the channel's size. The top 15 go to `research/<channel>.json`,
   and Claude uses them as inspiration (same proven angle, our own take) when it writes topic ideas.
2. **Package for the click.** Every script comes with a title under 60 characters, 3 other title
   options listed in the drafts PR, thumbnail words that add to the title, and a first scene that
   pays off the title straight away.
3. **Double down on winners (daily).** When one of our videos reaches 3x the channel's median views
   after 2 days, Claude writes 3 follow-ups (part 2, a deeper dive, the next question) and they jump
   to the front of the topic queue.

Needs a free `YOUTUBE_API_KEY` secret (Google Cloud > APIs > Credentials > API key, with YouTube
Data API v3 enabled). Create the key in a **separate Google Cloud project** from the upload OAuth
client: quota is per project, uploads use most of it, and search uses about 1,400 units on Mondays.

Every script also passes a critic before it reaches you (`facepipe/critic.py`): a title too close
to an earlier video, or a Claude Haiku score under 7/10 for hook, specificity, originality or
policy risk, gets one rewrite with the critic's notes, then is dropped. Scores show in the drafts PR.

## Self-funding budget

[`config/autopilot.yaml`](config/autopilot.yaml) holds the one-time budget ($70) and the
channel plan. Each morning `autopilot`:

1. adds up money left = budget + earnings reinvested - money spent (every Claude call and AI
   image is logged with its cost in `ledger/spend.jsonl`; earnings come from YouTube Analytics);
2. spreads that over `runway_days`, so it never spends it all at once, and compares it with the
   last 7 days of spending;
3. drafts channels in order of priority, dropping a long video before a Short, and skipping
   channels that don't fit today;
4. opens a channel listed with `unlock_at_usd` once lifetime earnings pass that level.

When earnings stop, it slows down; when the money is gone, it stops until earnings come in.
Check it any time with `python -m facepipe budget`, or preview today's plan with
`python -m facepipe autopilot --dry-run`.

Budget profile: the channel configs use `claude-sonnet-5-5` for long scripts, `claude-haiku-5-5`
for Shorts and free edge-tts voices. Switch `voice_provider` to `elevenlabs` and `claude_model` to
`claude-opus-5-5` once the channels earn.

## Paper-trading test

[`trader/`](trader) is a separate test of whether an AI trading bot is worth real money. On
weekdays after the NSE close (`trade.yml`), Claude Haiku gets the day's prices and simple signals
for 14 cheap, liquid NSE stocks and ETFs ([`config/trader.yaml`](config/trader.yaml)), decides
orders, and they are filled at the next trading day's close (never the close Claude just saw) with fake money (Rs 7,000) and realistic Zerodha delivery
fees. Delivery only: no F&O, intraday, shorting or leverage.

It is scored against buying and holding the Nifty 50 ETF with the same Rs 7,000. After 30 days the
scorecard in `trading/report.md` says PASSED only if the bot beat holding the Nifty by 2+ points
after fees and never fell more than 15% from its peak. No real money moves; nothing connects to a
broker. Run it yourself with `python -m trader run` (one day) or `python -m trader report`.

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
facepipe/breakout.py    outlier research per niche, winner detection and follow-ups
facepipe/budget.py      spend ledger, earnings, daily plan that keeps within the money left
facepipe/ci.py          writes YouTube secrets for every channel in GitHub Actions
config/autopilot.yaml   budget, reinvestment and which channel drafts on which day
ledger/                 spending and earnings, committed by the workflows
trader/                 paper-trading bot (fake money, real prices and fees) vs holding the Nifty
trading/                its portfolio, journal and scorecard, committed by trade.yml
facepipe/pipeline.py    draft -> review gate -> render -> publish
facepipe/__main__.py    CLI
tests/                  pytest, including an offline end-to-end render
```

Run tests with `pip install -r requirements-dev.txt && pytest`.
