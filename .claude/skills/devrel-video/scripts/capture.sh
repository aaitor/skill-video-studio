#!/usr/bin/env bash
# Record a walkthrough with playwright-cli page.screencast, then convert to MP4.
# Usage: capture.sh <hero-script.js> [start-url] [WxH]
# The hero script MUST call: page.screencast.start({ path: 'capture.webm', ... })
set -euo pipefail

HERO="${1:?path to hero script (.js)}"; URL="${2:-}"; VP="${3:-1600x900}"
W="${VP%x*}"; H="${VP#*x}"
SKILL="$(cd "$(dirname "$0")/.." && pwd)"

# AppArmor/userns-restricted hosts need the sandbox off for capture; harmless elsewhere.
export PLAYWRIGHT_MCP_SANDBOX=false

# Install playwright-cli locally so the open->run-code->close session daemon persists.
# (A bare per-command `npx @playwright/cli` drops the browser between invocations.)
BIN="$SKILL/.pw/node_modules/.bin/playwright-cli"
if [ ! -x "$BIN" ]; then
  echo "installing @playwright/cli (one-time)…"
  mkdir -p "$SKILL/.pw" && npm i --prefix "$SKILL/.pw" --loglevel=error @playwright/cli@latest >/dev/null
fi
export PATH="$SKILL/.pw/node_modules/.bin:$PATH"

HERODIR="$(cd "$(dirname "$HERO")" && pwd)"; HEROFILE="$(basename "$HERO")"
cd "$HERODIR"

playwright-cli open   >/dev/null 2>&1
playwright-cli resize "$W" "$H" >/dev/null 2>&1
[ -n "$URL" ] && playwright-cli goto "$URL" >/dev/null 2>&1
playwright-cli eval "() => new Promise(r => setTimeout(r, 4000))" >/dev/null 2>&1  # let the SPA settle
playwright-cli run-code --filename="$HEROFILE"
playwright-cli close  >/dev/null 2>&1

[ -f capture.webm ] || { echo "ERROR: hero script did not produce capture.webm"; exit 1; }
# Dense keyframes (-g 30 -keyint_min 30 -sc_threshold 0 at -r 30): HyperFrames seeks every frame,
# and a sparse GOP freezes footage frames between keyframes during the render.
ffmpeg -v error -y -i capture.webm -c:v libx264 -r 30 -g 30 -keyint_min 30 -sc_threshold 0 \
  -pix_fmt yuv420p -movflags +faststart capture.mp4
echo "wrote $HERODIR/capture.mp4 ($(ffprobe -v error -show_entries format=duration -of csv=p=0 capture.mp4)s)"
