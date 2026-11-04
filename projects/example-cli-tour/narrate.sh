#!/usr/bin/env bash
# One local Kokoro voice; measured WAV lengths drive scenes, footage, captions, and music.
# Requires HyperFrames + kokoro-onnx/soundfile (HYPERFRAMES_PYTHON may select a virtualenv).
# To use your existing endpoint instead: NARRATION_ENGINE=orpheus narrate.sh dan
set -euo pipefail
PROJ="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
S="$(cd "$PROJ/../../.claude/skills/devrel-video/scripts" && pwd)"
ENGINE="${NARRATION_ENGINE:-kokoro}"
case "$ENGINE" in
  kokoro) VOICE="${1:-af_heart}" ;;
  orpheus) VOICE="${1:-dan}" ;;
  *) echo "Unknown NARRATION_ENGINE: $ENGINE (use kokoro or orpheus)" >&2; exit 1 ;;
esac
mapfile -t LINES < <(python3 "$PROJ/narrate.py" --lines)
i=1
for line in "${LINES[@]}"; do
  if [ "$ENGINE" = kokoro ]; then
    hyperframes tts "$line" --voice "$VOICE" -o "$PROJ/vo$i.wav"
  else
    "$S/tts.sh" "$line" "$PROJ/vo$i.wav" "$VOICE"
  fi
  i=$((i + 1))
done
python3 "$PROJ/narrate.py"
TOTAL="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["total"])' "$PROJ/timing.json")"
python3 "$S/gen-bgm.py" "$PROJ/bgm.wav" "$TOTAL"
"$S/mix-audio.sh" "$PROJ/bgm.wav" "$PROJ/voice.wav" "$PROJ/narration-mix.mp3" 0.16
