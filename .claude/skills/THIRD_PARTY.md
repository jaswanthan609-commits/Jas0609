# Third-party skills

Copied unchanged, MIT licensed (licence text in each source repository):

| skills | source | commit |
| --- | --- | --- |
| `yt-*` (11) | https://github.com/Jakeschincariol/youtube-agent-skill | a2feb21 |
| `threejs-*` (9 of 13) | https://github.com/CloudAI-X/threejs-skills | 0e18186 |
| `gsap-core`, `gsap-timeline`, `gsap-performance`, `gsap-utils` | https://github.com/greensock/gsap-skills | aed9cfd |

| `earshot`, `real-sound` | https://github.com/Leonxlnx/earshot | 591fa3e |

earshot also runs in CI (`.github/workflows/listen.yml`, `publish.yml`, `facepipe/listen.py`), pinned to
that commit, to measure and describe every rendered soundtrack.

`hooks.json` and `hookscore.py` from `yt-script` are also used by the pipeline in
`facepipe/vendor/ytagent/` (with its LICENSE) for the free hook check in `facepipe/critic.py`.

Our own: `outlier-scan`, `story-script`, `channel-ops`.
