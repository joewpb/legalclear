import asyncio
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
        """Synchronous extraction — internal worker for executor."""
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        pages = [page.get_text() for page in doc]
        raw_text = "\n".join(pages)
        return {
            "raw_text": raw_text,
            "pages": pages,
            "page_count": len(pages),
            "extraction_method": "pdf"
        }

    async def extract_from_bytes_async(self, file_bytes: bytes) -> dict:
        """Async wrapper — runs sync extraction off the event loop."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, self.extract_from_bytes, file_bytes
        )
