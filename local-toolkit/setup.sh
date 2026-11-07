#!/bin/sh
# Local toolkit setup for your own computer (see local-toolkit/README.md). Safe to run again.
# Needs: git, uv, Node 22+, Python 3.12+, and the `claude` CLI. Nothing here runs in GitHub Actions.
set -e
TOOLKIT=${CLAUDE_TOOLKIT:-$HOME/claude-toolkit}
need() { command -v "$1" >/dev/null 2>&1 || { echo "✗ $1 is not installed: $2"; exit 1; }; }
need git "https://git-scm.com"
need uv "https://docs.astral.sh/uv/"

echo "1/4 SkillSpector (scan every skill before you install it)"
uv tool install --force "git+https://github.com/NVIDIA/SkillSpector.git@62c2fe8"

echo "2/4 Agent Reach, from GitHub (the PyPI package with the same name is a different project)"
uv tool install --force "git+https://github.com/Panniantong/Agent-Reach.git@c62128a"
agent-reach setup || echo "! agent-reach setup needs a look: run 'agent-reach doctor --text'"

echo "3/4 MCP servers for Claude Code (sign in later with /mcp > Authenticate)"
if command -v claude >/dev/null 2>&1; then
  claude mcp add --transport http --scope user higgsfield https://mcp.higgsfield.ai/mcp 2>/dev/null || true
  claude mcp add --transport http --scope user creatorberry https://www.creatorberry.com/api/mcp 2>/dev/null || true
else
  echo "! claude CLI not found: install Claude Code, then run this script again for the MCP servers"
fi

echo "4/4 Reference repos, pinned, into $TOOLKIT"
mkdir -p "$TOOLKIT"
clone() {  # clone <owner/repo> <commit>
  dir="$TOOLKIT/$(basename "$1")"
  [ -d "$dir/.git" ] || git clone --quiet "https://github.com/$1.git" "$dir"
  git -C "$dir" fetch --quiet origin "$2" 2>/dev/null || git -C "$dir" fetch --quiet origin
  git -C "$dir" checkout --quiet "$2" && echo "  $1 @ $2"
}
clone samuelgursky/davinci-resolve-mcp af6d897
clone pyang5166/gbro-collage-broll a1a4ee2
clone JohnHeibel/ClaudeAnimationBase 0ac8bf2
clone feitangyuan/onetake 013a61a          # PolyForm Noncommercial: personal tests only
clone debpalash/VoiceStudio fc154e7        # its default OmniVoice engine is non-commercial

echo "Scanning the repo's skills and the reference repos with SkillSpector (static checks only)..."
skillspector scan .claude/skills --no-llm || true
for d in "$TOOLKIT"/*/; do skillspector scan "$d" --no-llm || true; done
echo "✓ Done. Start 'claude' in this repo; type /mcp to sign in to Higgsfield and CreatorBerry."
echo "  DaVinci Resolve MCP: open Resolve, then follow $TOOLKIT/davinci-resolve-mcp/README.md."
echo "  IG research tool: https://leifabel.com/ig-research-tool/SETUP.md (Mac only; use a spare account)."
