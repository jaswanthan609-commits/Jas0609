# Third-party skills

Copied unchanged, MIT licensed (licence text in each source repository):

| skills | source | commit |
| --- | --- | --- |
| `yt-*` (11) | https://github.com/Jakeschincariol/youtube-agent-skill | a2feb21 |
| `threejs-*` (9 of 13) | https://github.com/CloudAI-X/threejs-skills | 0e18186 |
| `gsap-core`, `gsap-timeline`, `gsap-performance`, `gsap-utils` | https://github.com/greensock/gsap-skills | aed9cfd |

| `earshot`, `real-sound` | https://github.com/Leonxlnx/earshot | 591fa3e |
| `humanizer` (strips AI-writing tells from scripts and descriptions) | https://github.com/blader/humanizer | 0ef9fe5 |
| `i-have-adhd` (skill only; its always-on SessionStart hook is not installed) | https://github.com/ayghri/i-have-adhd | 1ecea19 |
| `video`, `social`, `copywriting`, `copy-editing`, `marketing-psychology`, `content-strategy`, `customer-research`, `ab-testing` (8 of ~50) | https://github.com/coreyhaines31/marketingskills | 88c79f6 |

Apache-2.0 (LICENSE in each folder):

| skills | source | commit |
| --- | --- | --- |
| `skill-creator`, `algorithmic-art`, `frontend-design` | https://github.com/anthropics/skills | ca45fc4 |
| `hyperframes`, `hyperframes-cli`, `hyperframes-registry`, `style-sampling`, `reverse-any-video` | https://github.com/heygen-com/hyperframes | c6f87f5 |

MIT (LICENSE in each folder):

| skills | source | commit |
| --- | --- | --- |
| `agent-reach` (local only: needs the `agent-reach` CLI from GitHub, see local-toolkit/) | https://github.com/Panniantong/Agent-Reach | c62128a |
| `lemo-opuscar` (local only: downloads its style library on first use) | https://github.com/lemomo-ai/lemo-opuscar | bebbbe1 |
| `prompt-optimizer`, `verification-loop`, `agent-self-evaluation`, `eval-harness`, `santa-method`, `loop-design-check`, `continuous-agent-loop`, `video-editing`, `content-engine`, `cost-aware-llm-pipeline`, `prompt-caching-strategy`, `growth-log`, `skill-scout` (13 of the ECC set) | https://github.com/affaan-m/everything-claude-code | b38be6a |

AGPL-3.0 (LICENSE in the folder; these files stay under AGPL):

| skills | source | commit |
| --- | --- | --- |
| `openmontage-craft`: 23 craft files from `skills/creative`, `core`, `meta`, `pipelines/documentary-montage`, plus our index | https://github.com/calesthio/OpenMontage | d21f5d4 |

Not taken, on purpose: Anthropic's docx/pdf/pptx/xlsx (not for video), brand-guidelines (Anthropic's brand),
slack-gif-creator, theme-factory, canvas-design; HyperFrames figma, slideshow, media-use (HeyGen paid
services), remotion-to-hyperframes; the other ~40 marketing skills (SaaS, email, ads, pricing); OpenMontage's
Python tools and its copies of third-party skills we already have.

earshot also runs in CI (`.github/workflows/listen.yml`, `publish.yml`, `facepipe/listen.py`), pinned to
that commit, to measure and describe every rendered soundtrack.

`hooks.json` and `hookscore.py` from `yt-script` are also used by the pipeline in
`facepipe/vendor/ytagent/` (with its LICENSE) for the free hook check in `facepipe/critic.py`.

Our own: `outlier-scan`, `story-script`, `channel-ops`, `brief-refiner` (turns the owner's rough asks into measurable targets), `quality-gate` (audio, picture, sync and packaging checks before anything is called done).
