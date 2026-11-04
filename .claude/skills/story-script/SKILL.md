---
name: story-script
description: Write or fix a "what really happened" story script or a 2-hour sleep script for facepipe. Use when drafting, reviewing or rewriting scripts for the story or sleep formats.
---

# Story and sleep scripts

The owner judges a video by one test: would they skip it? Write for that viewer.

## Story (format `story`, ~15 min, What Really Happened)

1. **Cold open, 20-30 s.** Drop into the single most dramatic real moment, mid-action, with a time,
   place, person or number. No context, no greeting, no "in this video". Check it with
   `python .claude/skills/yt-script/hookscore.py --hook "<line>"`; below 40 is dead.
2. **The question.** One line naming the mystery the video answers.
3. **Rewind and build.** People, stakes, then events in order. Every 60-90 s open a new loop and
   close an older one. Put a chapter title on the first scene of each section.
4. **The turn.** The decision everything hinged on, slowly, with real numbers.
5. **Payoff.** Answer the opening question fully, then one line on what it means today.
6. Facts: every name, date and amount goes in `facts_to_check` with its source. No invented quotes
   or inner thoughts; "reportedly" where reporting is the only source.
7. Read `research/hooks.json` openings for structure, never words.

## Sleep (format `sleep`, ~2 h, Slow History for Sleep)

- "You" inside a hard past life, contrasted with the warm bed now. Long flowing sentences, sights,
  sounds, smells, routines. No hooks, cliffhangers, questions, exclamation marks or violence.
- A 30-second soft trailer opens chapter 1, then one gentle subscribe line.
- Scenes 30-45 s each; `visual_query` names things painters depicted (museum search).
- Written as an outline plus one call per chapter (`facepipe/script.py:_write_chaptered`).

## Before it goes in the drafts PR

`facepipe/critic.py:lint` (free rules) then the model critic. A script that fails twice is dropped;
never lower `PASS_SCORE` to let one through.
