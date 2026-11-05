# Local toolkit: Claude Code tools for your own computer

Some tools you sent need a desktop app, a browser login or your own internet connection, so they can't run in
GitHub Actions. They live here, ready for when you set up Claude Code on your PC. Nothing in this folder runs in
the automated pipeline.

## Set up (once)

1. Install Claude Code, Git, Node 22+, Python 3.12+, ffmpeg and [uv](https://docs.astral.sh/uv/).
2. Clone this repo, open a terminal in it, and run:

   ```bash
   sh local-toolkit/setup.sh            # skill scanner, Agent Reach, MCP servers, reference repos
   ```

3. Start `claude` in the repo. The skills in `.claude/skills` load by themselves. For the MCP servers, type `/mcp`,
   pick each one and choose **Authenticate** (it opens a browser sign-in).

Before you install any new skill, scan it first: `skillspector scan <folder or GitHub URL> --no-llm`.

## What's in it

| Tool | What it's for here | Licence | OK on monetised videos? | How it's set up |
| --- | --- | --- | --- | --- |
| [NVIDIA SkillSpector](https://github.com/NVIDIA/SkillSpector) @62c2fe8 | Scans skills and MCP servers for prompt injection, data theft and supply-chain risks before you install them. It also runs in CI on every change to `.claude/skills` (`.github/workflows/skills-scan.yml`) | Apache-2.0 | n/a (a tool) | `setup.sh` installs the CLI |
| [Agent Reach](https://github.com/Panniantong/Agent-Reach) @c62128a | YouTube subtitles of breakout videos (works from a home connection, unlike GitHub's servers), Reddit and X research | MIT | yes | `setup.sh` installs it from GitHub; skill in `.claude/skills/agent-reach` |
| [Lemo-Opuscar](https://github.com/lemomo-ai/lemo-opuscar) @bebbbe1 | 66 code-made film styles (engraving, ink wash, archive) for Slow History intros and trailers | MIT | yes | skill in `.claude/skills/lemo-opuscar`; it downloads the library to `~/lemo-opuscar` on first use |
| [youtube-agent-skill](https://github.com/Jakeschincariol/youtube-agent-skill) | `/yt-*` planning, scripting, packaging and retention skills | MIT | yes | already in `.claude/skills/yt-*` |
| [Higgsfield Virality Predictor](https://higgsfield.ai/mcp) | Scores the first 15 s of a video: hook, hold rate | Higgsfield terms; credits (free tier ~10/day) | yes | MCP server `higgsfield`, browser sign-in |
| [CreatorBerry](https://www.creatorberry.com/claude) | Outlier videos, why they worked, hooks and scripts | CreatorBerry terms; 1 credit per new analysis | yes | MCP server `creatorberry`, browser sign-in |
| [DaVinci Resolve MCP](https://github.com/samuelgursky/davinci-resolve-mcp) @af6d897 | Lets Claude drive DaVinci Resolve for hand edits | MIT | yes | needs Resolve open (Studio for external scripting); `setup.sh` clones it, then follow its README to add it with `claude mcp add` |
| [gbro-collage-broll](https://github.com/pyang5166/gbro-collage-broll) @a1a4ee2 | 5 s vertical collage B-roll | MIT | yes, but its video model is paid per clip | cloned to `~/claude-toolkit/` |
| [ClaudeAnimationBase](https://github.com/JohnHeibel/ClaudeAnimationBase) @0ac8bf2 | p5.js character animation base | MIT code | **code yes, the Clawd mascot no**: it's Anthropic's character, so use the code with our own characters only | cloned to `~/claude-toolkit/` |
| [onetake](https://github.com/feitangyuan/onetake) @013a61a | One-take video editing | **PolyForm Noncommercial** | **no**: personal tests only, never on a monetised channel | cloned to `~/claude-toolkit/` |
| [VoiceStudio](https://github.com/debpalash/VoiceStudio) @fc154e7 | Desktop app wrapping many voice engines | AGPL-3.0; default engine OmniVoice is **non-commercial** | **only with a commercially licensed engine** (e.g. Kokoro); never OmniVoice | cloned to `~/claude-toolkit/`; runs as a desktop/Docker app |
| [IG research tool](https://leifabel.com/ig-research-tool/SETUP.md) | Pulls top Instagram posts and transcribes their openings | the author's terms | yes | follow its SETUP.md; Mac only |

## Things to know before you use them

- **Logins:** Agent Reach's Reddit, X and Instagram channels, and the IG research tool, use your browser login.
  Automated reading is against those sites' terms and can get the account limited, so use a spare account,
  never your main one.
- **Agent Reach from PyPI is a different project.** Only install it with `setup.sh` (from GitHub).
- **Lemo-Opuscar** always pulls the latest library from its `main` branch on first use; the skill itself is pinned.
- **Paid credits:** Higgsfield, CreatorBerry and gbro's video model spend money. Check the price before a big batch.
