import logging

logger = logging.getLogger(__name__)

SUPPORTED_LANGUAGES = ["en", "es"]


def get_lang(detected: str,
             user_preference: str | None = None) -> str:
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
    except Exception as e:
        logger.warning("Translation failed: %s", e)
        return text
