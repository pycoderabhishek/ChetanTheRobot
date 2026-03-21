"""
Language Detection Module for Chetan Robot
Detects Hindi, English, or Code-mixed (Hinglish) queries.
Uses Devanagari Unicode range for script detection and optional langdetect library.
"""

import re
from typing import Dict, Any, Optional

# Devanagari Unicode block: U+0900–U+097F
_DEVANAGARI_PATTERN = re.compile(r'[\u0900-\u097F]')

# Common Hinglish transliterated words (Roman-script Hindi commonly mixed with English)
_HINGLISH_WORDS = {
    # Greetings & meta
    'kya', 'hai', 'hain', 'kaise', 'kahan', 'kab', 'kaun', 'kyun', 'kyunki',
    'mein', 'mujhe', 'mera', 'mere', 'meri', 'aap', 'tum', 'hum', 'wo', 'yeh',
    'iska', 'uska', 'unka', 'hamara', 'tumhara',
    'nahi', 'nahin', 'nhi', 'haan', 'han', 'bilkul',
    'karo', 'batao', 'bataiye', 'batana', 'bataye',
    'chahiye', 'chahte', 'chahti', 'chahta',
    'kuch', 'sab', 'bahut', 'thoda', 'zyada', 'kam', 'aur', 'ya',
    'se', 'ke', 'ki', 'ka', 'ko', 'par', 'pe', 'tak', 'liye',
    'baare', 'baat', 'cheez', 'cheezein',
    'acha', 'theek', 'sahi', 'galat',
    'ho', 'hoga', 'hogi', 'hoge',
    'milta', 'milti', 'milte', 'mile',
    'deta', 'deti', 'dete', 'diya',
    'lena', 'lelo', 'le',
    'course', 'courses', 'college', 'admission', 'fees', 'fee',
    'kitna', 'kitni', 'kitne',
    'wala', 'wali', 'wale',
    'sirf', 'bas',
    'abhi', 'pehle', 'baad',
}

# Threshold: if hindi_percent > this value, consider it Hindi/code-mixed
_HINDI_THRESHOLD = 20.0


def detect_language(text: str) -> Dict[str, Any]:
    """
    Detect the language of the given text.

    Returns a dict with:
        language     : "en" | "hi" | "code_mixed"
        primary_lang : "en" | "hi"
        confidence   : 0.0–1.0
        hindi_percent: 0–100  (fraction of Devanagari or Hinglish tokens)
        english_percent: 0–100
    """
    if not text or not text.strip():
        return _make_result("en", "en", 1.0, 0, 100)

    text_stripped = text.strip()

    # --- Check for Devanagari script characters ---
    devanagari_chars = len(_DEVANAGARI_PATTERN.findall(text_stripped))
    # Use all non-whitespace characters as denominator to avoid ratio > 100%
    # when Devanagari combining marks (vowel signs, virama) are counted by the
    # regex but are not classified as isalpha() by Python.
    total_chars = len([c for c in text_stripped if not c.isspace()])

    if total_chars == 0:
        return _make_result("en", "en", 1.0, 0, 100)

    devanagari_ratio = min(devanagari_chars / total_chars * 100, 100.0)

    # Pure Devanagari text → Hindi
    if devanagari_ratio >= 70:
        confidence = min(0.5 + devanagari_ratio / 200, 0.99)
        hindi_pct = min(int(devanagari_ratio), 100)
        return _make_result("hi", "hi", confidence, hindi_pct, max(0, 100 - hindi_pct))

    # Mixed Devanagari (some Hindi script, some Roman)
    if devanagari_ratio > 0:
        hindi_pct = min(int(devanagari_ratio + 20), 100)
        return _make_result("code_mixed", "hi", 0.75, hindi_pct, max(0, 100 - hindi_pct))

    # --- No Devanagari: check for Hinglish transliteration in Roman script ---
    words = re.findall(r'[a-zA-Z]+', text_stripped.lower())
    if not words:
        return _make_result("en", "en", 1.0, 0, 100)

    hinglish_count = sum(1 for w in words if w in _HINGLISH_WORDS)
    hinglish_ratio = hinglish_count / len(words) * 100

    if hinglish_ratio >= 40:
        # Majority Hinglish → code_mixed with Hindi primary
        return _make_result("code_mixed", "hi", 0.80, int(hinglish_ratio), int(100 - hinglish_ratio))

    if hinglish_ratio >= _HINDI_THRESHOLD:
        # Some Hinglish mixing
        return _make_result("code_mixed", "hi", 0.65, int(hinglish_ratio), int(100 - hinglish_ratio))

    # Try optional langdetect for better accuracy
    try:
        from langdetect import detect as _detect, DetectorFactory
        DetectorFactory.seed = 0  # reproducibility
        lang_code = _detect(text_stripped)
        if lang_code == "hi":
            return _make_result("hi", "hi", 0.85, 60, 40)
        if lang_code in ("en", "en-US"):
            return _make_result("en", "en", 0.90, 0, 100)
        # Other detected language — treat as English fallback
        return _make_result("en", "en", 0.60, 0, 100)
    except Exception:
        pass

    # Default to English
    return _make_result("en", "en", 0.90, 0, 100)


def should_translate(text: str) -> bool:
    """Return True if the text needs translation to English."""
    result = detect_language(text)
    return result["language"] in ("hi", "code_mixed")


def get_response_language(detected_lang: Dict[str, Any]) -> str:
    """
    Determine which language to respond in based on detection result.
    Returns "hi" if user's primary language is Hindi, else "en".
    """
    return detected_lang.get("primary_lang", "en")


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _make_result(
    language: str,
    primary_lang: str,
    confidence: float,
    hindi_percent: int,
    english_percent: int,
) -> Dict[str, Any]:
    return {
        "language": language,
        "primary_lang": primary_lang,
        "confidence": round(confidence, 3),
        "hindi_percent": hindi_percent,
        "english_percent": english_percent,
    }
