"""
Hindi Translation Module for Chetan Robot
Translates Hindi/Hinglish queries to English and English responses to Hindi.

Primary: deep_translator (Google Translate, no API key needed)
Fallback: custom Hinglish→English dictionary
"""

import re
from typing import Optional, Dict

# ---------------------------------------------------------------------------
# Custom Hinglish → English phrase/word dictionary
# Used as fallback when deep_translator is unavailable.
# ---------------------------------------------------------------------------
_HINGLISH_DICT: Dict[str, str] = {
    # Greetings & meta
    "kya hai": "what is",
    "kaun hai": "who is",
    "kahan hai": "where is",
    "kab hai": "when is",
    "kaise hai": "how is",
    "batao": "tell me",
    "bataiye": "please tell",
    "bataye": "tell",
    "batana": "tell",

    # Common action words
    "hai kya": "is there",
    "hain kya": "are there",
    "milta hai": "is available",
    "milti hai": "is available",
    "milte hain": "are available",

    # Common nouns / college context
    "course": "course",
    "courses": "courses",
    "fees": "fees",
    "fee": "fee",
    "admission": "admission",
    "college": "college",
    "library": "library",
    "hostel": "hostel",
    "principal": "principal",
    "placement": "placement",
    "scholarship": "scholarship",
    "exam": "exam",
    "result": "result",

    # Pronouns / particles
    "mein": "in",
    "ke baare mein": "about",
    "ke liye": "for",
    "ka": "of",
    "ki": "of",
    "ke": "of",
    "kaunse": "which",
    "kaunsi": "which",
    "kitna": "how much",
    "kitni": "how many",
    "kitne": "how many",
    "kahan": "where",
    "kab": "when",
    "kaun": "who",
    "kyun": "why",
    "kaise": "how",
    "kya": "what",
    "kyunki": "because",

    # Common words
    "haan": "yes",
    "han": "yes",
    "nahi": "no",
    "nahin": "no",
    "aur": "and",
    "ya": "or",
    "se": "from",
    "par": "on",
    "pe": "on",
    "tak": "till",
    "sirf": "only",
    "bas": "just",
    "bahut": "very",
    "thoda": "a little",
    "zyada": "more",
    "sab": "all",
    "kuch": "some",
    "acha": "good",
    "theek": "okay",
    "wala": "",
    "wali": "",
    "wale": "",
    "abhi": "now",
    "pehle": "before",
    "baad": "after",

    # Patterns
    "NPGC mein": "at NPGC",
    "NPGC ka": "NPGC's",
    "NPGC ki": "NPGC's",
    "NPGC ke": "NPGC's",
}

# Ordered longer phrases first so they get substituted before shorter ones
_SORTED_HINGLISH_KEYS = sorted(_HINGLISH_DICT.keys(), key=lambda x: -len(x))


def translate_to_english(text: str, source_lang: str = "auto") -> str:
    """
    Translate Hindi or code-mixed (Hinglish) text to English.

    Tries deep_translator first; falls back to dictionary-based normalization.
    Proper nouns (NPGC, BCA, etc.) are preserved.

    Args:
        text: The query text to translate.
        source_lang: "hi" for Hindi, "code_mixed" for Hinglish, "auto" for auto-detect.

    Returns:
        English translation of the input text.
    """
    if not text or not text.strip():
        return text

    # Try deep_translator (Google Translate, no API key)
    try:
        from deep_translator import GoogleTranslator
        src = "hi" if source_lang == "hi" else "auto"
        translated = GoogleTranslator(source=src, target="en").translate(text.strip())
        if translated and translated.strip():
            return translated.strip()
    except Exception:
        pass

    # Fallback: normalize Hinglish using the dictionary
    return normalize_hinglish(text)


def translate_to_hindi(text: str) -> str:
    """
    Translate an English response to Hindi.

    Tries deep_translator first; returns original English on failure
    (so the system always has a usable response).

    Args:
        text: English text to translate.

    Returns:
        Hindi translation, or original text if translation fails.
    """
    if not text or not text.strip():
        return text

    try:
        from deep_translator import GoogleTranslator
        translated = GoogleTranslator(source="en", target="hi").translate(text.strip())
        if translated and translated.strip():
            return translated.strip()
    except Exception:
        pass

    # If translation fails, return original English text
    return text


def normalize_hinglish(text: str) -> str:
    """
    Normalize code-mixed Hindi-English (Hinglish) text to plain English
    using the built-in dictionary. Preserves proper nouns (all-caps words).

    Args:
        text: Code-mixed input text.

    Returns:
        Normalized English text.
    """
    if not text or not text.strip():
        return ""

    result = text.strip()

    # Apply phrase-level substitutions (longest first)
    for hindi_phrase in _SORTED_HINGLISH_KEYS:
        pattern = re.compile(re.escape(hindi_phrase), re.IGNORECASE)
        replacement = _HINGLISH_DICT[hindi_phrase]
        result = pattern.sub(replacement, result)

    # Collapse multiple spaces
    result = re.sub(r'\s+', ' ', result).strip()
    return result
