// playwright-cli hero script for the example-walkthrough — a silent tour of the self-contained
// "Acme" mock app in ./site/ (served locally; no login, no PII, no external dependency).
// Run via scripts/capture.sh after starting the local server (see this project's README / brief.yaml).
// Selectors are exact because we own the page; each beat still keeps a fallback (SKILL §4 rule).
async page => {
  const scrollTo = (y, dur) =>
    page.evaluate(({ y, dur }) => new Promise((res) => {
      const start = window.scrollY, delta = y - start, t0 = performance.now();
      const step = (now) => {
        const p = Math.min(1, (now - t0) / dur);
        const e = p < 0.5 ? 2 * p * p : 1 - Math.pow(-2 * p + 2, 2) / 2; // easeInOutQuad
        window.scrollTo(0, start + delta * e);
        if (p < 1) requestAnimationFrame(step); else res();
      };
      requestAnimationFrame(step);
    }), { y, dur });

  await page.screencast.start({ path: 'capture.webm', size: { width: 1600, height: 900 } });

  // ── Beat 1 — your workspace (t≈0) ──────────────────────────────────
  await page.waitForTimeout(2600);          // hold on the landing state
  await scrollTo(620, 1900);                // reveal the project grid
  await page.waitForTimeout(1500);
  await scrollTo(0, 1100);
  await page.waitForTimeout(700);

  // ── Beat 2 — filter by category (t≈7.8) — grid filters in place, no navigation ──
  {
    const tag = page.locator('#tags button[data-tag="analytics"]');
    if (await tag.count()) await tag.click();
    else await page.locator('#tags button').nth(1).click();   // fallback: first real category
  }
  await page.waitForTimeout(1600);
  await scrollTo(360, 1400);
  await page.waitForTimeout(1500);
  await scrollTo(0, 1100);
  await page.waitForTimeout(700);

  // ── Beat 3 — open a project (t≈14.1) — in-page detail overlay ──
  {
    const card = page.locator('.card[data-item="insights"]');  // an Analytics card, visible after the filter
    if (await card.count()) await card.first().click();
    else await page.locator('.card:not(.hide)').first().click();
  }
  await page.waitForTimeout(3200);          // hold on the opened detail

  await page.screencast.stop();
}
