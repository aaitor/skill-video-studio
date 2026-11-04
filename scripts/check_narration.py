"""Regression check: long voice takes survive the CLI/browser composition intact."""
import contextlib
import importlib.util
import io
from pathlib import Path
import tempfile
from unittest.mock import patch
import wave

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / "projects/example-cli-tour"
spec = importlib.util.spec_from_file_location("cli_narration", PROJECT / "narrate.py")
narration = importlib.util.module_from_spec(spec)
spec.loader.exec_module(narration)


def main():
    with tempfile.TemporaryDirectory(prefix="narration-check-") as temporary:
        project = Path(temporary)
        (project / "index.html").write_text((PROJECT / "index.html").read_text())
        sources = []
        # The last sentence alone exceeds the old CTA slot; total exceeds the old 27.2s cap.
        for i, duration in enumerate([5, 6, 4, 3, 4, 8, 7], 1):
            data = np.full(duration * narration.SR, i * 1000, dtype="<i2")
            sources.append(data)
            with wave.open(str(project / f"vo{i}.wav"), "wb") as w:
                w.setnchannels(1)
                w.setsampwidth(2)
                w.setframerate(narration.SR)
                w.writeframes(data.tobytes())
        # Media conversion is exercised manually; this offline check isolates scheduling and mixing.
        with patch.object(narration.subprocess, "check_output", return_value=b"17.4\n"), \
             patch.object(narration.subprocess, "run"), contextlib.redirect_stdout(io.StringIO()):
            narration.main(project)
            first = (project / "index.html").read_text()
            narration.main(project)
            assert first == (project / "index.html").read_text(), "Retiming must be idempotent"
        with wave.open(str(project / "voice.wav")) as w:
            assert w.getframerate() == narration.SR
            track = np.frombuffer(w.readframes(w.getnframes()), dtype="<i2").reshape(-1, 2)
        cursor = round(narration.LEAD * narration.SR)
        for source in sources:
            expected = (source.astype(np.float32) / 32768 * 32767).astype("<i2")
            assert np.array_equal(track[cursor:cursor + len(source), 0], expected), "Voice samples lost or overlapped"
            assert np.array_equal(track[:, 0], track[:, 1]), "Stereo channels differ"
            cursor += len(source) + round(narration.GAP * narration.SR)
        expected_length = cursor - round(narration.GAP * narration.SR) + round(narration.TAIL * narration.SR)
        assert len(track) == expected_length
        assert not track[-round(narration.TAIL * narration.SR):].any(), "Final word needs a complete tail"
    print("OK: long narration preserved, stereo intact, full tail, idempotent scene timing.")


if __name__ == "__main__":
    main()
