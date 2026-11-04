---
name: quality-gate
description: Definition of done for every video, demo, render or pipeline change in this repo. Run it before showing anything to the owner and before opening or updating a PR - it verifies audio, picture, sync, hook/CTA and automation with tools, then loops fix -> re-measure until every gate passes or the failure is reported plainly.
---

# Quality gate (verify before you deliver)

Nothing reaches the owner on a feeling. Every deliverable passes these gates, measured by tools, and the
report goes with it. If a gate fails, fix and re-measure (max 3 rounds); if still failing, ship nothing and
say which gate failed and why.

## 1. Audio (earshot; CI: `.github/workflows/listen.yml`, per video: `audio_report.json`)
- Mix `realness` >= 0.75 ("real or pro-produced"). Music stem alone >= 0.75.
- `describe` on the mix names the intended bed (rain / fire) with z >= 3, and no "white noise", "pink
  noise", "waterfall", "vacuum" tag at z >= 2.5.
- Balance: music stem 3-6 LU louder than the bed stem (ambience); voice 18-20 dB over music (narrated).
- Integrated loudness: -16 to -20 LUFS for ambience/sleep, -14 for stories; true peak <= -1.5 dBTP.
- Seam: the loop point has no click (sample jump <= 1.5x the typical step; test_music / test_beds).

## 2. Picture (`python -m facepipe qa <video>`; frames at 1 s steps)
- Not flat: luminance std >= 0.16; motion between frames >= 0.6 %; 3+ depth layers.
- Loop seamless: first vs last frame of the loop differ < 0.5 %.
- No pops: no per-frame difference spike > 4x the median.
- Thumbnail frame: subject readable at 320x180, contrast ratio >= 4.5 for any text.
- Look at 3 frames yourself (Read the jpgs) before claiming anything about the look.

## 3. Sync and match
- Every audible texture has a visible cause and vice versa (rain <-> rain on glass, fire <-> fire glow).
- Narrated formats: caption timing within 150 ms of the voice; scene cuts on sentence ends.

## 4. Packaging (story/long; ambience uses the title rules in its spec)
- `critic.lint` returns no problems; hookscore >= 55; model critic >= 8 on hook and retention.
- Title follows the niche's measured pattern; 60-95 chars for ambience, <= 70 for stories.
- CTA: one specific next action tied to the video; description has chapters (long) and credits (samples, beds).

## 5. Automation
- The change runs in CI on the branch (workflow green) before it is called done.
- Scheduled jobs live on `main`; a draft PR carries the QA report; the owner's only step is the merge.

## Report format (what the owner sees)
Three lines max: what changed, the before -> after numbers for the gates it touched, and the link/file.
