import logging
import traceback

from .ocr import OCRProcessor
from .pdf_parser import PDFParser
from .text_cleaner import TextCleaner

_pdf = PDFParser()
_ocr = OCRProcessor()
_cleaner = TextCleaner()

logger = logging.getLogger(__name__)


async def ingest_document(file_bytes: bytes,
                          filename: str) -> dict:
    if len(file_bytes) > 15_000_000:
        return {
            "error": True,
            "error_code": "document_too_large",
            "message_en": (
                "This document is too large to process. "
                "Please upload sections under 15MB."),
            "message_es": (
                "Este documento es demasiado grande. "
                "Por favor, cargue secciones menores de 15MB."),
        }

    try:
        # Use async PDF extraction — off the event loop
        extraction = await _pdf.extract_from_bytes_async(file_bytes)
        if extraction.get("error"):
            return extraction

        raw_text = extraction["raw_text"]
        page_count = extraction.get("page_count", 1)

    except Exception as e:
        logger.error(
            "PDF extraction failed for %s:\n%s",
            filename, traceback.format_exc(),
        )
        return {
            "error": True,
            "error_code": "pdf_extraction_failed",
            "message_en": f"Could not extract text: {e!s}",
            "message_es": f"No se pudo extraer texto: {e!s}",
        }

    # Clean text
    try:
        cleaned = _cleaner.clean(raw_text)
    except Exception:
        logger.warning(
            "Text cleaning failed for %s — using raw text",
            filename,
        )
        cleaned = raw_text

    return {
        "error": False,
        "raw_text": raw_text,
        "cleaned_text": cleaned,
        "page_count": page_count,
        "token_estimate": int(len(cleaned.split()) * 1.3),
        "filename": filename,
        "ingestion_method": "pdf"
    }
