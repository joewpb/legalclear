"""HTML -> Playwright PDF -> pikepdf PDF/A-1b metadata.

Per `phases/source/PHASE_23_packet_builder.md`:
- Jinja2 renders the cover sheet / walkthrough / form-fields summary
- Playwright (headless Chromium) prints to a temp PDF
- pikepdf stamps PDF/A-1b conformance metadata onto the final file

Playwright is used here ONLY for headless print-to-PDF of locally rendered
HTML -- no remote browser navigation against any external portal. The
Phase 23 `test_no_mode_b` hard test enforces this contract by scanning for
the literal portal hostname; this docstring intentionally avoids that
hostname so the scan stays a clean negative for this file.
"""
from pathlib import Path

import pikepdf
from jinja2 import Environment, FileSystemLoader, select_autoescape
from playwright.async_api import async_playwright

_TEMPLATES_DIR = Path(__file__).resolve().parents[1] / "templates"

env = Environment(
    loader=FileSystemLoader(str(_TEMPLATES_DIR)),
    autoescape=select_autoescape(["html", "xml"]),
)


async def render_html_to_pdfa(
    template_relative_path: str,
    context: dict,
    output_path: Path,
) -> Path:
    """Render a Jinja2 template to a PDF/A-1b file at `output_path`."""
    template = env.get_template(template_relative_path)
    html = template.render(**context)

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temp_pdf = output_path.with_suffix(".tmp.pdf")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        try:
            page = await browser.new_page()
            await page.set_content(html, wait_until="networkidle")
            await page.pdf(
                path=str(temp_pdf),
                format="Letter",
                margin={
                    "top": "0.75in",
                    "bottom": "0.75in",
                    "left": "0.75in",
                    "right": "0.75in",
                },
                print_background=True,
            )
        finally:
            await browser.close()

    with pikepdf.open(temp_pdf, allow_overwriting_input=False) as pdf:
        with pdf.open_metadata() as meta:
            meta["pdf:Producer"] = "LegalClear Filing Packet Generator"
            meta["pdfaid:part"] = "1"
            meta["pdfaid:conformance"] = "B"
            meta["dc:title"] = context.get(
                "packet_id", "LegalClear Filing Packet"
            )
        pdf.save(str(output_path), linearize=True)

    temp_pdf.unlink(missing_ok=True)
    return output_path
