# facepipe: faceless YouTube video pipeline

Turns a topic into a finished, captioned YouTube Short or long-form video and uploads it on a
schedule. English, Tamil and Hindi are supported.

```
topic ──► Claude writes script ──► neural voiceover ──► stock footage per scene
      ──► ffmpeg: clips + voice + burned captions + ducked music ──► thumbnail
      ──► YouTube upload (title, description, tags, scheduled publish)
```

| Step | Tool | Cost |
|---|---|---|
| Script, title, tags, topic ideas | Claude API (`claude-opus-5-5`) | a few rupees per script |
| Voiceover | [edge-tts](https://github.com/rany2/edge-tts) Microsoft neural voices | free |
| Visuals | [Pexels API](https://www.pexels.com/api/) stock video, photo fallback | free |
| Assembly, captions, music | ffmpeg + libass | free |
| Upload and scheduling | YouTube Data API v3 | free (quota: about 6 uploads/day by default) |

## Setup

1. Install Python 3.11+ and ffmpeg (`sudo apt install ffmpeg fonts-noto-core`, or `brew install ffmpeg`).
2. `pip install -r requirements.txt`
3. `cp .env.example .env` and add your `ANTHROPIC_API_KEY` ([console](https://platform.claude.com/))
   and `PEXELS_API_KEY`.
4. Edit [`config/channel.yaml`](config/channel.yaml): channel name, niche, language (`en`, `ta`,
   `hi`), tone, publish times.
5. Add a few royalty-free music tracks to `assets/music/` (YouTube Audio Library is safest).
6. Tamil/Hindi captions need Noto fonts; see [`assets/fonts/README.md`](assets/fonts/README.md).

Check everything works without any keys:

```bash
python -m facepipe make --offline            # Short, 1080x1920
python -m facepipe make --offline --format long
```

Output lands in `output/<timestamp>-<format>-<slug>/` with `video.mp4`, `thumbnail.jpg`,
`script.json` and `metadata.json`.

## Making videos

```bash
# 20 topic ideas for your niche, appended to topics.txt
python -m facepipe ideas --count 20 --save

# One Short from a topic
python -m facepipe make "SIP vs FD: which is better in 2026?"

# Same topic, Tamil long-form
python -m facepipe make "SIP vs FD" --format long --language ta

# Edit output/<folder>/script.json by hand, then re-render from it
python -m facepipe make --script output/<folder>/script.json

# Work through topics.txt, 5 at a time (finished topics go to topics.done.txt)
python -m facepipe batch --limit 5
```

## Uploading to YouTube

One-time setup:

1. In [Google Cloud Console](https://console.cloud.google.com/), create a project and enable
   **YouTube Data API v3**.
2. Configure the OAuth consent screen (External, add yourself as a test user).
3. Create an OAuth client ID of type **Desktop app**, download it as `client_secret.json` into
   this folder.
4. `python -m facepipe auth` opens a browser; sign in with the channel's Google account.

Then:

```bash
python -m facepipe make "Credit card mistakes" --upload --schedule   # next free slot from publish_times
python -m facepipe batch --limit 3 --upload --schedule              # fills the next 3 slots
python -m facepipe upload output/<folder> --publish-at 2026-11-08T18:30
```

Scheduled videos upload as private and go public at the slot time. Videos are marked as
containing synthetic media (AI voice), which YouTube requires for realistic AI content.

**Important:** until your Google Cloud project passes YouTube's
[API compliance audit](https://support.google.com/youtube/contact/yt_api_form), uploads from an
unverified project are locked to private. Apply as soon as the channel is set up, or upload the
rendered `video.mp4` through YouTube Studio meanwhile.

## Staying monetisable

YouTube's Partner Program demonetises "inauthentic" and "reused" content: mass-produced videos
that differ only slightly, or stock clips with a robotic voice and no added value. To stay safe:

- Review and edit every script (`script.json`) before rendering; add your own angle or examples.
- Keep topics specific and useful; don't publish near-duplicate videos.
- Swap stock clips that don't match the narration (rerun with an edited `visual_query`).
- Use a consistent voice, style and intro so the channel has an identity.

## Layout

```
config/channel.yaml     channel settings
facepipe/script.py      Claude: topic ideas, structured scripts (title, tags, scenes)
facepipe/voice.py       edge-tts voiceover (en/ta/hi voices)
facepipe/visuals.py     Pexels stock video/photo download, offline placeholders
facepipe/captions.py    timed ASS captions, any script
facepipe/assemble.py    ffmpeg scene clips, concat, music ducking, loudness, thumbnail
facepipe/upload.py      YouTube OAuth, resumable upload, scheduling
facepipe/pipeline.py    end-to-end orchestration
facepipe/__main__.py    CLI
tests/                  pytest (offline end-to-end render included)
```

Run tests with `pip install -r requirements-dev.txt && pytest`.
