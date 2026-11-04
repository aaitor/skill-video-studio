"""Check that a rendered demo retains its complete reference mix without audio dropouts."""
import subprocess
import sys

import numpy as np

SR = 48000


def decode(path):
    return np.frombuffer(subprocess.check_output([
        "ffmpeg", "-v", "error", "-i", path, "-vn", "-ac", "1", "-ar", str(SR),
        "-f", "f32le", "-",
    ]), dtype="<f4")


def main():
    video, reference = sys.argv[1:]
    actual, expected = decode(video), decode(reference)
    if len(actual) < len(expected) - SR // 20:
        raise SystemExit("FAIL: the final video cuts the reference audio short")
    length = min(len(actual), len(expected))
    correlations, gains = [], []
    for start in range(0, length - SR // 2, SR // 2):
        a, b = actual[start:start + SR // 2], expected[start:start + SR // 2]
        rms_a, rms_b = np.sqrt(np.mean(a * a)), np.sqrt(np.mean(b * b))
        if rms_b < 0.005:
            continue
        correlation = float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))) if rms_a else 0
        gain = float(rms_a / rms_b)
        if correlation < 0.97 or not 0.9 < gain < 1.1:
            raise SystemExit(f"FAIL: altered or missing audio at {start / SR:.2f}s: correlation={correlation:.4f}, gain={gain:.3f}")
        correlations.append(correlation)
        gains.append(gain)
    if not correlations:
        raise SystemExit("FAIL: no audible reference windows")
    print(f"OK: complete audio, {len(correlations)} half-second windows, minimum correlation {min(correlations):.4f}, gain {min(gains):.3f}–{max(gains):.3f}.")


if __name__ == "__main__":
    main()
