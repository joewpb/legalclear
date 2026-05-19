# LegalClear — Complete One-Shot Build Prompt
# For: OpenCode + Nemotron Super 120B + uv + Pop OS/Ubuntu
#
# PORTS:
#   Nemotron inference container : localhost:8000  (DO NOT CHANGE)
#   LegalClear FastAPI backend   : localhost:8001  (DO NOT CHANGE)
#   Web frontend                 : localhost:3000
#
# PYTHON: Use uv for everything. Never use pip or python3 directly.
#   Create venv : uv venv --python 3.11
#   Install     : uv pip install -r requirements.txt
#   Run scripts : uv run python script.py
#
# BEFORE YOU START:
#   1. Set ANTHROPIC_API_KEY in backend/.env before Phase 3
#   2. Run Supabase SQL from Phase 8 in your dashboard before Phase 10
#   3. Each phase must fully complete before starting the next

---

# LegalClear — Complete One-Shot Build Prompt

## Master instructions — read before executing anything

You are building LegalClear, a full-stack AI-powered legal document
explanation product. This is a single self-directed build session.

**Non-negotiable execution rules:**

1. Execute phases in strict order: 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14.
2. After completing each phase, run the verification test for that phase.
3. Read the test output. If any assertion fails or any error appears, fix
   the error before moving to the next phase. Do not proceed on a broken phase.
4. If a test fails more than twice on the same phase, stop and print:
   "PHASE [N] BLOCKED — [error summary]" and halt. Do not continue.
5. Only move to the next phase after printing:
   "PHASE [N] COMPLETE — all checks passed."
6. Never skip a phase. Never reorder phases.
7. The venv at ~/legalclear/backend/venv must be active for all Python work.
8. All Python test files run from inside ~/legalclear/backend/.

---

## Phase 0 — Scaffold

Create the project at ~/legalclear/ with this exact structure:

```
legalclear/
├── backend/
│   ├── src/
│   │   ├── agents/
│   │   │   ├── __init__.py
│   │   │   ├── classifier.py
│   │   │   ├── explainer.py
│   │   │   ├── form_guide.py
│   │   │   ├── risk_scanner.py
│   │   │   └── expungement.py
│   │   ├── ingestion/
│   │   │   ├── __init__.py
│   │   │   ├── pdf_parser.py
│   │   │   ├── ocr.py
│   │   │   └── text_cleaner.py
│   │   ├── memory/
│   │   │   ├── __init__.py
│   │   │   └── db.py
│   │   ├── payments/
│   │   │   ├── __init__.py
│   │   │   └── stripe_client.py
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   └── routes.py
│   │   ├── platforms/
│   │   │   ├── __init__.py
│   │   │   ├── florida_courts.py
│   │   │   └── notifications.py
│   │   ├── core/
│   │   │   ├── __init__.py
│   │   │   ├── config.py
│   │   │   ├── disclaimer.py
│   │   │   ├── escalation.py
│   │   │   └── i18n.py
│   │   └── data/
│   │       ├── __init__.py
│   │       ├── jurisdictions.json
│   │       └── forms_library.json
│   ├── requirements.txt
│   ├── .env.example
│   └── main.py
├── frontend/
├── mobile/
└── README.md
```

Write backend/requirements.txt with exactly these packages:
```
anthropic
fastapi
uvicorn
pymupdf
pytesseract
pillow
supabase
stripe
python-dotenv
pydantic
aiohttp
python-multipart
pytest
deep-translator
reportlab
weasyprint
playwright
```

Write backend/.env.example:
```
ANTHROPIC_API_KEY=
SUPABASE_URL=
SUPABASE_ANON_KEY=
SUPABASE_SERVICE_KEY=
STRIPE_SECRET_KEY=
STRIPE_WEBHOOK_SECRET=
STRIPE_PRICE_SMALL=price_xxx
STRIPE_PRICE_MEDIUM=price_xxx
STRIPE_PRICE_LARGE=price_xxx
STRIPE_SUBSCRIPTION_PRICE_ID=price_xxx
API_KEY=testkey123
ENVIRONMENT=development
MESSAGING_PLATFORM=log
BACKEND_PORT=8001
```

Write backend/src/data/jurisdictions.json as a JSON object with entries
for all 50 US states + DC. Use real data for Florida, California, New York,
Texas, Georgia, and Illinois. Use placeholder data for all others.

Florida entry must be exactly:
```json
{
  "Florida": {
    "small_claims_court_name": "County Court",
    "small_claims_dollar_limit": 8000,
    "small_claims_filing_fee_range": "$55-$300",
    "court_self_help_url": "https://www.flcourts.gov",
    "public_defender_url": "https://www.pd.state.fl.us",
    "legal_aid_url": "https://www.floridalegal.org",
    "portal_county_codes": {
      "Miami-Dade": "miami-dade",
      "Broward": "broward",
      "Palm Beach": "palm-beach",
      "Martin": "martin",
      "Orange": "orange",
      "Hillsborough": "hillsborough"
    }
  }
}
```

Write backend/src/data/forms_library.json with entries for:
IRS_1040, IRS_W9, USCIS_I485, USCIS_N400, SSA_disability,
FL_small_claims_7B, FL_civil_cover_1997, CA_SC100,
generic_eviction_response, generic_expungement.

Each entry has: form_name, issuing_agency, jurisdiction_type,
official_url, description.

Create Python 3.11 venv using uv:
```bash
cd ~/legalclear/backend
uv venv --python 3.11
uv pip install -r requirements.txt
```

**Phase 0 verification — run before proceeding:**
```bash
cd ~/legalclear
find . -name "*.py" | head -30
cd backend && source venv/bin/activate
uv run python -c "import anthropic, fastapi, fitz, pytesseract, stripe, supabase, reportlab; print('ALL IMPORTS OK')"
python -c "import json; d=json.load(open('src/data/jurisdictions.json')); assert 'Florida' in d; assert 'California' in d; print('JURISDICTIONS OK')"
python -c "import json; f=json.load(open('src/data/forms_library.json')); assert 'IRS_1040' in f; print('FORMS LIBRARY OK')"
```

All three commands must print their OK message.
Print "PHASE 0 COMPLETE — all checks passed." then continue.

---

## Phase 1 — Document ingestion

Work in backend/src/ingestion/. Venv is active. Do not reinstall packages.

### pdf_parser.py

```python
import fitz
import os

class PDFParser:

    def extract_text(self, file_path: str) -> dict:
        doc = fitz.open(file_path)
        pages = [page.get_text() for page in doc]
        raw_text = "\n".join(pages)
        file_size_kb = os.path.getsize(file_path) / 1024
        return {
            "raw_text": raw_text,
            "pages": pages,
            "page_count": len(pages),
            "file_size_kb": round(file_size_kb, 2),
            "extraction_method": "pdf"
        }

    def extract_from_bytes(self, file_bytes: bytes) -> dict:
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        pages = [page.get_text() for page in doc]
        raw_text = "\n".join(pages)
        return {
            "raw_text": raw_text,
            "pages": pages,
            "page_count": len(pages),
            "file_size_kb": round(len(file_bytes) / 1024, 2),
            "extraction_method": "pdf"
        }

    def estimate_token_count(self, text: str) -> int:
        return int(len(text.split()) * 1.3)
```

### ocr.py

```python
import pytesseract
from PIL import Image, ImageFilter, ImageEnhance
import fitz
import io

class OCRProcessor:

    def extract_from_image(self, file_bytes: bytes,
                           lang: str = "eng") -> dict:
        img = Image.open(io.BytesIO(file_bytes))
        img = img.convert("L")
        img = ImageEnhance.Contrast(img).enhance(2.0)
        data = pytesseract.image_to_data(
            img, lang=lang,
            output_type=pytesseract.Output.DICT)
        raw_text = pytesseract.image_to_string(
            img, lang=lang)
        confidences = [int(c) for c in data["conf"]
                       if str(c).isdigit() and int(c) > 0]
        avg_confidence = (sum(confidences) / len(confidences)
                         if confidences else 0.0)
        return {
            "raw_text": raw_text,
            "pages": [raw_text],
            "page_count": 1,
            "confidence": round(avg_confidence / 100, 2),
            "extraction_method": "ocr"
        }

    def extract_from_pdf_images(self, file_bytes: bytes,
                                lang: str = "eng") -> dict:
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        all_pages = []
        for page in doc:
            mat = fitz.Matrix(200/72, 200/72)
            pix = page.get_pixmap(matrix=mat)
            img_bytes = pix.tobytes("png")
            result = self.extract_from_image(img_bytes, lang)
            all_pages.append(result["raw_text"])
        full_text = "\n".join(all_pages)
        return {
            "raw_text": full_text,
            "pages": all_pages,
            "page_count": len(all_pages),
            "file_size_kb": round(len(file_bytes) / 1024, 2),
            "extraction_method": "ocr"
        }
```

### text_cleaner.py

```python
import re

class TextCleaner:

    def clean(self, raw_text: str) -> str:
        text = raw_text.replace("\x00", "")
        text = re.sub(r"[\x01-\x08\x0b\x0c\x0e-\x1f\x7f]",
                      "", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = re.sub(r" {3,}", " ", text)
        lines = text.split("\n")
        from collections import Counter
        line_counts = Counter(
            l.strip() for l in lines
            if len(l.strip()) > 5)
        repeated = {l for l, c in line_counts.items()
                    if c >= 5}
        cleaned = [l for l in lines
                   if l.strip() not in repeated]
        return "\n".join(cleaned).strip()

    def detect_language(self, text: str) -> str:
        text_lower = text.lower()
        spanish_words = [
            "contrato", "acuerdo", "demanda", "tribunal",
            "firmante", "arrendamiento", "inquilino",
            "propietario", "plazo", "pago"
        ]
        english_words = [
            "agreement", "contract", "plaintiff",
            "defendant", "lease", "hereby", "whereas",
            "tenant", "landlord", "party"
        ]
        es_count = sum(1 for w in spanish_words
                       if w in text_lower)
        en_count = sum(1 for w in english_words
                       if w in text_lower)
        return "es" if es_count > en_count else "en"

    def truncate_for_llm(self, text: str,
                          max_tokens: int = 90000) -> str:
        estimated = int(len(text.split()) * 1.3)
        if estimated <= max_tokens:
            return text
        target_chars = int(
            len(text) * max_tokens / estimated)
        first_part = int(target_chars * 0.6)
        last_part = int(target_chars * 0.4)
        truncation_notice = (
            "\n\n[Document truncated for processing. "
            "Some middle sections omitted.]\n\n"
        )
        return (text[:first_part] +
                truncation_notice +
                text[len(text) - last_part:])
```

### ingestion/__init__.py

```python
from .pdf_parser import PDFParser
from .ocr import OCRProcessor
from .text_cleaner import TextCleaner

_pdf_parser = PDFParser()
_ocr_processor = OCRProcessor()
_text_cleaner = TextCleaner()

async def ingest_document(file_bytes: bytes,
                          filename: str) -> dict:
    # Gate: file size
    if len(file_bytes) > 15_000_000:
        return {
            "error": True,
            "error_code": "document_too_large",
            "message_en": (
                "This document is too large to process. "
                "Please upload individual sections under 15MB."),
            "message_es": (
                "Este documento es demasiado grande. "
                "Por favor suba secciones individuales "
                "de menos de 15MB.")
        }

    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    # Magic byte detection fallback
    if ext not in ["pdf","jpg","jpeg","png","webp",
                   "tiff","bmp","txt"]:
        if file_bytes[:4] == b"%PDF":
            ext = "pdf"
        elif file_bytes[:2] == b"\xff\xd8":
            ext = "jpg"
        elif file_bytes[:4] == b"\x89PNG":
            ext = "png"
        else:
            return {
                "error": True,
                "error_code": "unsupported_format",
                "message_en": (
                    "Unsupported file type. Please upload "
                    "a PDF, image, or text file."),
                "message_es": (
                    "Tipo de archivo no compatible.")
            }

    # Extract
    if ext == "pdf":
        result = _pdf_parser.extract_from_bytes(file_bytes)
        if len(result["raw_text"].strip()) < 100:
            result = _ocr_processor.extract_from_pdf_images(
                file_bytes)
            result["extraction_method"] = "ocr_fallback"
    elif ext in ["jpg","jpeg","png","webp","tiff","bmp"]:
        result = _ocr_processor.extract_from_image(file_bytes)
    else:
        raw_text = file_bytes.decode("utf-8", errors="replace")
        result = {
            "raw_text": raw_text,
            "pages": [raw_text],
            "page_count": 1,
            "file_size_kb": round(len(file_bytes)/1024, 2),
            "extraction_method": "text"
        }

    cleaned = _text_cleaner.clean(result["raw_text"])
    language = _text_cleaner.detect_language(cleaned)
    truncated_text = _text_cleaner.truncate_for_llm(cleaned)
    token_estimate = _pdf_parser.estimate_token_count(cleaned)
    was_truncated = len(truncated_text) < len(cleaned)

    return {
        "text": truncated_text,
        "raw_text": cleaned,
        "pages": result.get("pages", []),
        "page_count": result.get("page_count", 1),
        "token_estimate": token_estimate,
        "file_size_kb": result.get("file_size_kb", 0.0),
        "extraction_method": result.get(
            "extraction_method", "unknown"),
        "filename": filename,
        "language": language,
        "truncated": was_truncated,
        "error": False
    }
```

**Phase 1 verification — create and run this test:**

First create test_lease.pdf:
```python
import fitz
doc = fitz.open()
page = doc.new_page()
page.insert_text((50, 50),
    "RESIDENTIAL LEASE AGREEMENT\n\n"
    "This agreement is entered into between Landlord "
    "John Smith (Owner) and Tenant Maria Garcia (Resident).\n\n"
    "Monthly rent is $1,500.00 due on the 1st of each month. "
    "A late fee of $150.00 applies after 5 days.\n\n"
    "Lease term: January 1, 2026 to December 31, 2026.\n\n"
    "AUTO-RENEWAL CLAUSE: This lease shall automatically renew "
    "for successive one-year terms unless either party provides "
    "30 days written notice of termination.\n\n"
    "BINDING ARBITRATION: Any disputes arising from this "
    "agreement shall be resolved through binding arbitration. "
    "Tenant waives the right to a jury trial.")
doc.save("test_lease.pdf")
print("test_lease.pdf created")
```

Then run backend/test_phase1.py:
```python
import asyncio, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from src.ingestion import ingest_document

async def run():
    with open("test_lease.pdf", "rb") as f:
        data = f.read()

    result = await ingest_document(data, "test_lease.pdf")

    assert result["error"] == False, f"Error: {result}"
    assert result["extraction_method"] in [
        "pdf", "ocr_fallback"], (
        f"Wrong method: {result['extraction_method']}")
    assert result["language"] == "en", (
        f"Wrong language: {result['language']}")
    assert result["token_estimate"] > 0, "Zero tokens"
    assert len(result["text"]) > 50, "Text too short"

    print(f"extraction_method: {result['extraction_method']}")
    print(f"language: {result['language']}")
    print(f"token_estimate: {result['token_estimate']}")
    print(f"text preview: {result['text'][:200]}")

    # Test oversized file gate
    big = await ingest_document(b"x" * 20_000_000, "big.pdf")
    assert big["error"] == True
    assert big["error_code"] == "document_too_large"

    # Test unsupported format gate
    bad = await ingest_document(b"garbage", "file.xyz")
    assert bad["error"] == True

    print("ALL PHASE 1 ASSERTIONS PASSED")

asyncio.run(run())
```

Run: `cd ~/legalclear/backend && uv run python test_phase1.py`
All assertions must pass.
Print "PHASE 1 COMPLETE — all checks passed." then continue.

---

## Phase 2 — Core utilities

Work in backend/src/core/ and backend/src/platforms/notifications.py.
Venv is active. Do not reinstall packages.

### core/config.py

```python
import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_ANON_KEY: str = os.getenv("SUPABASE_ANON_KEY", "")
    SUPABASE_SERVICE_KEY: str = os.getenv(
        "SUPABASE_SERVICE_KEY", "")
    STRIPE_SECRET_KEY: str = os.getenv(
        "STRIPE_SECRET_KEY", "")
    STRIPE_WEBHOOK_SECRET: str = os.getenv(
        "STRIPE_WEBHOOK_SECRET", "")
    STRIPE_PRICE_SMALL: str = os.getenv(
        "STRIPE_PRICE_SMALL", "")
    STRIPE_PRICE_MEDIUM: str = os.getenv(
        "STRIPE_PRICE_MEDIUM", "")
    STRIPE_PRICE_LARGE: str = os.getenv(
        "STRIPE_PRICE_LARGE", "")
    STRIPE_SUBSCRIPTION_PRICE_ID: str = os.getenv(
        "STRIPE_SUBSCRIPTION_PRICE_ID", "")
    API_KEY: str = os.getenv("API_KEY", "testkey123")
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    MESSAGING_PLATFORM: str = os.getenv(
        "MESSAGING_PLATFORM", "log")

    @property
    def is_development(self) -> bool:
        return self.ENVIRONMENT == "development"

settings = Settings()
```

Copy backend/.env.example to backend/.env if .env does not exist.

### core/disclaimer.py

```python
DISCLAIMER_EN = (
    "IMPORTANT: This is not legal advice. LegalClear is an "
    "AI-powered tool that helps you understand legal documents "
    "in plain language. It does not create an attorney-client "
    "relationship and is not a substitute for advice from a "
    "licensed attorney. For decisions involving your legal "
    "rights, obligations, or significant financial consequences, "
    "consult a licensed attorney in your jurisdiction."
)

DISCLAIMER_ES = (
    "IMPORTANTE: Esto no es asesoramiento legal. LegalClear es "
    "una herramienta impulsada por inteligencia artificial que "
    "le ayuda a comprender documentos legales en lenguaje "
    "sencillo. No crea una relacion abogado-cliente y no "
    "sustituye el consejo de un abogado con licencia. Para "
    "decisiones que involucren sus derechos legales, consulte "
    "a un abogado con licencia en su jurisdiccion."
)

SHORT_DISCLAIMER_EN = (
    "Not legal advice. For informational purposes only."
)

SHORT_DISCLAIMER_ES = (
    "No es asesoramiento legal. Solo para fines informativos."
)

CRIMINAL_WARNING_EN = (
    "This appears to be a criminal matter. LegalClear can help "
    "you understand what this document says in plain language. "
    "However, criminal cases involve rights that can be "
    "permanently affected by your decisions. If you cannot "
    "afford an attorney, you have the right to a public "
    "defender. Contact your local public defender's office "
    "before making any decisions about your case."
)

CRIMINAL_WARNING_ES = (
    "Este parece ser un asunto penal. LegalClear puede ayudarle "
    "a comprender lo que dice este documento en lenguaje "
    "sencillo. Sin embargo, los casos penales involucran "
    "derechos que pueden verse afectados permanentemente. Si "
    "no puede pagar un abogado, tiene derecho a un defensor "
    "publico. Comuniquese con la oficina del defensor publico "
    "local antes de tomar decisiones sobre su caso."
)

PLEA_WARNING_EN = (
    "WARNING: This is a plea agreement. Signing this document "
    "waives important legal rights that cannot be recovered. "
    "Do NOT sign this document without first speaking to an "
    "attorney or public defender. This is the single most "
    "important action you can take right now."
)

PLEA_WARNING_ES = (
    "ADVERTENCIA: Este es un acuerdo de culpabilidad. Firmar "
    "este documento renuncia a derechos legales importantes "
    "que no se pueden recuperar. NO firme este documento sin "
    "antes hablar con un abogado o defensor publico. Esta es "
    "la accion mas importante que puede tomar ahora mismo."
)


def get_disclaimer(lang: str,
                   level: str = "standard") -> str:
    lang = "es" if lang == "es" else "en"
    if level == "standard":
        return DISCLAIMER_ES if lang == "es" else DISCLAIMER_EN
    if level == "short":
        return (SHORT_DISCLAIMER_ES
                if lang == "es" else SHORT_DISCLAIMER_EN)
    if level == "criminal":
        return (CRIMINAL_WARNING_ES
                if lang == "es" else CRIMINAL_WARNING_EN)
    if level == "plea":
        return (PLEA_WARNING_ES
                if lang == "es" else PLEA_WARNING_EN)
    return DISCLAIMER_EN
```

### core/escalation.py

```python
import json
import os
from .disclaimer import get_disclaimer


def _load_jurisdictions():
    path = os.path.join(
        os.path.dirname(__file__), "../data/jurisdictions.json")
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return {}


_JURISDICTIONS = _load_jurisdictions()

_STANDARD = [
    "contract", "agreement", "real_estate", "employment",
    "financial", "will_estate", "notice", "other"
]
_ELEVATED = [
    "government_form", "court_filing",
    "small_claims_complaint", "small_claims_response",
    "small_claims_judgment", "expungement_petition"
]
_CRIMINAL = [
    "criminal_charge", "criminal_summons", "restraining_order"
]

_UNIVERSAL_LINKS_EN = [
    {"label": "Find free legal aid",
     "url": "https://www.lawhelp.org"},
    {"label": "Find your public defender",
     "url": "https://www.nacdl.org/Landing/PublicDefenders"},
    {"label": "Court self-help center",
     "url": "https://www.ncsc.org/topics/access-and-fairness/"
             "self-represented-litigants/resource-guide"}
]

_UNIVERSAL_LINKS_ES = [
    {"label": "Encuentre ayuda legal gratuita",
     "url": "https://www.lawhelp.org"},
    {"label": "Encuentre su defensor publico",
     "url": "https://www.nacdl.org/Landing/PublicDefenders"},
    {"label": "Centro de autoayuda del tribunal",
     "url": "https://www.ncsc.org/topics/access-and-fairness/"
             "self-represented-litigants/resource-guide"}
]


class EscalationRouter:

    def route(self, classification: dict,
              lang: str = "en") -> dict:
        category = classification.get(
            "document_category", "other")
        jurisdiction = classification.get(
            "jurisdiction_name", "unknown")

        links = (_UNIVERSAL_LINKS_ES
                 if lang == "es" else _UNIVERSAL_LINKS_EN)

        jur_data = _JURISDICTIONS.get(jurisdiction, {})
        if jur_data.get("legal_aid_url"):
            links = links + [
                {"label": (
                     "Ayuda legal en su estado"
                     if lang == "es"
                     else "Legal aid in your state"),
                 "url": jur_data["legal_aid_url"]}
            ]

        if category in _STANDARD:
            return {
                "disclaimer_level": "standard",
                "show_attorney_warning": False,
                "show_public_defender_info": False,
                "pre_analysis_warning": None,
                "resource_links": links,
                "escalation_color": "green"
            }
        if category in _ELEVATED:
            return {
                "disclaimer_level": "standard",
                "show_attorney_warning": True,
                "show_public_defender_info": False,
                "pre_analysis_warning": None,
                "resource_links": links,
                "escalation_color": "yellow"
            }
        if category in _CRIMINAL:
            return {
                "disclaimer_level": "criminal",
                "show_attorney_warning": True,
                "show_public_defender_info": True,
                "pre_analysis_warning": get_disclaimer(
                    lang, "criminal"),
                "resource_links": links,
                "escalation_color": "red"
            }
        if category == "plea_agreement":
            return {
                "disclaimer_level": "plea",
                "show_attorney_warning": True,
                "show_public_defender_info": True,
                "pre_analysis_warning": get_disclaimer(
                    lang, "plea"),
                "resource_links": links,
                "escalation_color": "red"
            }
        return {
            "disclaimer_level": "standard",
            "show_attorney_warning": False,
            "show_public_defender_info": False,
            "pre_analysis_warning": None,
            "resource_links": links,
            "escalation_color": "green"
        }
```

### core/i18n.py

```python
SUPPORTED_LANGUAGES = ["en", "es"]


def get_lang(detected: str,
             user_preference: str = None) -> str:
    if user_preference in SUPPORTED_LANGUAGES:
        return user_preference
    if detected in SUPPORTED_LANGUAGES:
        return detected
    return "en"


def translate_if_needed(text: str,
                        target_lang: str) -> str:
    if target_lang != "es":
        return text
    try:
        from deep_translator import GoogleTranslator
        return GoogleTranslator(
            source="en", target="es").translate(text)
    except Exception:
        return text
```

### platforms/notifications.py

```python
import aiohttp


class NotificationService:

    async def send(self, user_id: str, title: str,
                   message: str,
                   data: dict = None) -> dict:
        # MESSAGING SLOT
        # Set MESSAGING_PLATFORM in .env to activate a platform.
        # To add WhatsApp: implement send_whatsapp()
        # To add Slack: implement send_slack()
        # To add Discord: implement send_discord()
        print(f"[NOTIFICATION] user={user_id} "
              f"title={title} message={message}")
        return {"sent": True, "method": "log",
                "message": message}

    async def send_push(self, expo_token: str,
                        title: str, body: str,
                        data: dict = None) -> dict:
        if not expo_token:
            return {"sent": False, "reason": "no_token"}
        payload = {"to": expo_token, "title": title,
                   "body": body, "data": data or {}}
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://exp.host/--/api/v2/push/send",
                    json=payload,
                    headers={"Content-Type":
                             "application/json"}
                ) as resp:
                    ticket = await resp.json()
                    return {"sent": True, "ticket": ticket}
        except Exception as e:
            return {"sent": False, "error": str(e)}

    async def notify_document_ready(
            self, user_id: str, document_id: str,
            lang: str = "en") -> dict:
        title = ("Analisis listo" if lang == "es"
                 else "Analysis ready")
        message = ("Su documento ha sido analizado."
                   if lang == "es"
                   else "Your document analysis is ready.")
        return await self.send(
            user_id, title, message,
            {"document_id": document_id})

    async def notify_payment_confirmed(
            self, user_id: str,
            lang: str = "en") -> dict:
        title = ("Pago confirmado" if lang == "es"
                 else "Payment confirmed")
        message = ("Su pago fue procesado."
                   if lang == "es"
                   else "Your payment was processed.")
        return await self.send(user_id, title, message)
```

**Phase 2 verification — create and run backend/test_phase2.py:**

```python
import sys, os, asyncio
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.core.config import settings
from src.core.disclaimer import get_disclaimer
from src.core.escalation import EscalationRouter
from src.core.i18n import get_lang, translate_if_needed
from src.platforms.notifications import NotificationService

def test():
    # 1. Config
    assert hasattr(settings, "is_development")
    print(f"1. is_development: {settings.is_development}")

    # 2. Disclaimer ES criminal
    d = get_disclaimer("es", "criminal")
    assert "defensor" in d.lower(), "Missing defensor"
    print(f"2. ES criminal disclaimer OK (len={len(d)})")

    # 3. Disclaimer EN plea
    d = get_disclaimer("en", "plea")
    assert "plea" in d.lower()
    print(f"3. EN plea disclaimer OK")

    # 4. Escalation router — plea agreement
    router = EscalationRouter()
    result = router.route(
        {"document_category": "plea_agreement",
         "jurisdiction_name": "Florida"}, "es")
    assert result["escalation_color"] == "red"
    assert result["pre_analysis_warning"] is not None
    assert result["show_public_defender_info"] == True
    print(f"4. Escalation plea=red OK")

    # 5. Escalation router — green category
    result2 = router.route(
        {"document_category": "contract",
         "jurisdiction_name": "unknown"}, "en")
    assert result2["escalation_color"] == "green"
    print(f"5. Escalation contract=green OK")

    # 6. get_lang
    assert get_lang("en", "es") == "es"
    assert get_lang("es", None) == "es"
    assert get_lang("unknown", None) == "en"
    print(f"6. get_lang OK")

    # 7. Notification log
    async def _test_notify():
        n = NotificationService()
        r = await n.send("user_1", "Test", "Hello")
        assert r["sent"] == True
        assert r["method"] == "log"
        print(f"7. Notification log OK")

    asyncio.run(_test_notify())

    print("\nALL PHASE 2 ASSERTIONS PASSED")

test()
```

Run: `cd ~/legalclear/backend && uv run python test_phase2.py`
All assertions must pass.
Print "PHASE 2 COMPLETE — all checks passed." then continue.

---

## Phase 3 — Classifier agent

Work in backend/src/agents/classifier.py.
Venv active. ANTHROPIC_API_KEY must be set in .env.

```python
import json
from anthropic import Anthropic
from src.core.config import settings

SYSTEM_PROMPT = (
    "You are a legal document classification expert. "
    "Your only job is to analyze legal documents and return "
    "precise structured metadata about what they are. "
    "You are highly accurate. You never guess. If uncertain "
    "about any field, return \"unknown\". You always return "
    "valid JSON and nothing else. "
    "No preamble. No explanation. No markdown. JSON only."
)

VALID_CATEGORIES = [
    "contract", "government_form", "court_filing", "notice",
    "agreement", "will_estate", "employment", "real_estate",
    "financial", "criminal_charge", "criminal_summons",
    "plea_agreement", "restraining_order",
    "expungement_petition", "small_claims_complaint",
    "small_claims_response", "small_claims_judgment", "other"
]


class ClassifierAgent:

    def __init__(self):
        self.client = Anthropic(
            api_key=settings.ANTHROPIC_API_KEY)
        self.model = "claude-haiku-4-5-20251001"

    async def classify(self, document: dict) -> dict:
        text_sample = document.get("text", "")[:24000]

        user_prompt = f"""Analyze this legal document and
return JSON with exactly these fields:

document_category: one of exactly these values:
{", ".join(VALID_CATEGORIES)}

document_type: specific type string e.g.
"residential_lease", "IRS_1040",
"small_claims_complaint_florida"

jurisdiction_type: one of: federal, state, local, unknown

jurisdiction_name: state name if state/local,
"federal" if federal, "unknown" if cannot determine

issuing_agency: e.g. "IRS", "USCIS",
"Florida Courts", "unknown"

parties: list of up to 4 party names found

key_dates: list of objects each with label, date,
importance fields

filing_deadline: date string if found, "none" if not
applicable, "unknown" if unclear

estimated_complexity: one of: simple, moderate, complex

detected_language: one of: en, es, unknown

red_flag_preview: list of up to 3 brief strings noting
immediate concerns

confidence: float 0.0 to 1.0

Document text:
{text_sample}"""

        for attempt in range(2):
            try:
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=1024,
                    system=[{
                        "type": "text",
                        "text": SYSTEM_PROMPT,
                        "cache_control": {
                            "type": "ephemeral"}
                    }],
                    messages=[{
                        "role": "user",
                        "content": (
                            "Return ONLY a JSON object. "
                            "No other text. " + user_prompt
                            if attempt > 0
                            else user_prompt)
                    }]
                )
                raw = response.content[0].text.strip()
                if raw.startswith("```"):
                    raw = raw.split("```")[1]
                    if raw.startswith("json"):
                        raw = raw[4:]
                return json.loads(raw)
            except (json.JSONDecodeError, Exception):
                if attempt == 1:
                    return self._default()
        return self._default()

    def _default(self) -> dict:
        return {
            "document_category": "unknown",
            "document_type": "unknown",
            "jurisdiction_type": "unknown",
            "jurisdiction_name": "unknown",
            "issuing_agency": "unknown",
            "parties": [],
            "key_dates": [],
            "filing_deadline": "unknown",
            "estimated_complexity": "simple",
            "detected_language": "en",
            "red_flag_preview": [],
            "confidence": 0.0
        }

    def get_price_tier(self, document: dict) -> dict:
        tokens = document.get("token_estimate", 0)
        if tokens < 4000:
            return {"tier": "small", "price_usd": 5,
                    "label": "Short document (under 5 pages)"}
        elif tokens <= 12000:
            return {"tier": "medium", "price_usd": 10,
                    "label": "Standard document (5-15 pages)"}
        else:
            return {"tier": "large", "price_usd": 15,
                    "label": "Complex document (15+ pages)"}
```

**Phase 3 verification — create and run backend/test_phase3.py:**

```python
import asyncio, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.agents.classifier import ClassifierAgent

lease_doc = {
    "text": (
        "RESIDENTIAL LEASE AGREEMENT "
        "This lease is between Landlord Robert Johnson and "
        "Tenant Sarah Williams for 456 Oak St Miami FL 33101. "
        "Monthly rent $2200 due on the 1st. Late fee $200 "
        "after 5 days. Term 12 months starting March 1 2026. "
        "AUTO-RENEWAL: Lease renews automatically unless 60 "
        "days notice given. ARBITRATION: All disputes subject "
        "to binding arbitration, tenant waives jury trial."
    ),
    "token_estimate": 500,
    "language": "en"
}

criminal_doc = {
    "text": (
        "STATE OF FLORIDA vs DEFENDANT "
        "CRIMINAL COMPLAINT MISDEMEANOR "
        "You are hereby charged with Petit Theft First Degree "
        "Misdemeanor Florida Statute 812.014. "
        "Date of alleged offense February 10 2026. "
        "You must appear before Judge Martinez at Broward "
        "County Courthouse Room 4B on March 15 2026 at 9AM. "
        "Failure to appear will result in a warrant."
    ),
    "token_estimate": 300,
    "language": "en"
}

small_claims_doc = {
    "text": (
        "SMALL CLAIMS COURT COMPLAINT "
        "Plaintiff Maria Gonzalez 789 Palm Ave Stuart FL 34994 "
        "Defendant Quick Fix Contractors LLC 321 US-1 Stuart FL "
        "Amount claimed $3500.00 "
        "Reason Contractor accepted payment for roof repair work "
        "completed January 2026. Work was defective and caused "
        "water damage. Contractor refused to remedy."
    ),
    "token_estimate": 300,
    "language": "en"
}

async def run():
    agent = ClassifierAgent()

    print("Classifying lease...")
    lease = await agent.classify(lease_doc)
    print(f"  category: {lease['document_category']}")
    print(f"  confidence: {lease['confidence']}")
    assert lease["document_category"] in [
        "real_estate", "contract", "agreement"], (
        f"Lease wrong category: {lease['document_category']}")

    print("Classifying criminal document...")
    crim = await agent.classify(criminal_doc)
    print(f"  category: {crim['document_category']}")
    assert crim["document_category"] in [
        "criminal_charge", "criminal_summons"], (
        f"Criminal wrong: {crim['document_category']}")

    print("Classifying small claims...")
    sc = await agent.classify(small_claims_doc)
    print(f"  category: {sc['document_category']}")
    assert "small_claims" in sc["document_category"] or \
           sc["document_category"] == "court_filing", (
        f"Small claims wrong: {sc['document_category']}")

    tier = agent.get_price_tier({"token_estimate": 500})
    assert tier["tier"] == "small"
    tier2 = agent.get_price_tier({"token_estimate": 8000})
    assert tier2["tier"] == "medium"
    tier3 = agent.get_price_tier({"token_estimate": 20000})
    assert tier3["tier"] == "large"
    print("Price tiers OK")

    print("\nALL PHASE 3 ASSERTIONS PASSED")

asyncio.run(run())
```

Run: `cd ~/legalclear/backend && uv run python test_phase3.py`
All assertions must pass.
Print "PHASE 3 COMPLETE — all checks passed." then continue.

---

## Phase 4 — Explainer agent

Work in backend/src/agents/explainer.py.

```python
import json
from anthropic import Anthropic
from src.core.config import settings
from src.core.disclaimer import get_disclaimer

SYSTEM_PROMPT = (
    "You are a plain language legal document explainer "
    "for LegalClear. Your job is to help ordinary people "
    "with no legal background understand legal documents "
    "clearly and accurately. You use simple everyday language. "
    "You never use legal jargon without immediately explaining "
    "it in parentheses. You are thorough, warm, and clear. "
    "You never give legal advice — you explain what documents "
    "say, not what people should do. When the user's language "
    "is Spanish, respond entirely in Spanish including all "
    "JSON field values. Return valid JSON only. "
    "No preamble. No markdown. JSON only."
)


class ExplainerAgent:

    def __init__(self):
        self.client = Anthropic(
            api_key=settings.ANTHROPIC_API_KEY)
        self.model = "claude-sonnet-4-6"

    async def explain(self, document: dict,
                      classification: dict,
                      lang: str = "en") -> dict:
        spanish = (
            "Respond entirely in Spanish. "
            "All JSON values must be in Spanish."
            if lang == "es" else ""
        )

        user_prompt = f"""Language: {lang}
{spanish}
Document type: {classification.get("document_type")}
Category: {classification.get("document_category")}
Jurisdiction: {classification.get("jurisdiction_name")}
Parties: {", ".join(classification.get("parties", []))}
Complexity: {classification.get("estimated_complexity")}

Explain this document in plain language.
Return JSON with exactly these fields:

summary: 2-3 sentence plain language summary

what_this_means_for_you: 3-5 sentences on real-world
impact — what the reader agrees to, rights they have,
obligations they take on

key_sections: list of 5-8 most important sections, each
with: title, plain_explanation, importance
(one of: high, medium, low)

important_numbers: list of dollar amounts, percentages,
timeframes, deadlines, each with: label, value, context

your_rights: list of strings describing reader rights

your_obligations: list of strings describing obligations

questions_to_ask: list of 3-5 smart questions to ask
before signing or responding

Document text:
{document.get("text", "")[:80000]}"""

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                system=[{
                    "type": "text",
                    "text": SYSTEM_PROMPT,
                    "cache_control": {"type": "ephemeral"}
                }],
                messages=[{
                    "role": "user",
                    "content": user_prompt
                }]
            )
            raw = response.content[0].text.strip()
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            result = json.loads(raw)
            result["disclaimer"] = get_disclaimer(
                lang, "standard")
            result["language"] = lang
            return result
        except Exception as e:
            return {
                "error": True,
                "message": str(e),
                "disclaimer": get_disclaimer(
                    lang, "standard"),
                "language": lang
            }

    async def answer_question(
            self, document: dict,
            classification: dict,
            explanation: dict,
            question: str,
            chat_history: list,
            lang: str = "en") -> dict:
        spanish = (
            "Respond entirely in Spanish."
            if lang == "es" else ""
        )

        messages = [
            {
                "role": "user",
                "content": (
                    f"Document type: "
                    f"{classification.get('document_type')}\n"
                    f"Jurisdiction: "
                    f"{classification.get('jurisdiction_name')}\n"
                    f"Summary: "
                    f"{explanation.get('summary', '')}\n\n"
                    f"Document text:\n"
                    f"{document.get('text', '')[:40000]}"
                )
            },
            {
                "role": "assistant",
                "content": (
                    "I have read and understood the document. "
                    "I am ready to answer questions about it "
                    "in plain language."
                )
            }
        ]

        for msg in chat_history:
            messages.append({
                "role": msg.get("role", "user"),
                "content": msg.get("content", "")
            })

        messages.append({
            "role": "user",
            "content": f"{spanish}\n{question}"
        })

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1024,
                system=[{
                    "type": "text",
                    "text": SYSTEM_PROMPT,
                    "cache_control": {"type": "ephemeral"}
                }],
                messages=messages
            )
            answer_text = response.content[0].text.strip()
            try:
                parsed = json.loads(answer_text)
                answer = parsed.get("answer", answer_text)
                confidence = parsed.get(
                    "confidence", "medium")
            except Exception:
                answer = answer_text
                confidence = "medium"
            return {
                "answer": answer,
                "confidence": confidence,
                "disclaimer": get_disclaimer(lang, "short"),
                "language": lang
            }
        except Exception as e:
            return {
                "answer": (
                    "Lo siento, no pude procesar su pregunta."
                    if lang == "es"
                    else "Sorry, I could not process "
                         "your question."),
                "confidence": "low",
                "disclaimer": get_disclaimer(lang, "short"),
                "language": lang,
                "error": str(e)
            }
```

**Phase 4 verification — create and run backend/test_phase4.py:**

```python
import asyncio, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.ingestion import ingest_document
from src.agents.classifier import ClassifierAgent
from src.agents.explainer import ExplainerAgent

async def run():
    classifier = ClassifierAgent()
    explainer = ExplainerAgent()

    with open("test_lease.pdf", "rb") as f:
        data = f.read()

    doc = await ingest_document(data, "test_lease.pdf")
    assert not doc.get("error")

    classification = await classifier.classify(doc)
    print(f"Category: {classification['document_category']}")

    explanation = await explainer.explain(
        doc, classification, "en")

    assert not explanation.get("error"), (
        f"Explainer error: {explanation.get('message')}")
    assert "summary" in explanation
    assert "your_rights" in explanation
    assert "disclaimer" in explanation
    assert explanation["language"] == "en"

    print(f"Summary: {explanation['summary'][:150]}")
    print(f"Rights count: {len(explanation.get('your_rights',[]))}")

    qa = await explainer.answer_question(
        doc, classification, explanation,
        "What happens if I pay my rent late?",
        [], "en")
    assert "answer" in qa
    assert len(qa["answer"]) > 20
    assert "disclaimer" in qa
    print(f"Q&A answer: {qa['answer'][:150]}")

    es_explanation = await explainer.explain(
        doc, classification, "es")
    assert es_explanation.get("language") == "es"
    assert "disclaimer" in es_explanation
    print(f"ES summary: {es_explanation.get('summary','')[:100]}")

    print("\nALL PHASE 4 ASSERTIONS PASSED")

asyncio.run(run())
```

Run: `cd ~/legalclear/backend && uv run python test_phase4.py`
All assertions must pass.
Print "PHASE 4 COMPLETE — all checks passed." then continue.

---

## Phase 5 — Form guide agent

Work in backend/src/agents/form_guide.py.

```python
import json, os
from anthropic import Anthropic
from src.core.config import settings
from src.core.disclaimer import get_disclaimer

SYSTEM_PROMPT = (
    "You are a government and court form completion guide "
    "for LegalClear. You help ordinary people fill out legal "
    "and government forms correctly and completely. You explain "
    "each field in plain language. You know requirements for "
    "federal and state forms across all 50 US states. You flag "
    "common mistakes. You tell people exactly what to write. "
    "You never give legal advice. When the user's language is "
    "Spanish, respond entirely in Spanish. Return valid JSON "
    "only. No preamble. No markdown. JSON only."
)


class FormGuideAgent:

    def __init__(self):
        self.client = Anthropic(
            api_key=settings.ANTHROPIC_API_KEY)
        self.model = "claude-sonnet-4-6"
        self._load_forms_library()

    def _load_forms_library(self):
        path = os.path.join(
            os.path.dirname(__file__),
            "../data/forms_library.json")
        try:
            with open(path) as f:
                self.forms_library = json.load(f)
        except Exception:
            self.forms_library = {}

    async def guide(self, document: dict,
                    classification: dict,
                    lang: str = "en") -> dict:
        spanish = (
            "Respond entirely in Spanish. "
            "All JSON values must be in Spanish."
            if lang == "es" else ""
        )
        doc_type = classification.get("document_type", "")
        form_meta = self.forms_library.get(doc_type, {})
        official_url = form_meta.get("official_url", "")

        user_prompt = f"""Language: {lang}
{spanish}
Form type: {classification.get("document_type")}
Issuing agency: {classification.get("issuing_agency")}
Jurisdiction: {classification.get("jurisdiction_name")}
Filing deadline: {classification.get("filing_deadline")}
Official URL if known: {official_url}

Create a complete field-by-field completion guide.
Return JSON with exactly these fields:

form_overview: string explaining what this form is,
why people file it, what it does

before_you_start: list of strings for docs to gather

sections: list of section objects, each with:
  section_name, description, and fields list where
  each field has: field_name, field_number,
  plain_label, instructions, example,
  common_mistakes, required (boolean)

where_to_file: object with: methods (list),
address, online_url, fee, copies_needed, what_to_keep

after_filing: list of strings for next steps

deadline_warning: string if deadline is real, null if none

small_claims_hearing_tips: list of strings if small
claims document, null otherwise

Document text:
{document.get("text", "")[:80000]}"""

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                system=[{
                    "type": "text",
                    "text": SYSTEM_PROMPT,
                    "cache_control": {"type": "ephemeral"}
                }],
                messages=[{
                    "role": "user",
                    "content": user_prompt
                }]
            )
            raw = response.content[0].text.strip()
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            result = json.loads(raw)
            result["disclaimer"] = get_disclaimer(
                lang, "standard")
            return result
        except Exception as e:
            return {"error": True, "message": str(e),
                    "disclaimer": get_disclaimer(
                        lang, "standard")}

    async def answer_form_question(
            self, document: dict,
            classification: dict,
            guide: dict, question: str,
            chat_history: list,
            lang: str = "en") -> dict:
        spanish = (
            "Respond entirely in Spanish."
            if lang == "es" else ""
        )
        context = (
            f"Form type: "
            f"{classification.get('document_type')}\n"
            f"Jurisdiction: "
            f"{classification.get('jurisdiction_name')}\n"
            f"Form overview: "
            f"{guide.get('form_overview', '')}\n\n"
            f"Document text:\n"
            f"{document.get('text', '')[:30000]}"
        )
        messages = [
            {"role": "user", "content": context},
            {"role": "assistant",
             "content": (
                 "I have reviewed this form and its "
                 "completion guide. Ready to answer "
                 "questions about how to fill it out.")}
        ]
        for msg in chat_history:
            messages.append({
                "role": msg.get("role", "user"),
                "content": msg.get("content", "")
            })
        messages.append({
            "role": "user",
            "content": f"{spanish}\n{question}"
        })
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1024,
                system=[{
                    "type": "text",
                    "text": SYSTEM_PROMPT,
                    "cache_control": {"type": "ephemeral"}
                }],
                messages=messages
            )
            answer = response.content[0].text.strip()
            return {
                "answer": answer,
                "confidence": "high",
                "disclaimer": get_disclaimer(lang, "short"),
                "language": lang
            }
        except Exception as e:
            return {
                "answer": (
                    "No pude procesar su pregunta."
                    if lang == "es"
                    else "Could not process your question."),
                "confidence": "low",
                "disclaimer": get_disclaimer(lang, "short"),
                "language": lang,
                "error": str(e)
            }
```

**Phase 5 verification — create and run backend/test_phase5.py:**

```python
import asyncio, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.agents.form_guide import FormGuideAgent

small_claims_text = """
SMALL CLAIMS COURT COMPLAINT FORM
Martin County Court Stuart Florida
Case Number: _______________
Plaintiff Full Legal Name: _______________
Plaintiff Street Address: _______________
Plaintiff City State Zip: _______________
Plaintiff Phone: _______________
Defendant Full Legal Name or Business: _______________
Defendant Address: _______________
Amount Claimed max 8000: $_______________
Date of Incident: _______________
Description of Claim: _______________
Plaintiff Signature: _______________ Date: ______
"""

document = {"text": small_claims_text, "language": "en"}
classification = {
    "document_category": "small_claims_complaint",
    "document_type": "small_claims_complaint_florida",
    "jurisdiction_name": "Florida",
    "issuing_agency": "Martin County Court",
    "filing_deadline": "unknown",
    "estimated_complexity": "simple"
}

async def run():
    agent = FormGuideAgent()

    guide = await agent.guide(document, classification, "en")
    assert not guide.get("error"), (
        f"Guide error: {guide.get('message')}")
    assert "form_overview" in guide
    assert "sections" in guide
    assert "where_to_file" in guide
    assert "disclaimer" in guide
    print(f"Form overview: {guide['form_overview'][:150]}")
    print(f"Sections count: {len(guide.get('sections', []))}")

    qa = await agent.answer_form_question(
        document, classification, guide,
        "Where do I file this form and how much does it cost?",
        [], "en")
    assert "answer" in qa
    assert len(qa["answer"]) > 20
    print(f"Q&A: {qa['answer'][:150]}")

    print("\nALL PHASE 5 ASSERTIONS PASSED")

asyncio.run(run())
```

Run: `cd ~/legalclear/backend && uv run python test_phase5.py`
All assertions must pass.
Print "PHASE 5 COMPLETE — all checks passed." then continue.

---

## Phase 6 — Risk scanner agent

Work in backend/src/agents/risk_scanner.py.

```python
import json
from anthropic import Anthropic
from src.core.config import settings
from src.core.disclaimer import get_disclaimer

SYSTEM_PROMPT = (
    "You are a legal document risk scanner for LegalClear. "
    "You identify clauses and terms that are unusual, "
    "potentially harmful, one-sided, or worth careful "
    "attention. You score risk clearly using RED, YELLOW, "
    "or GREEN. You explain why each item matters in plain "
    "language a non-lawyer can understand. You are thorough, "
    "direct, and never alarmist. When the user's language is "
    "Spanish, respond entirely in Spanish. Return valid JSON "
    "only. No preamble. No markdown. JSON only.\n\n"
    "RED = significantly harmful, one-sided, or dangerous\n"
    "YELLOW = unusual, worth negotiating, needs attention\n"
    "GREEN = standard, fair, and reasonable"
)


class RiskScannerAgent:

    def __init__(self):
        self.client = Anthropic(
            api_key=settings.ANTHROPIC_API_KEY)
        self.model = "claude-haiku-4-5-20251001"

    async def scan(self, document: dict,
                   classification: dict,
                   lang: str = "en") -> dict:
        spanish = (
            "Respond entirely in Spanish. "
            "All JSON values must be in Spanish."
            if lang == "es" else ""
        )

        user_prompt = f"""Language: {lang}
{spanish}
Document type: {classification.get("document_type")}
Category: {classification.get("document_category")}
Jurisdiction: {classification.get("jurisdiction_name")}

Scan this document for risk. Return JSON with:

overall_risk_level: one of: LOW, MEDIUM, HIGH

risk_summary: 2-3 sentence plain language assessment

clauses: list of objects each with:
  clause_title, risk_level (RED/YELLOW/GREEN),
  what_it_says, why_it_matters, what_to_do,
  quote (max 100 chars verbatim)

missing_protections: list of objects each with:
  protection_name, why_important, what_to_ask_for

red_count: integer
yellow_count: integer
green_count: integer

top_concerns: list of exactly 3 strings in order
of severity

negotiation_tips: list of tips if signable contract,
empty list otherwise

Document text:
{document.get("text", "")[:60000]}"""

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                system=[{
                    "type": "text",
                    "text": SYSTEM_PROMPT,
                    "cache_control": {"type": "ephemeral"}
                }],
                messages=[{
                    "role": "user",
                    "content": user_prompt
                }]
            )
            raw = response.content[0].text.strip()
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            result = json.loads(raw)
            result["disclaimer"] = get_disclaimer(
                lang, "standard")
            return result
        except Exception as e:
            return {"error": True, "message": str(e),
                    "disclaimer": get_disclaimer(
                        lang, "standard")}
```

**Phase 6 verification — create and run backend/test_phase6.py:**

```python
import asyncio, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.agents.risk_scanner import RiskScannerAgent

risky_contract = """
COMMERCIAL LEASE AGREEMENT

AUTO-RENEWAL CLAUSE: This lease automatically renews for
one-year terms without any notice required from either party.

BINDING ARBITRATION: Tenant permanently and irrevocably
waives the right to a jury trial. All disputes must be
resolved through binding arbitration selected solely by
Landlord.

TERMINATION: Landlord may terminate this lease at any time
for any reason with 3 days notice. Tenant may only terminate
with 90 days written notice.

PERSONAL GUARANTEE: Tenant personally guarantees all
obligations under this lease including amounts owed by any
business entity.

RENT INCREASES: Landlord may increase rent at any time with
7 days notice.

INSPECTION: Landlord may enter the premises at any time
without notice for any reason.
"""

document = {"text": risky_contract, "language": "en"}
classification = {
    "document_category": "contract",
    "document_type": "commercial_lease",
    "jurisdiction_name": "Florida",
    "estimated_complexity": "moderate"
}

async def run():
    agent = RiskScannerAgent()
    result = await agent.scan(document, classification, "en")

    assert not result.get("error"), (
        f"Scanner error: {result.get('message')}")
    assert "overall_risk_level" in result
    assert "clauses" in result
    assert "red_count" in result
    assert "disclaimer" in result

    print(f"Overall risk: {result['overall_risk_level']}")
    print(f"Red: {result['red_count']} "
          f"Yellow: {result['yellow_count']} "
          f"Green: {result['green_count']}")
    for c in result.get("clauses", []):
        print(f"  {c['risk_level']}: {c['clause_title']}")

    assert result["overall_risk_level"] == "HIGH", (
        f"Expected HIGH got {result['overall_risk_level']}")
    assert result["red_count"] >= 2, (
        f"Expected >= 2 red, got {result['red_count']}")
    assert len(result.get("missing_protections", [])) >= 1

    print("\nALL PHASE 6 ASSERTIONS PASSED")

asyncio.run(run())
```

Run: `cd ~/legalclear/backend && uv run python test_phase6.py`
All assertions must pass.
Print "PHASE 6 COMPLETE — all checks passed." then continue.

---

## Phase 7 — Expungement agent

Work in backend/src/agents/expungement.py.

```python
import json
from anthropic import Anthropic
from src.core.config import settings
from src.core.disclaimer import get_disclaimer

GUIDE_SYSTEM_PROMPT = (
    "You are an expungement petition guide for LegalClear. "
    "You help people understand the expungement process and "
    "fill out expungement petitions correctly. Expungement "
    "seals or clears a criminal record, giving people a fresh "
    "start in employment, housing, and professional licensing. "
    "You explain every step clearly in plain language. You know "
    "expungement laws for all 50 US states. You never give "
    "legal advice. When the user's language is Spanish, respond "
    "entirely in Spanish. Return valid JSON only. "
    "No preamble. No markdown. JSON only."
)

ELIGIBILITY_SYSTEM_PROMPT = (
    "You are a preliminary expungement eligibility assessor "
    "for LegalClear. You provide general eligibility estimates "
    "based on jurisdiction, offense type, and time elapsed. "
    "You are always clear this is preliminary only and not "
    "legal advice. Individual circumstances vary. Always "
    "recommend verifying with the court. Return valid JSON "
    "only. No preamble. No markdown. JSON only."
)


class ExpungementAgent:

    def __init__(self):
        self.client = Anthropic(
            api_key=settings.ANTHROPIC_API_KEY)
        self.guide_model = "claude-sonnet-4-6"
        self.eligibility_model = "claude-haiku-4-5-20251001"

    async def guide(self, document: dict,
                    classification: dict,
                    lang: str = "en") -> dict:
        spanish = (
            "Respond entirely in Spanish. "
            "All JSON values must be in Spanish."
            if lang == "es" else ""
        )
        jurisdiction = classification.get(
            "jurisdiction_name", "unknown")

        user_prompt = f"""Language: {lang}
{spanish}
Jurisdiction: {jurisdiction}
Document type: expungement_petition

Return JSON with:

what_is_expungement: plain language explanation of what
expungement does and why it matters

eligibility_overview: general criteria for {jurisdiction},
always note eligibility varies by case

before_you_start: list of documents and info to gather

steps: list of step objects each with:
  step_number, title, instructions, tips,
  estimated_time, cost

form_fields: list of field objects each with:
  field_name, plain_label, instructions,
  example, common_mistakes, required

where_to_file: object with: court_type, methods,
address_note, online_url, fee, fee_waiver_note

after_filing: list of strings

what_changes_after: list of concrete improvements
after successful expungement

what_does_not_change: list of important limitations

free_resources: list of objects each with:
  label, url, description
Always include expungement.com and lawhelp.org

Document text:
{document.get("text", "")[:80000]}"""

        try:
            response = self.client.messages.create(
                model=self.guide_model,
                max_tokens=4096,
                system=[{
                    "type": "text",
                    "text": GUIDE_SYSTEM_PROMPT,
                    "cache_control": {"type": "ephemeral"}
                }],
                messages=[{
                    "role": "user",
                    "content": user_prompt
                }]
            )
            raw = response.content[0].text.strip()
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            result = json.loads(raw)
            result["disclaimer"] = get_disclaimer(
                lang, "standard")
            return result
        except Exception as e:
            return {"error": True, "message": str(e),
                    "disclaimer": get_disclaimer(
                        lang, "standard")}

    async def check_eligibility(
            self, jurisdiction: str,
            offense_description: str,
            years_since_offense: int,
            lang: str = "en") -> dict:
        spanish = (
            "Respond entirely in Spanish."
            if lang == "es" else ""
        )

        user_prompt = f"""Language: {lang}
{spanish}
Jurisdiction: {jurisdiction}
Offense: {offense_description}
Years since offense: {years_since_offense}

Return JSON with:
likely_eligible: boolean
confidence: one of: high, medium, low
reasoning: plain language explanation
key_factors: list of strings
next_steps: list of strings
disclaimer: always include that this is preliminary
only and not legal advice"""

        try:
            response = self.client.messages.create(
                model=self.eligibility_model,
                max_tokens=1024,
                system=[{
                    "type": "text",
                    "text": ELIGIBILITY_SYSTEM_PROMPT,
                    "cache_control": {"type": "ephemeral"}
                }],
                messages=[{
                    "role": "user",
                    "content": user_prompt
                }]
            )
            raw = response.content[0].text.strip()
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            return json.loads(raw)
        except Exception as e:
            return {
                "likely_eligible": False,
                "confidence": "low",
                "reasoning": (
                    "Could not assess eligibility."),
                "key_factors": [],
                "next_steps": [
                    "Contact your local legal aid office",
                    "Visit https://www.lawhelp.org"
                ],
                "disclaimer": get_disclaimer(
                    lang, "standard"),
                "error": str(e)
            }
```

**Phase 7 verification — create and run backend/test_phase7.py:**

```python
import asyncio, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.agents.expungement import ExpungementAgent

expungement_text = """
PETITION FOR EXPUNGEMENT OF CRIMINAL RECORD
Petitioner: James Robert Williams
Case Number: 2019-MM-014521-A
Court: Palm Beach County Court
Offense: Misdemeanor Petit Theft First Offense
Florida Statute 812.014(2)(e)
Date of Offense: August 3 2019
Disposition: Guilty Plea Probation 12 months
Probation Completed: August 3 2020
All fines paid: Yes
Adjudication withheld: Yes
"""

document = {"text": expungement_text, "language": "en"}
classification = {
    "document_category": "expungement_petition",
    "document_type": "expungement_petition_florida",
    "jurisdiction_name": "Florida",
    "estimated_complexity": "moderate"
}

async def run():
    agent = ExpungementAgent()

    guide = await agent.guide(document, classification, "en")
    assert not guide.get("error"), (
        f"Guide error: {guide.get('message')}")
    assert "what_is_expungement" in guide
    assert "steps" in guide
    assert "what_changes_after" in guide
    assert "disclaimer" in guide
    print(f"Steps count: {len(guide.get('steps', []))}")
    print(f"Changes: "
          f"{guide.get('what_changes_after', ['none'])[0]}")

    elig = await agent.check_eligibility(
        "Florida", "misdemeanor petit theft first offense",
        6, "en")
    assert "likely_eligible" in elig
    assert "confidence" in elig
    assert "reasoning" in elig
    print(f"Eligible: {elig['likely_eligible']} "
          f"Confidence: {elig['confidence']}")
    print(f"Reasoning: {elig['reasoning'][:150]}")

    elig_es = await agent.check_eligibility(
        "Florida", "misdemeanor petit theft", 6, "es")
    assert "likely_eligible" in elig_es
    print(f"ES reasoning: "
          f"{elig_es.get('reasoning', '')[:100]}")

    print("\nALL PHASE 7 ASSERTIONS PASSED")

asyncio.run(run())
```

Run: `cd ~/legalclear/backend && uv run python test_phase7.py`
All assertions must pass.
Print "PHASE 7 COMPLETE — all checks passed." then continue.

---

## Phase 8 — Memory layer

Work in backend/src/memory/db.py.

**IMPORTANT: Print the following SQL block first so the
user can run it in the Supabase dashboard before this
phase's code is tested.**

```
PRINT THIS SQL EXACTLY:
=========================================
-- Run this entire block in Supabase SQL editor --

CREATE TABLE IF NOT EXISTS users (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  created_at timestamptz DEFAULT now(),
  email text UNIQUE,
  stripe_customer_id text,
  subscription_status text DEFAULT 'free',
  subscription_id text,
  free_doc_used boolean DEFAULT false,
  preferred_language text DEFAULT 'en',
  expo_push_token text
);

CREATE TABLE IF NOT EXISTS sessions (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  created_at timestamptz DEFAULT now(),
  user_id uuid REFERENCES users(id),
  stripe_payment_intent text,
  stripe_subscription_id text,
  payment_status text DEFAULT 'pending',
  payment_type text,
  document_filename text,
  document_token_count int,
  price_tier text,
  price_paid_usd numeric DEFAULT 0
);

CREATE TABLE IF NOT EXISTS documents (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id uuid REFERENCES sessions(id),
  created_at timestamptz DEFAULT now(),
  classification jsonb,
  explanation jsonb,
  form_guide jsonb,
  risk_scan jsonb,
  expungement_guide jsonb,
  escalation jsonb,
  language text DEFAULT 'en',
  status text DEFAULT 'processing',
  document_text text
);

CREATE TABLE IF NOT EXISTS chat_messages (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  document_id uuid REFERENCES documents(id),
  created_at timestamptz DEFAULT now(),
  role text,
  content text,
  language text DEFAULT 'en'
);

CREATE TABLE IF NOT EXISTS usage_stats (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  created_at timestamptz DEFAULT now(),
  document_category text,
  jurisdiction text,
  language text,
  price_tier text,
  processing_time_seconds float
);

CREATE TABLE IF NOT EXISTS push_tokens (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid REFERENCES users(id),
  expo_token text UNIQUE,
  platform text,
  created_at timestamptz DEFAULT now()
);
=========================================
```

Then build the DatabaseManager class:

```python
from src.core.config import settings


class DatabaseManager:

    def __init__(self):
        from supabase import create_client
        self.client = create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_SERVICE_KEY
        )

    def get_or_create_user(
            self, email: str,
            preferred_language: str = "en") -> dict:
        result = (self.client.table("users")
                  .select("*").eq("email", email)
                  .execute())
        if result.data:
            return result.data[0]
        new_user = (self.client.table("users")
                    .insert({"email": email,
                             "preferred_language":
                             preferred_language})
                    .execute())
        return new_user.data[0]

    def update_user_subscription(
            self, user_id: str, status: str,
            subscription_id: str = None) -> dict:
        update = {"subscription_status": status}
        if subscription_id:
            update["subscription_id"] = subscription_id
        result = (self.client.table("users")
                  .update(update)
                  .eq("id", user_id).execute())
        return result.data[0] if result.data else {}

    def get_user(self, user_id: str) -> dict:
        result = (self.client.table("users")
                  .select("*").eq("id", user_id)
                  .execute())
        return result.data[0] if result.data else {}

    def mark_free_doc_used(self, user_id: str):
        self.client.table("users").update(
            {"free_doc_used": True}
        ).eq("id", user_id).execute()

    def save_push_token(
            self, user_id: str,
            expo_token: str,
            platform: str) -> dict:
        result = (self.client.table("push_tokens")
                  .upsert({"user_id": user_id,
                           "expo_token": expo_token,
                           "platform": platform})
                  .execute())
        return result.data[0] if result.data else {}

    def create_session(
            self, user_id: str, filename: str,
            token_count: int, price_tier: str,
            price_usd: float,
            payment_type: str) -> str:
        result = (self.client.table("sessions")
                  .insert({
                      "user_id": user_id,
                      "document_filename": filename,
                      "document_token_count": token_count,
                      "price_tier": price_tier,
                      "price_paid_usd": price_usd,
                      "payment_type": payment_type
                  }).execute())
        return result.data[0]["id"]

    def update_payment_status(
            self, session_id: str, status: str,
            payment_intent: str = None,
            subscription_id: str = None):
        update = {"payment_status": status}
        if payment_intent:
            update["stripe_payment_intent"] = (
                payment_intent)
        if subscription_id:
            update["stripe_subscription_id"] = (
                subscription_id)
        self.client.table("sessions").update(
            update).eq("id", session_id).execute()

    def get_session(self, session_id: str) -> dict:
        result = (self.client.table("sessions")
                  .select("*").eq("id", session_id)
                  .execute())
        return result.data[0] if result.data else {}

    def create_document(
            self, session_id: str,
            document_text: str = "") -> str:
        result = (self.client.table("documents")
                  .insert({
                      "session_id": session_id,
                      "document_text": document_text,
                      "status": "processing"
                  }).execute())
        return result.data[0]["id"]

    def save_results(
            self, document_id: str,
            classification: dict,
            explanation: dict,
            form_guide: dict,
            risk_scan: dict,
            expungement_guide: dict,
            escalation: dict,
            language: str):
        self.client.table("documents").update({
            "classification": classification,
            "explanation": explanation,
            "form_guide": form_guide,
            "risk_scan": risk_scan,
            "expungement_guide": expungement_guide,
            "escalation": escalation,
            "language": language,
            "status": "complete"
        }).eq("id", document_id).execute()

    def update_document_status(
            self, document_id: str,
            status: str):
        self.client.table("documents").update(
            {"status": status}
        ).eq("id", document_id).execute()

    def get_document(self, document_id: str) -> dict:
        result = (self.client.table("documents")
                  .select("*").eq("id", document_id)
                  .execute())
        return result.data[0] if result.data else {}

    def get_user_documents(
            self, user_id: str,
            limit: int = 20) -> list:
        result = (self.client.table("documents")
                  .select("*, sessions!inner(user_id)")
                  .eq("sessions.user_id", user_id)
                  .order("created_at", desc=True)
                  .limit(limit).execute())
        return result.data if result.data else []

    def save_message(
            self, document_id: str,
            role: str, content: str,
            language: str = "en") -> str:
        result = (self.client.table("chat_messages")
                  .insert({
                      "document_id": document_id,
                      "role": role,
                      "content": content,
                      "language": language
                  }).execute())
        return result.data[0]["id"]

    def get_history(
            self, document_id: str) -> list:
        result = (self.client.table("chat_messages")
                  .select("*")
                  .eq("document_id", document_id)
                  .order("created_at", desc=False)
                  .execute())
        return result.data if result.data else []

    def log_usage(
            self, category: str,
            jurisdiction: str, language: str,
            price_tier: str,
            processing_time: float):
        self.client.table("usage_stats").insert({
            "document_category": category,
            "jurisdiction": jurisdiction,
            "language": language,
            "price_tier": price_tier,
            "processing_time_seconds": processing_time
        }).execute()
```

**Phase 8 verification:**

The DatabaseManager requires live Supabase credentials.
Run this structural check instead:

```python
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import inspect
from src.memory.db import DatabaseManager

methods = [
    "get_or_create_user", "update_user_subscription",
    "get_user", "mark_free_doc_used", "save_push_token",
    "create_session", "update_payment_status",
    "get_session", "create_document", "save_results",
    "update_document_status", "get_document",
    "get_user_documents", "save_message",
    "get_history", "log_usage"
]

for method in methods:
    assert hasattr(DatabaseManager, method), (
        f"Missing method: {method}")
    print(f"  {method}: OK")

print("\nALL PHASE 8 STRUCTURAL CHECKS PASSED")
print("NOTE: Run SQL in Supabase dashboard before")
print("testing live database operations.")
```

Run: `cd ~/legalclear/backend && uv run python test_phase8.py`
All structural checks must pass.
Print "PHASE 8 COMPLETE — all checks passed." then continue.

---

## Phase 9 — Payments

Work in backend/src/payments/stripe_client.py
and backend/src/payments/__init__.py.

### payments/stripe_client.py

```python
import stripe
from src.core.config import settings

stripe.api_key = settings.STRIPE_SECRET_KEY


class StripeClient:

    def create_payment_intent(
            self, price_usd: int,
            session_id: str, user_email: str,
            metadata: dict = None) -> dict:
        intent = stripe.PaymentIntent.create(
            amount=price_usd * 100,
            currency="usd",
            receipt_email=user_email,
            metadata={
                "session_id": session_id,
                **(metadata or {})
            }
        )
        return {
            "client_secret": intent.client_secret,
            "payment_intent_id": intent.id
        }

    def create_subscription_checkout(
            self, user_email: str,
            user_id: str,
            success_url: str,
            cancel_url: str) -> dict:
        customer_id = self.create_or_get_customer(
            user_email)
        session = stripe.checkout.Session.create(
            customer=customer_id,
            payment_method_types=["card"],
            line_items=[{
                "price": (
                    settings.STRIPE_SUBSCRIPTION_PRICE_ID),
                "quantity": 1
            }],
            mode="subscription",
            success_url=success_url,
            cancel_url=cancel_url,
            metadata={"user_id": user_id}
        )
        return {
            "checkout_url": session.url,
            "session_id": session.id
        }

    def create_or_get_customer(
            self, email: str) -> str:
        customers = stripe.Customer.list(
            email=email, limit=1)
        if customers.data:
            return customers.data[0].id
        customer = stripe.Customer.create(email=email)
        return customer.id

    def cancel_subscription(
            self, subscription_id: str) -> bool:
        try:
            stripe.Subscription.modify(
                subscription_id,
                cancel_at_period_end=True)
            return True
        except Exception:
            return False

    def verify_webhook(
            self, payload: bytes,
            sig_header: str) -> dict:
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header,
                settings.STRIPE_WEBHOOK_SECRET)
            return event
        except stripe.error.SignatureVerificationError:
            raise ValueError(
                "Invalid webhook signature")

    def get_payment_status(
            self, payment_intent_id: str) -> str:
        intent = stripe.PaymentIntent.retrieve(
            payment_intent_id)
        return intent.status
```

### payments/__init__.py

```python
def check_access(user: dict,
                 session: dict = None) -> dict:
    sub_status = user.get(
        "subscription_status", "free")
    free_used = user.get("free_doc_used", False)
    payment_status = (session or {}).get(
        "payment_status", "pending")

    if sub_status == "active":
        return {
            "allowed": True,
            "reason": "Active subscription",
            "payment_type": "subscription"
        }
    if not free_used:
        return {
            "allowed": True,
            "reason": "First document free",
            "payment_type": "free"
        }
    if payment_status == "paid":
        return {
            "allowed": True,
            "reason": "Payment confirmed",
            "payment_type": "payg"
        }
    return {
        "allowed": False,
        "reason": "Payment required",
        "payment_type": "none"
    }
```

**Phase 9 verification — create and run backend/test_phase9.py:**

```python
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.payments import check_access

def test():
    # 1. Subscription user always allowed
    r = check_access(
        {"subscription_status": "active",
         "free_doc_used": True})
    assert r["allowed"] == True
    assert r["payment_type"] == "subscription"
    print("1. Subscription access OK")

    # 2. Free doc not yet used
    r = check_access(
        {"subscription_status": "free",
         "free_doc_used": False})
    assert r["allowed"] == True
    assert r["payment_type"] == "free"
    print("2. Free doc access OK")

    # 3. Free doc used + payment confirmed
    r = check_access(
        {"subscription_status": "free",
         "free_doc_used": True},
        {"payment_status": "paid"})
    assert r["allowed"] == True
    assert r["payment_type"] == "payg"
    print("3. PAYG access OK")

    # 4. Free doc used + no payment
    r = check_access(
        {"subscription_status": "free",
         "free_doc_used": True},
        {"payment_status": "pending"})
    assert r["allowed"] == False
    print("4. Blocked access OK")

    print("\nALL PHASE 9 ASSERTIONS PASSED")

test()
```

Run: `cd ~/legalclear/backend && uv run python test_phase9.py`
All assertions must pass.
Print "PHASE 9 COMPLETE — all checks passed." then continue.

---

## Phase 10 — API

Work in backend/src/api/routes.py and backend/main.py.

Build the complete FastAPI application with all these
endpoints. Import all modules built in previous phases.
Use module-level singleton instances of all agents,
DatabaseManager, StripeClient, EscalationRouter,
and NotificationService.

Endpoints to implement:

```
GET  /health
POST /user
GET  /user/{user_id}
POST /user/{user_id}/push-token
POST /subscribe/{user_id}
POST /upload
POST /process/{session_id}
POST /chat/{document_id}
POST /eligibility           (no auth required)
GET  /document/{document_id}
GET  /documents/{user_id}
POST /florida-filing/prepare
POST /webhook               (no auth required)
```

All endpoints except /health, /eligibility, and /webhook
require X-API-Key header matching settings.API_KEY.

Add CORS middleware allowing all origins.

The /upload endpoint must:
1. Run ingest_document() on the uploaded file
2. Return error if doc.get("error") is True
3. Run ClassifierAgent.classify()
4. Run EscalationRouter.route()
5. Run classifier.get_price_tier()
6. Load user and run check_access()
7. Create session in DB
8. Create document record in DB
9. If payment required: create Stripe PaymentIntent
10. Return full response dict

The /process/{session_id} endpoint must:
1. Load session and document from DB
2. Verify access via check_access()
3. Run ExplainerAgent and RiskScannerAgent always
4. Run FormGuideAgent if category in FORM_CATEGORIES
5. Run ExpungementAgent if category is expungement_petition
6. Save all results to DB
7. Mark free doc used if payment_type is free
8. Log usage stats
9. Send push notification if user has expo token
10. Return complete results

FORM_CATEGORIES = [
    "government_form", "court_filing",
    "small_claims_complaint", "small_claims_response",
    "small_claims_judgment"
]

The /webhook endpoint must handle:
- payment_intent.succeeded → update session to paid
- payment_intent.payment_failed → update session to failed
- customer.subscription.created → update user to active
- customer.subscription.deleted → update user to cancelled

Write backend/main.py:
```python
import uvicorn
from src.api.routes import app
from src.core.config import settings

if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8001,
        reload=settings.is_development
    )
```

**Phase 10 verification:**

```bash
cd ~/legalclear/backend
source venv/bin/activate
uv run python main.py &
sleep 4

curl -s http://localhost:8001/health
echo ""

curl -s -X POST http://localhost:8001/eligibility \
  -H "Content-Type: application/json" \
  -d '{"jurisdiction":"Florida","offense_description":"misdemeanor petit theft","years_since_offense":6,"lang":"en"}'
echo ""

kill %1 2>/dev/null
```

Health endpoint must return:
`{"status":"ok","version":"1.0","product":"LegalClear"}`

Eligibility endpoint must return a JSON object
containing "likely_eligible" field.

Print "PHASE 10 COMPLETE — all checks passed." then continue.

---

## Phase 11 — Florida courts

Work in backend/src/platforms/florida_courts.py.

Build three classes: PDFAGenerator, CountyRouter,
and ManualFilingHelper.

PDFAGenerator uses reportlab to generate PDF files
for Florida small claims court filings:
- generate_complaint(case_data, output_path) -> str
- generate_civil_cover_sheet(case_data, output_path) -> str
- generate_summons(case_data, output_path) -> str
- generate_packet(case_data, output_dir) -> dict
  Returns paths to all three files plus county info.

CountyRouter loads jurisdictions.json and provides:
- route(county) -> dict with portal info
- detect_county_from_address(address) -> str
- get_deep_link(county) -> str

ManualFilingHelper provides:
- get_instructions(county, lang) -> dict with steps list
  English steps explain how to use myflcourtaccess.com
  Spanish steps are translated via translate_if_needed()
- get_deep_link_button(county) -> dict with labels and URL

**Phase 11 verification — create and run
backend/test_phase11.py:**

```python
import sys, os, asyncio
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.platforms.florida_courts import (
    PDFAGenerator, CountyRouter, ManualFilingHelper)

case_data = {
    "plaintiff_name": "Maria Garcia",
    "plaintiff_address": "123 Main St",
    "plaintiff_city_state_zip": "Stuart FL 34994",
    "plaintiff_phone": "772-555-0100",
    "defendant_name": "ABC Landlord LLC",
    "defendant_address": "456 Oak Ave",
    "defendant_city_state_zip": "Stuart FL 34994",
    "amount_claimed": 2500.00,
    "claim_reason": (
        "Security deposit not returned after "
        "move-out on January 15 2026."),
    "incident_date": "2026-01-15",
    "county": "Martin",
    "court_name": "Martin County Court"
}

def test():
    gen = PDFAGenerator()
    packet = gen.generate_packet(
        case_data, "/tmp/lc_test_packet/")

    for key in ["complaint_path",
                "cover_sheet_path",
                "summons_path"]:
        path = packet[key]
        assert os.path.exists(path), (
            f"File not found: {path}")
        size = os.path.getsize(path)
        assert size > 0, f"Empty file: {path}"
        print(f"{key}: {round(size/1024,1)}KB OK")

    router = CountyRouter()
    info = router.route("Martin")
    assert "court_name" in info
    assert "portal_url" in info
    assert "martin" in info["portal_url"].lower() or \
           "myflcourtaccess" in info["portal_url"].lower()
    print(f"County route: {info['portal_url']}")

    helper = ManualFilingHelper()
    instr_en = helper.get_instructions("Martin", "en")
    assert "steps" in instr_en
    assert len(instr_en["steps"]) >= 5
    assert "disclaimer" in instr_en
    print(f"EN steps: {len(instr_en['steps'])}")

    instr_es = helper.get_instructions("Martin", "es")
    assert "steps" in instr_es
    print(f"ES steps[0]: {instr_es['steps'][0][:60]}")

    btn = helper.get_deep_link_button("Martin")
    assert "url" in btn
    assert "label_en" in btn
    assert "label_es" in btn
    print(f"Button URL: {btn['url']}")

    print("\nALL PHASE 11 ASSERTIONS PASSED")

test()
```

Run: `cd ~/legalclear/backend && uv run python test_phase11.py`
All assertions must pass.
Print "PHASE 11 COMPLETE — all checks passed." then continue.

---

## Phase 12 — Web frontend

Work in frontend/. Backend must be running on port 8001.

Initialize the React project:
```bash
cd ~/legalclear/frontend
npm create vite@latest . -- --template react
npm install tailwindcss postcss autoprefixer \
  @stripe/stripe-js @stripe/react-stripe-js \
  react-router-dom i18next react-i18next
npx tailwindcss init -p
```

Configure tailwind.config.js content:
```js
content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"]
```

Add to src/index.css:
```css
@tailwind base;
@tailwind components;
@tailwind utilities;
:root {
  --navy: #1e3a5f;
  --teal: #0d9488;
  --red-flag: #dc2626;
  --yellow-flag: #d97706;
  --green-flag: #16a34a;
}
```

Create frontend/.env:
```
VITE_API_URL=http://localhost:8001
VITE_STRIPE_PUBLISHABLE_KEY=pk_test_xxx
```

Create src/i18n.js with i18next configuration loading
EN and ES locale files.

Create src/locales/en.json and src/locales/es.json
with translations for all UI strings including:
tagline, upload_title, analyzing, tab_summary,
tab_risk, tab_form, tab_expungement, tab_florida,
tab_chat, risk_high, risk_medium, risk_low,
your_rights, your_obligations, disclaimer_short,
file_now, subscribe_title, sub_price, most_popular.

Create src/api.js with functions:
uploadDocument, processDocument, getDocument,
sendChat, checkEligibility, createUser.
All functions use VITE_API_URL and send X-API-Key header.

Build these components in src/components/:
- DisclaimerBanner.jsx (collapsible, navy border-left)
- RiskBadge.jsx (RED/YELLOW/GREEN colored pills)
- ClauseCard.jsx (colored left border per risk level)
- ChatInterface.jsx (message list + input + send)
- LanguageToggle.jsx (EN/ES buttons)

Build these pages in src/pages/:
- UploadPage.jsx (route: /) with drag-drop upload zone,
  language toggle, warning banners, Stripe payment form,
  loading messages cycling every 3 seconds
- ProcessingPage.jsx (route: /processing/:sessionId)
  polls every 3 seconds, navigates on complete
- ResultsPage.jsx (route: /results/:documentId)
  with 6 conditional tabs: Summary, Risk Report,
  Form Guide, Expungement Guide, Florida Filing, Chat
- EligibilityPage.jsx (route: /eligibility)
  free form, no auth, calls checkEligibility()
- SubscribePage.jsx (route: /subscribe)
  two pricing cards, Stripe Checkout redirect

Build App.jsx with React Router and all 5 routes.
Wrap in Stripe Elements provider.

**Phase 12 verification:**

```bash
cd ~/legalclear/frontend
npm run build 2>&1 | tail -10
```

Build must complete with no errors.
Then run:
```bash
npm run preview -- --port 3000 &
sleep 3
curl -s http://localhost:3000 | grep -c "html"
kill %1 2>/dev/null
```

Must return a number greater than 0 (HTML is served).
Print "PHASE 12 COMPLETE — all checks passed." then continue.

---

## Phase 13 — Mobile app

Work in mobile/. Backend must be complete.

Initialize Expo project:
```bash
cd ~/legalclear/mobile
npx create-expo-app . --template blank-typescript
```

Install dependencies:
```bash
npx expo install @stripe/stripe-react-native \
  expo-document-picker expo-image-picker \
  expo-camera expo-notifications expo-secure-store
npm install @react-navigation/native \
  @react-navigation/stack i18next react-i18next axios
npx expo install react-native-safe-area-context \
  react-native-screens
```

Create mobile/.env:
```
EXPO_PUBLIC_API_URL=http://YOUR_LOCAL_IP:8001
EXPO_PUBLIC_STRIPE_KEY=pk_test_xxx
```

Replace YOUR_LOCAL_IP with: hostname -I | awk '{print $1}'

Copy locale files:
```bash
mkdir -p src/locales
cp ../frontend/src/locales/en.json src/locales/
cp ../frontend/src/locales/es.json src/locales/
```

Create src/i18n.ts using same i18next pattern as web.

Create src/api.ts with same functions as web api.js
adapted for React Native FormData format.

Set up push notifications in App.tsx:
request permissions, get Expo push token,
call savePushToken API if user is logged in.

Build these screens in src/screens/:
- HomeScreen.tsx with logo, tagline, language toggle,
  two action cards (Upload, Eligibility)
- UploadScreen.tsx with three upload options
  (camera, file picker, paste text), email input,
  payment sheet via @stripe/stripe-react-native
- ProcessingScreen.tsx polling every 3 seconds
- ResultsScreen.tsx with tab navigator showing
  Summary, Risk Report, Form Guide, Expungement,
  Florida Filing, Chat screens
- EligibilityScreen.tsx with state picker and form
- SubscribeScreen.tsx with pricing cards

Build App.tsx with NavigationContainer,
Stack Navigator, and StripeProvider.

**Phase 13 verification:**

```bash
cd ~/legalclear/mobile
npx expo export --platform web 2>&1 | tail -5
```

Export must complete without TypeScript errors.
Print "PHASE 13 COMPLETE — all checks passed." then continue.

---

## Phase 14 — Deploy

Create deploy/ directory at ~/legalclear/deploy/.

Get current username:
```bash
CURRENT_USER=$(whoami)
echo "Building deploy files for user: $CURRENT_USER"
```

Create deploy/legalclear-backend.service by writing
the systemd service file with the actual username
substituted for YOUR_USERNAME in all paths.

Create deploy/legalclear-frontend.service similarly.

Create deploy/nginx.conf with:
- /api/ proxied to localhost:8001 (strip prefix)
- / serving frontend/dist/
- Security headers added

Run the complete final checklist:

```bash
# Step 1: Verify .env
cd ~/legalclear/backend
echo "API_KEY set: $(grep -c API_KEY .env)"
echo "ANTHROPIC_API_KEY set: $(grep -c ANTHROPIC_API_KEY .env)"

# Step 2: Start API
source venv/bin/activate
uv run python main.py &
API_PID=$!
sleep 5

# Step 3: Health check
HEALTH=$(curl -s http://localhost:8001/health)
echo "Health: $HEALTH"
echo $HEALTH | python3 -c "import sys,json; d=json.load(sys.stdin); assert d['status']=='ok'; print('HEALTH OK')"

# Step 4: Eligibility check
curl -s -X POST http://localhost:8001/eligibility \
  -H "Content-Type: application/json" \
  -d '{"jurisdiction":"Florida","offense_description":"misdemeanor","years_since_offense":5,"lang":"en"}' \
  | python3 -c "import sys,json; d=json.load(sys.stdin); assert 'likely_eligible' in d; print('ELIGIBILITY OK')"

# Step 5: Build frontend
cd ~/legalclear/frontend
npm run build
echo "FRONTEND BUILD OK"

# Step 6: Install systemd services
cd ~/legalclear
sed -i "s/YOUR_USERNAME/$CURRENT_USER/g" \
  deploy/legalclear-backend.service
sed -i "s/YOUR_USERNAME/$CURRENT_USER/g" \
  deploy/legalclear-frontend.service
sed -i "s/YOUR_USERNAME/$CURRENT_USER/g" \
  deploy/nginx.conf

sudo cp deploy/legalclear-backend.service \
  /etc/systemd/system/
sudo cp deploy/legalclear-frontend.service \
  /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable legalclear-backend \
  legalclear-frontend
sudo systemctl start legalclear-backend \
  legalclear-frontend
sleep 3

# Step 7: Confirm services running
sudo systemctl is-active legalclear-backend
sudo systemctl is-active legalclear-frontend

kill $API_PID 2>/dev/null
```

Both services must show "active".

If all steps pass, print:
```
========================================
LEGALCLEAR DEPLOY COMPLETE
========================================
Backend:  http://localhost:8001
Frontend: http://localhost:3000
Health:   curl http://localhost:8001/health
Logs:     journalctl -u legalclear-backend -f
Restart:  sudo systemctl restart legalclear-backend

Messaging slot: set MESSAGING_PLATFORM in .env
Florida Mode B: set FLORIDA_PORTAL_EMAIL and
                FLORIDA_PORTAL_PASSWORD in .env

All 14 phases complete. LegalClear is live.
========================================
```

