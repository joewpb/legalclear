"""Generate the B5 UI live-gate fixture PDF (one page, text layer).

Run: cd backend && uv run python ../scripts/gen_b5_ui_fixture.py
Output: ../scripts/fixtures/b5_ui_summons.pdf
"""
from pathlib import Path

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

OUT = Path(__file__).resolve().parent / "fixtures" / "b5_ui_summons.pdf"
OUT.parent.mkdir(parents=True, exist_ok=True)

lines = [
    "IN THE COUNTY COURT IN AND FOR SAINT LUCIE COUNTY, FLORIDA",
    "CASE NO. 2026-CC-004242",
    "",
    "SUMMONS - EVICTION / RESIDENTIAL",
    "",
    "TO: TEST TENANT",
    "2000 GATEWAY AVE",
    "PORT SAINT LUCIE, FL 34953",
    "",
    "A lawsuit has been filed against you. You are required to serve a "
    "written response to the attached complaint within the time allowed by "
    "law. Failure to respond may result in a default judgment being entered "
    "against you for the relief demanded in the complaint.",
    "",
    "DATED this 14th day of August, 2026.",
    "",
    "CLERK OF THE COUNTY COURT",
]

c = canvas.Canvas(str(OUT), pagesize=letter)
y = 720
for line in lines:
    c.drawString(72, y, line)
    y -= 16
c.save()
print(f"wrote {OUT} ({OUT.stat().st_size} bytes)")
