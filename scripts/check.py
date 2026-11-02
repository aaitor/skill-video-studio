"""Offline source, documentation, manifest, and local music checks; no rendering/services."""

import ast
import html
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from urllib.parse import unquote, urlsplit
import wave
import xml.etree.ElementTree as ET

import yaml

ROOT = Path(__file__).resolve().parents[1]
EXCLUDED = {".git", ".venv", "__pycache__", "node_modules", ".pw", ".vhs", ".hyperframes", ".playwright-cli"}


def check_links(path, errors):
    text = re.sub(r"^(`{3,}|~{3,}).*?^\1[^\n]*$", "", path.read_text(), flags=re.M | re.S)
    # Inline source examples are instructions, not live document/media links.
    text = re.sub(r'`[^`\n]+`', '', text)
    links = re.findall(r'!?\[[^\]\n]*\]\(([^\s)]+)(?:\s+"[^"]*")?\)', text)
    links += re.findall(r'(?:href|src)=["\x27]([^"\x27]+)', text)
    for link in links:
        parsed = urlsplit(html.unescape(link))
        if parsed.scheme or parsed.netloc:
            continue
        if parsed.path:
            target = (ROOT if parsed.path.startswith("/") else path.parent) / unquote(parsed.path).lstrip("/")
        else:
            target = path
        if not target.exists():
            errors.append(f"{path.relative_to(ROOT)}: missing target {link}")
            continue
        if parsed.fragment and target.suffix == ".md":
            headings = re.findall(r"^#{1,6}\s+(.+)$", target.read_text(), flags=re.M)
            anchors = {re.sub(r"[^\w\- ]", "", heading.lower()).replace(" ", "-") for heading in headings}
            if parsed.fragment not in anchors:
                errors.append(f"{path.relative_to(ROOT)}: missing heading {link}")


def check_brief(path):
    data = yaml.safe_load(path.read_text())
    required = ["id", "mode", "audience", "message", "brand", "capture", "beats", "outputs", "duration_target_seconds"]
    if not isinstance(data, dict) or any(key not in data for key in required):
        raise ValueError("Brief is missing required fields")
    duration = data["duration_target_seconds"]
    if not isinstance(duration, (int, float)) or duration <= 0:
        raise ValueError("Brief duration must be positive")
    if not isinstance(data["beats"], list) or not data["beats"]:
        raise ValueError("Brief needs at least one beat")
    for beat in data["beats"]:
        if not beat.get("label") or not 0 <= beat["at_seconds"] < duration:
            raise ValueError("Brief beat needs a label and time within the duration")
    if not data["capture"].get("url") or not data["outputs"]:
        raise ValueError("Brief needs a capture URL and output profile")


def check_render_path(errors):
    """Guard the documented capture and silent-render path; the tools themselves stay out of CI."""
    skill = ROOT / ".claude/skills/devrel-video"
    example = ROOT / "projects/example-walkthrough"
    readme = (example / "README.md").read_text()
    # Capture fills the project folder first, and init refuses a non-empty folder.
    for path in (skill / "SKILL.md", example / "README.md"):
        if "hyperframes init projects/" in path.read_text():
            errors.append(f"{path.relative_to(ROOT)}: hyperframes init fails on a captured project")
    # npm installs into any ancestor with a package.json unless the prefix is explicit.
    if 'npm i --prefix "$SKILL/.pw"' not in (skill / "scripts/capture.sh").read_text():
        errors.append("capture.sh: install playwright-cli with an explicit --prefix")
    # The silent render must not need audio that only exists after a later step.
    before_render = readme.split("render-qa.sh")[0]
    for source in re.findall(r'<audio[^>]+src="([^"]+)"', (example / "index.html").read_text()):
        if source not in before_render:
            errors.append(f"projects/example-walkthrough/README.md: create {source} before render-qa.sh")


def main():
    errors = []
    counts = {"python": 0, "shell": 0, "javascript": 0, "manifests": 0}
    for path in ROOT.rglob("*"):
        if not path.is_file() or any(part in EXCLUDED for part in path.relative_to(ROOT).parts):
            continue
        try:
            if path.suffix == ".md":
                check_links(path, errors)
            elif path.suffix == ".svg":
                ET.parse(path)
            elif path.suffix == ".json":
                json.loads(path.read_text())
            elif path.suffix in (".yaml", ".yml"):
                yaml.safe_load(path.read_text())
                if path.name in ("brief.yaml", "recorded-brief.yaml", "brief.example.yaml"):
                    check_brief(path)
                    counts["manifests"] += 1
            elif path.suffix == ".py":
                ast.parse(path.read_text(), filename=str(path))
                counts["python"] += 1
            elif path.suffix in (".sh", ".js"):
                command = ["bash", "-n"] if path.suffix == ".sh" else ["node", "--check"]
                result = subprocess.run(command + [str(path)], capture_output=True, text=True)
                if result.returncode:
                    errors.append(f"{path.relative_to(ROOT)}: {result.stderr.strip()}")
                counts["shell" if path.suffix == ".sh" else "javascript"] += 1
        except (SyntaxError, ValueError, ET.ParseError, yaml.YAMLError, TypeError, KeyError) as exc:
            errors.append(f"{path.relative_to(ROOT)}: {exc}")
    check_render_path(errors)
    # Exercise one existing local utility, without TTS, GPUs, browsers, or any API.
    with tempfile.TemporaryDirectory(prefix="studio-music-check-") as temporary:
        output = Path(temporary) / "bed.wav"
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / ".claude/skills/devrel-video/scripts/gen-bgm.py"),
                str(output),
                "2",
                "corporate",
            ],
            capture_output=True,
            text=True,
        )
        if result.returncode:
            errors.append("Local music smoke test failed: " + result.stderr)
        else:
            with wave.open(str(output)) as audio:
                if (audio.getnchannels(), audio.getsampwidth(), audio.getframerate(), audio.getnframes()) != (
                    2,
                    2,
                    44100,
                    88200,
                ) or not any(audio.readframes(audio.getnframes())):
                    errors.append("Local music output has unexpected format, length, or silence.")
    if errors:
        print("\n".join(errors), file=sys.stderr)
        raise SystemExit(1)
    print("OK: documentation links/headings, SVG/JSON/YAML, source syntax, brief fields, local WAV smoke test.")
    print(counts)


if __name__ == "__main__":
    main()
