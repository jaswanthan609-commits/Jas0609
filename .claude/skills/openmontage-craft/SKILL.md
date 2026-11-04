---
name: openmontage-craft
description: Production craft notes for faceless videos - storytelling, long-form and short-form retention benchmarks, b-roll planning, sound design, typography, editing, colour grading, ffmpeg, subtitle sync, a reviewer checklist, taste direction, voice performance and a documentary-montage pipeline. Use when writing, editing or reviewing a Slow History, What Really Happened or Cozy Hours video, or when judging pacing, retention or polish.
---

# OpenMontage craft notes

A curated slice of OpenMontage's own production knowledge (AGPL-3.0, LICENSE in this folder,
https://github.com/calesthio/OpenMontage at d21f5d4). Only the tool-independent craft files are kept. They
mention OpenMontage's own tools (`tool_registry`, selectors, providers), which facepipe does not have: map
them to facepipe instead (script.py writes, visuals.py sources images and art, assemble.py edits with ffmpeg,
music.py and samples.py score, listen.py runs earshot, critic.py reviews).

| need | read |
| --- | --- |
| a story's shape, tension, payoff | `creative/storytelling.md` |
| 10+ minute videos: hook by 0:30, pattern interrupts, chapter length, retention targets | `creative/long-form.md` |
| Shorts / trailers | `creative/short-form.md` |
| what to show over narration | `creative/broll-planning.md`, `documentary-montage/*.md` |
| music beds, ducking, loudness | `creative/sound-design.md` |
| on-screen text | `creative/typography.md` |
| cuts and pacing | `creative/video-editing.md`, `creative/cinematic.md` |
| grade, ffmpeg recipes, caption timing | `core/color-grading.md`, `core/ffmpeg.md`, `core/subtitle-sync.md` |
| reviewing a draft before the approval PR | `meta/reviewer.md`, `meta/taste-direction.md` |
| directing a TTS read | `meta/voice-performance-director.md` |

Sleep and ambience formats break some of these rules on purpose (no pattern interrupts, no hooks that jolt):
follow the channel's format brief in facepipe/script.py where they disagree.
