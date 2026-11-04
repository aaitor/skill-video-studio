#!/usr/bin/env python3
"""Build a voice-led timeline. Never trim, overlap, or speed up spoken audio."""
import json
from pathlib import Path
import re
import subprocess
import sys
import wave

import numpy as np

SR = 48000
LEAD, GAP, TAIL = 0.35, 0.30, 0.8
SPOKEN = [
    "Turn a product workflow into a finished demo with Video Studio.",
    "Start in Claude Code. Ask for a narrated walkthrough using the bundled Acme app.",
    "Now move into the browser. Record the real workspace with Playwright.",
    "Filter by analytics to narrow the project list.",
    "Open Usage Insights and show the project details.",
    "Back in the terminal, compose the scenes and master the video. Check the picture, captions, and complete voice track.",
    "Your demo is ready. Get Video Studio on GitHub and make your own.",
]
ES = [
    "Convierte un flujo de producto en un demo terminado con Video Studio.",
    "Empieza en Claude Code. Pide un recorrido narrado de la app Acme incluida.",
    "Pasa al navegador. Graba el espacio de trabajo real con Playwright.",
    "Filtra por analítica para reducir la lista de proyectos.",
    "Abre Usage Insights y muestra los detalles del proyecto.",
    "Vuelve al terminal, compón las escenas y masteriza el vídeo. Comprueba imagen, subtítulos y voz completa.",
    "Tu demo está listo. Consigue Video Studio en GitHub y crea el tuyo.",
]


def load(path):
    with wave.open(str(path), "rb") as w:
        if w.getsampwidth() != 2:
            raise ValueError(f"{path}: expected PCM16 WAV")
        sr, channels = w.getframerate(), w.getnchannels()
        data = np.frombuffer(w.readframes(w.getnframes()), dtype="<i2").astype(np.float32) / 32768
    data = data.reshape(-1, channels).mean(axis=1)
    if sr != SR:
        data = np.interp(np.arange(round(len(data) * SR / sr)) / SR, np.arange(len(data)) / sr, data)
    if not len(data) or not np.any(data):
        raise ValueError(f"{path}: empty or silent narration")
    return data


def stamp(seconds):
    ms = round(seconds * 1000)
    return f"{ms // 3600000:02}:{ms % 3600000 // 60000:02}:{ms % 60000 // 1000:02},{ms % 1000:03}"


def main(project=None):
    if "--lines" in sys.argv:
        print("\n".join(SPOKEN))
        return
    project = Path(project) if project else Path(__file__).resolve().parent
    voices = [load(project / f"vo{i}.wav") for i in range(1, len(SPOKEN) + 1)]
    # Integer sample offsets preserve every sample, including the final word.
    starts, cursor = [], round(LEAD * SR)
    for voice in voices:
        starts.append(cursor)
        cursor += len(voice) + round(GAP * SR)
    total_samples = cursor - round(GAP * SR) + round(TAIL * SR)
    voice_track = np.zeros(total_samples, dtype=np.float32)
    for start, voice in zip(starts, voices):
        voice_track[start:start + len(voice)] = voice
    if np.max(np.abs(voice_track)) > 1:
        raise ValueError("Narration clips; normalize the source WAVs first")
    with wave.open(str(project / "voice.wav"), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((np.repeat(voice_track[:, None], 2, axis=1) * 32767).astype("<i2").tobytes())
    seconds = [x / SR for x in starts]
    total = total_samples / SR
    # Scene boundaries lie in the gaps between complete sentences.
    edges = [0] + [s - GAP / 2 for s in seconds[1:]] + [total]
    timing = dict(total=total, title_end=edges[1], terminal_start=edges[1], browser_start=edges[2],
                  filter_start=edges[3], detail_start=edges[4], result_start=edges[5], cta_start=edges[6],
                  vo_starts=seconds, line_durs=[len(v) / SR for v in voices])
    (project / "timing.json").write_text(json.dumps(timing, indent=2) + "\n")
    for language, lines in [("en", SPOKEN), ("es", ES)]:
        cues = [f"{i}\n{stamp(s / SR)} --> {stamp((s + len(v)) / SR)}\n{text}\n"
                for i, (s, v, text) in enumerate(zip(starts, voices, lines), 1)]
        (project / f"captions.{language}.srt").write_text("\n".join(cues))

    # Retime the three browser beats separately, so filter/open follow their narration.
    capture_duration = float(subprocess.check_output([
        "ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(project / "capture.mp4")
    ]))
    source_edges = [0, 7.8, 14.1, capture_duration]
    if capture_duration <= source_edges[-2]:
        raise ValueError("Browser capture does not contain the open-project beat")
    filters = []
    for i in range(3):
        duration = edges[i + 3] - edges[i + 2]
        scale = duration / (source_edges[i + 1] - source_edges[i])
        filters.append(f"[0:v]trim=start={source_edges[i]}:end={source_edges[i+1]},setpts=(PTS-STARTPTS)*{scale},fps=30[v{i}]")
    filters.append("[v0][v1][v2]concat=n=3:v=1:a=0[out]")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(project / "capture.mp4"),
                    "-filter_complex", ";".join(filters), "-map", "[out]", "-an", "-c:v", "libx264",
                    "-pix_fmt", "yuv420p", "-g", "30", "-keyint_min", "30", "-sc_threshold", "0",
                    str(project / "capture-timed.mp4")], check=True)

    page = project / "index.html"
    html = page.read_text()
    spans = {"root": (0, total), "bg": (0, total), "bgm": (0, total), "title": (0, edges[1]),
             "t1": (edges[1], edges[2]), "b-frame": (edges[2], edges[5]), "b-roll": (edges[2], edges[5]),
             "brandmark": (edges[2], edges[5]), "b-ch": (edges[2], edges[3]),
             "filter-ch": (edges[3], edges[4]), "detail-ch": (edges[4], edges[5]),
             "t2": (edges[5], edges[6]), "cta": (edges[6], total)}
    for element, (start, end) in spans.items():
        pattern = rf'(<[^>]*\bid="{element}"[^>]*>)'
        def update(match):
            tag = re.sub(r'data-start="[^"]*"', f'data-start="{start:.6f}"', match[0])
            return re.sub(r'data-duration="[^"]*"', f'data-duration="{end-start:.6f}"', tag)
        html, count = re.subn(pattern, update, html)
        if count != 1:
            raise ValueError(f"Expected exactly one #{element}, got {count}")
    html, count = re.subn(r'const timing = .*?;', "const timing = " + json.dumps(timing) + ";", html)
    if count != 1:
        raise ValueError("Composition needs one timing declaration")
    page.write_text(html)
    print(json.dumps(timing, indent=2))


if __name__ == "__main__":
    main()
