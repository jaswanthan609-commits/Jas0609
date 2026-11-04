---
name: brief-refiner
description: Turn the owner's rough, voice-typed or one-line requests into a precise, testable brief before any work starts. Use at the start of every request in this repo (video changes, new formats, fixes, "make it better", "it feels flat", "audio is off"), and whenever a request bundles several asks.
---

# Brief refiner (prompt engineering for this project)

The owner speaks in quick, emotional, bundled messages ("visuals get flat", "hook is subpar", "music too loud").
They are right about what they feel and should never have to say it twice. Your job is to translate each
feeling into an engineering spec with a number that can be checked, then do the work against that number.

## Steps (do them silently; the owner sees only the result)

1. **Split** the message into separate asks. One line each. Keep the owner's words in quotes.
2. **Translate** each ask into a symptom and a measurable target, using the table below. If none fits,
   write your own target that a script or a tool can check, never "looks better".
3. **Find the cause** in the code before changing anything (grep the module, read the render, measure the
   output). Write the cause in one sentence.
4. **Write the brief** to `research/briefs/<date>-<slug>.md`:
   - Asks (quoted) -> targets (numbers) -> cause -> change -> how it will be verified.
   - Out of scope: what you will not touch.
5. **Do the work**, then run the `quality-gate` skill. Report only the before/after numbers and the output.
6. **Never ask the owner to rephrase.** Pick the most likely reading, say which one, and go.

## Translation table (owner's words -> target)

| owner says | measure | target |
| --- | --- | --- |
| "music too loud" / "rain is white noise" | earshot measure on music stem and bed stem, `describe` on the mix | bed reads as rain/fire (z >= 3) in describe; music 3-6 LU above bed; no "white noise"/"pink noise" tag >= 2.5 |
| "audio not clear" / "muffled" | earshot brightness, presence band | brightness >= 900 Hz on the music stem; presence band within 25 dB of low-mid |
| "sounds fake / AI" | earshot realness | mix p_real >= 0.75, music stem >= 0.75 |
| "audio mismatch" | sound sources vs picture | every audible texture has a visible cause (rain audible -> rain visible; fire audible -> fire glow visible); no visible weather without its sound |
| "visuals flat" | frame stats from `facepipe.qa.visual_report` | luminance std >= 0.16, mean motion between frames 1 s apart >= 0.6 %, at least 3 depth layers moving at different speeds |
| "animation sloppy" | loop seam, jitter | frame(0) vs frame(LOOP) diff < 0.5 %; no object pops (per-frame diff spikes > 4x median) |
| "hook is subpar" | critic.lint + hookscore + breakout comparison | hookscore >= 55 for story/long; a number or name in the first 2 scenes; first line under 20 words |
| "CTA is weak" | script end and description | one specific next action tied to the video (next episode, playlist, comment prompt with a question), no "like and subscribe" alone |
| "won't go viral" / "how to boom" | research/scan.json outliers in the niche | title and thumbnail follow the measured patterns (see cozy-benchmarks / lineup notes); length within the winners' middle half |
| "do it without me" | workflows on main | the job runs on schedule, opens a draft PR with the QA report, and the only human step is the merge |

## Prompt hygiene for the Claude calls inside facepipe

When you edit a prompt in `facepipe/script.py`, `ambience.py` or `critic.py`:
- State the audience, the format's job and the measured benchmark first (from research/), then the rules.
- Give one strong example drawn from a real breakout opening (research/hooks.json), never invented.
- Ask for structured output (pydantic) and validate it with `critic.lint`; never trust self-scores.
- Put banned patterns in code (lint), not only in the prompt.
