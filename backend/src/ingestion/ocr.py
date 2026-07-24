import io

import fitz
import pytesseract
from PIL import Image, ImageEnhance


class OCRProcessor:

    def extract_from_image(self, file_bytes: bytes,
                           lang: str = "eng") -> dict:
        img = Image.open(io.BytesIO(file_bytes))
        img = img.convert("L")
        img = ImageEnhance.Contrast(img).enhance(2.0)
        data = pytesseract.image_to_data(
            img, lang=lang,
            output_type=pytesseract.Output.DICT)
        raw_text = pytesseract.image_to_string(img, lang=lang)
        confidences = [int(c) for c in data["conf"]
                       if str(c).isdigit() and int(c) > 0]
        avg_conf = (sum(confidences) / len(confidences)
                    if confidences else 0.0)
        return {
            "raw_text": raw_text,
            "pages": [raw_text],
            "page_count": 1,
            "confidence": round(avg_conf / 100, 2),
            "extraction_method": "ocr"
        }

    def extract_from_pdf_images(self, file_bytes: bytes,
                                lang: str = "eng") -> dict:
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        all_pages = []
        for page in doc:
            mat = fitz.Matrix(200 / 72, 200 / 72)
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
