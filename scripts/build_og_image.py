"""Render the LegalClear OG (Open Graph) social preview image.

1200x630 (Facebook, LinkedIn, Twitter `summary_large_image`).

Composition (locked from the v1 retheme):
  - Background: #FAFAF7
  - "legal" / "clear" wordmark, 130px Fraunces 500, color-split
    #1A1A1A / #1E40AF
  - Tagline beneath: "Florida legal help, explained in plain English."
    in Inter 400, 36px, #6B6B66
  - Geometric mark (circle + vertical line) bottom-right, 56px,
    #1E40AF stroke
  - Left padding 80px, asymmetric layout matching the homepage hero

Why Playwright: it's already installed in the backend venv (Phase 23
PDF/A pipeline uses it), Fraunces + Inter load from Google Fonts via
the same <link> the site uses, no separate font-rasterizer setup.

Output: frontend/public/og-image.png.

Re-run when the wordmark or tagline changes:
    backend/.venv/bin/python scripts/build_og_image.py
"""
import asyncio
from pathlib import Path

from playwright.async_api import async_playwright

OUT = Path(__file__).resolve().parents[1] / "frontend" / "public" / "og-image.png"

HTML = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet"
  href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500;9..144,600&family=Inter:wght@400;500&display=swap">
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  html, body {
    width: 1200px; height: 630px;
    background: #FAFAF7;
    font-family: "Inter", system-ui, sans-serif;
    -webkit-font-smoothing: antialiased;
  }
  body {
    padding: 80px;
    position: relative;
    display: flex;
    flex-direction: column;
    justify-content: center;
  }
  .wordmark {
    font-family: "Fraunces", Georgia, serif;
    font-size: 144px;
    font-weight: 500;
    letter-spacing: -0.025em;
    line-height: 1;
    margin-bottom: 28px;
  }
  .wordmark .legal { color: #1A1A1A; }
  .wordmark .clear { color: #1E40AF; }
  .tagline {
    font-family: "Inter", system-ui, sans-serif;
    font-weight: 400;
    font-size: 38px;
    line-height: 1.35;
    color: #6B6B66;
    max-width: 900px;
  }
  .tagline .accent { color: #1A1A1A; font-weight: 500; }
  .mark {
    position: absolute;
    bottom: 64px;
    right: 80px;
    color: #1E40AF;
  }
  .footer-rule {
    position: absolute;
    bottom: 0;
    left: 0;
    width: 100%;
    height: 6px;
    background: #1E40AF;
  }
</style>
</head>
<body>
  <div class="wordmark">
    <span class="legal">legal</span> <span class="clear">clear</span>
  </div>
  <div class="tagline">
    <span class="accent">Florida legal help,</span>
    explained in plain English.
  </div>
  <svg class="mark" width="64" height="64" viewBox="0 0 24 24"
       fill="none" stroke="currentColor" stroke-width="1.25" stroke-linecap="round">
    <circle cx="12" cy="12" r="9" />
    <line x1="12" y1="2" x2="12" y2="22" />
  </svg>
  <div class="footer-rule"></div>
</body>
</html>
"""


async def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        try:
            page = await browser.new_page(
                viewport={"width": 1200, "height": 630},
                device_scale_factor=1,
            )
            await page.set_content(HTML, wait_until="networkidle")
            # Slight settle for late-arriving Fraunces glyph metrics.
            await page.wait_for_timeout(500)
            await page.screenshot(
                path=str(OUT),
                type="png",
                clip={"x": 0, "y": 0, "width": 1200, "height": 630},
                omit_background=False,
            )
        finally:
            await browser.close()

    size = OUT.stat().st_size
    print(f"wrote {OUT.relative_to(OUT.parents[2])} ({size:,} bytes, 1200x630 PNG)")


if __name__ == "__main__":
    asyncio.run(main())
