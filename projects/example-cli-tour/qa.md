# README video QA

Checked on 2026-11-04. The deliverable is [`assets/default-demo.mp4`](../../assets/default-demo.mp4), generated from this project's composition, real Acme browser capture, local Kokoro `af_heart` voice, and quiet corporate music bed.

| Check | Result |
| --- | --- |
| Video | H.264, 1920 × 1080, 30 fps, 32.100 seconds |
| Audio | AAC stereo, 48 kHz, 32.100 seconds |
| Size | 4,826,714 bytes |
| Integrated loudness | −16.4 LUFS |
| Loudness range | 1.9 LU |
| True peak | −1.8 dBFS |
| Audio continuity | All 64 audible half-second windows match the reference mix; minimum waveform correlation 0.9977; RMS gain 0.994–1.000 |
| Final sentence | Complete; reference narration ends at 31.270 s, followed by an 800 ms tail |
| HyperFrames 0.9.5 | Check passed; zero lint/runtime/layout/motion/audio errors; 29/29 sampled text contrast checks pass WCAG AA |
| README delivery | Animated GIF preview and direct MP4 download; the hosted MP4 loads and plays in Chrome: 32.1 s, 1920 × 1080, no media error. GitHub strips custom HTML video tags from README content. |
| Offline regression | Every sample of seven longer voice takes survives without overlap or truncation; stereo, final tail, and idempotent timing verified |

SHA-256: `f2adfdb0267a3c4745fe65ea7b2dc1a9a665adaf821ffad8a47cd9b4d3bc2078`.

The [contact sheet](renders/contact-sample.png) was visually inspected: readable complete terminal prompt/result, real workspace/filter/detail states, and no private paths or credentials. Both terminal/browser handoffs fade through the brand background. Terminal scenes are labeled reenactments on screen and in the README.

A local Whisper `small.en` transcription of the final encoded MP4 recovered the narration through “Get Video Studio on GitHub and make your own.” This complements the sample-level regression and encoded/reference comparison; speech recognition alone is not an audio-continuity test.

HyperFrames reports nonblocking advisories about the existing flat composition structure and small decorative window labels. Its text-clipping information occurs during the intentional prompt typewriter reveal; the complete prompt is visible afterward.

Recheck a rebuild with:

```bash
python3 scripts/check.py
hyperframes check projects/example-cli-tour
python3 scripts/check_demo_audio.py assets/default-demo.mp4 projects/example-cli-tour/narration-mix.mp3
ffprobe -v error -show_streams -show_format assets/default-demo.mp4
ffmpeg -hide_banner -nostats -i assets/default-demo.mp4 -filter_complex ebur128=peak=true -f null -
```

The encoded/reference check detects missing or changed audio introduced by rendering. The narration regression detects the earlier fixed-slot truncation before rendering. Live capture, local synthesis, and full renders remain manual, outside CI.
