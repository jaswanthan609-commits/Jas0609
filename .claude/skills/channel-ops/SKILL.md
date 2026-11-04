---
name: channel-ops
description: Run the faceless channels end to end without asking the owner: drafts, renders, uploads, budget and weekly review. Use for any operational task on facepipe channels or when something in the daily pipeline fails.
---

# Channel operations

The owner's only job is merging the daily drafts PR. Everything else is ours. Do not hand them
tasks that a workflow, a script or a decision of ours can do.

## The loop (all in GitHub Actions)

| when | workflow | what |
| --- | --- | --- |
| daily 06:00 IST | `drafts.yml` | `scan` (weekly), `breakout --all`, `autopilot` (budget decides), review PR |
| on merge | `publish.yml` | render every approved script, upload when `UPLOAD_ENABLED=true` |
| weekly | `stats.yml` | earnings into the budget ledger |

Line-up and days: `config/autopilot.yaml`. Channel settings: `config/channels/*.yaml`.
Formats: `short`, `long`, `story` (15 min), `deep` (30 min), `sleep` (2 h), `ambience` (90 min).

## Rules

- Money: $70 total, must sustain itself; check `python -m facepipe budget`. Never add a paid tool
  without showing it pays back inside the budget.
- Policy: every upload is unique (own script, own scene, own music); scripts get human approval via
  the PR (YouTube's mass-produced rule); `containsSyntheticMedia` stays true.
- Never put secrets in the repo; keys live in GitHub secrets. The repo is public.
- Never post, upload or message outside the pipeline's approval flow.

## When something fails

1. Read the failed run's log (`mcp__github__get_job_logs`).
2. Reproduce locally with `--dry-run` or `make --offline`.
3. Fix the cause, run `pytest -q`, push on the working branch, open a PR. Tell the owner only the
   result and anything they must tap.

## Weekly review (Mondays)

Read `research/scan.json` ranking and our own `stats`: if an area cooled, move seeds; if one of our
videos is a winner (3x median), breakout already queued follow-ups; check they are in the next PR.
Use `/yt-retention` on retention exports and `/yt-package` on titles that under-performed.
