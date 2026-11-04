---
name: outlier-scan
description: Decide what to make next from data, not guesses. Use before picking a niche, a channel, a series or a batch of topics, or when asked "what is working on YouTube".
---

# Outlier scan

The rule this project learned the hard way (2026-11-04): a plan built on assumptions got skipped by
the owner; the one built on a 3,700-video pull found 4.7M-view breakouts on channels a month old.
Never propose a niche, format or topic without numbers from YouTube behind it.

## Steps

1. Read `research/scan.json` (weekly, `python -m facepipe scan`). If it is older than 7 days and
   `YOUTUBE_API_KEY` is set, run `python -m facepipe scan --force` first (about 4,100 of 10,000 daily
   quota units).
2. An outlier is: views >= 100K, views per subscriber >= 5, channel under 100K subscribers. Young =
   channel under a year old. Rank areas by young + long outliers, not by total views: big channels
   prove nothing about what a new channel can do.
3. For an area, read its outliers: length (median minutes), title shapes, upload dates, channel ages.
   Write down the pattern in one line per point (format, length, angle, packaging).
4. Check the policy risk before recommending: reused content, mass-produced or AI-slop signals, kids,
   finance advice (SEBI/SEC), medical claims. Note anti-AI sentiment ("NO AI" titles).
5. Recommend with the evidence inline: "X: N young outliers, median M min, top: <title> (<views> on
   <subs> subs)". If the data is thin (fewer than 5 outliers), say so and widen the seeds in
   `config/scan.yaml` rather than guessing.
6. To act on it: add the area's seeds to a channel's `scan_topics`, so breakout ideas and the hook
   library (`research/hooks.json`) follow it automatically.

Related: `/yt-viral` (per-niche outliers by each channel's own median), `channel-ops`.
