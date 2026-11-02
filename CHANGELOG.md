# Changelog

## v1.0.1 — 2026-11-02

- Fix the compose step: `hyperframes init` refuses a captured project folder, so new videos start from `templates/composition.html`.
- Fix the silent render of `example-walkthrough`, which stopped on a narration mix that only exists after step 3.
- Install `playwright-cli` under `.pw/` even when a parent folder has a `package.json`, and show npm errors.

## v1.0 — 2026-10-29

- Publish the first release as Video Studio Skill with updated shared artwork.
- Rename the repository to `skill-video-studio`; update installation, project CTA links, and recording commands. Keep `/devrel-video` unchanged.

- Adopt the shared repository format with a branded banner, MIT license, focused README, guides, and community files.
- Add a real black-background Claude Code intake demo, producing a walkthrough brief before capture/render.
- Add offline source/documentation checks and a local background-music smoke test.
- Preserve the studio's native skill layout, production helpers, worked examples, and original long-form guides.
