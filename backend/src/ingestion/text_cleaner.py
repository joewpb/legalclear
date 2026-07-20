import re
from collections import Counter


class TextCleaner:

    def clean(self, raw_text: str) -> str:
        text = raw_text.replace("\x00", "")
        text = re.sub(r"[\x01-\x08\x0b\x0c\x0e-\x1f\x7f]",
                      "", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = re.sub(r" {3,}", " ", text)
        lines = text.split("\n")
        line_counts = Counter(
            ln.strip() for ln in lines if len(ln.strip()) > 5)
        repeated = {ln for ln, c in line_counts.items()
                    if c >= 5}
        cleaned = [ln for ln in lines
                   if ln.strip() not in repeated]
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
        notice = (
            "\n\n[Document truncated for processing. "
            "Some middle sections omitted.]\n\n"
        )
        return (text[:first_part] + notice +
                text[len(text) - last_part:])
