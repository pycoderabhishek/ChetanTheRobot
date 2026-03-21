"""
Multilingual Knowledge Base for Chetan Robot
Wraps the existing knowledge_base with language detection and translation.

Flow:
  1. Detect language of query (Hindi / English / Hinglish)
  2. If Hindi or Hinglish → translate to English
  3. Search knowledge base
  4. If user's primary language is Hindi → translate response to Hindi
  5. Return answer with language metadata
"""

import json
import os
from typing import Optional, Tuple, List, Dict, Any

from app.audio.language_detector import detect_language, get_response_language
from app.audio.hindi_translator import translate_to_english, translate_to_hindi

# Path to the optional multilingual Q&A dataset
_MULTILINGUAL_DB_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "../../dataset/query_multilingual.json",
)

_multilingual_db: Optional[List[Dict]] = None


def _load_multilingual_db() -> List[Dict]:
    """Load the multilingual Q&A dataset (once, cached)."""
    global _multilingual_db
    if _multilingual_db is not None:
        return _multilingual_db

    path = os.path.abspath(_MULTILINGUAL_DB_FILE)
    if not os.path.exists(path):
        _multilingual_db = []
        return _multilingual_db

    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
            _multilingual_db = data if isinstance(data, list) else []
    except Exception as exc:
        print(f"Warning: could not load multilingual DB: {exc}")
        _multilingual_db = []

    return _multilingual_db


def _search_multilingual_db(query: str, lang_info: Dict[str, Any]) -> Optional[str]:
    """
    Search the multilingual dataset for a direct match.
    Checks Hinglish variants and Hindi queries directly.
    Returns the English answer if found, else None.
    """
    from difflib import SequenceMatcher

    db = _load_multilingual_db()
    if not db:
        return None

    query_lower = query.lower().strip()
    best_score = 0.0
    best_answer = None

    for entry in db:
        # Check all variant fields
        candidates = []
        if lang_info["language"] in ("hi", "code_mixed"):
            candidates += entry.get("query_hinglish", [])
            if entry.get("query_hi"):
                candidates.append(entry["query_hi"])
        # Always check English as well
        if entry.get("query_en"):
            candidates.append(entry["query_en"])

        for candidate in candidates:
            score = SequenceMatcher(None, query_lower, candidate.lower().strip()).ratio()
            if score > best_score:
                best_score = score
                best_answer = entry.get("answer_en", "")

    if best_score >= 0.55 and best_answer:
        return best_answer
    return None


def search_qa_multilingual(query: str, top_k: int = 3) -> List[Dict[str, Any]]:
    """
    Multi-language Q&A search.

    1. Detect language of the query.
    2. If Hindi/Hinglish → translate to English for KB search.
    3. Also search the multilingual dataset for direct matches.
    4. Return top matches with language metadata.

    Args:
        query: User's question (any language).
        top_k: Maximum number of results to return.

    Returns:
        List of result dicts, each with keys:
            question, answer, category, confidence, response_language
    """
    if not query or not query.strip():
        return []

    lang_info = detect_language(query)
    response_lang = get_response_language(lang_info)

    # Translate to English if needed for KB search
    search_query = query
    if lang_info["language"] in ("hi", "code_mixed"):
        search_query = translate_to_english(query, lang_info["language"])

    # Search main English knowledge base (lazy import for test-stub compatibility)
    try:
        from app.audio.knowledge_base import search_qa
        results = search_qa(search_query, top_k=top_k)
    except ImportError:
        results = []

    # Also try multilingual dataset
    ml_answer = _search_multilingual_db(query, lang_info)
    if ml_answer and not any(r["answer"] == ml_answer for r in results):
        results.insert(0, {
            "question": query,
            "answer": ml_answer,
            "category": "Multilingual",
            "confidence": 0.80,
        })
        results = results[:top_k]

    # Attach response language metadata
    for r in results:
        r["response_language"] = response_lang

    return results


def get_answer_multilingual(query: str) -> Tuple[Optional[str], str]:
    """
    Get the best answer for a query, handling multilingual input.

    1. Detect language.
    2. Translate query to English if needed.
    3. Search knowledge base.
    4. Translate answer to Hindi if user's primary language is Hindi.

    Args:
        query: User's question in any language.

    Returns:
        (answer_text, response_language) where response_language is "en" or "hi".
        answer_text is None if no answer was found.
    """
    if not query or not query.strip():
        return None, "en"

    lang_info = detect_language(query)
    response_lang = get_response_language(lang_info)

    # Translate to English for search
    search_query = query
    if lang_info["language"] in ("hi", "code_mixed"):
        search_query = translate_to_english(query, lang_info["language"])

    # Try multilingual dataset first
    answer = _search_multilingual_db(query, lang_info)

    # Fall back to main knowledge base (lazy import for test-stub compatibility)
    if not answer:
        from app.audio.knowledge_base import get_answer
        answer = get_answer(search_query)

    if not answer:
        return None, response_lang

    # Translate response to Hindi if user prefers Hindi
    if response_lang == "hi":
        answer = translate_to_hindi(answer)

    return answer, response_lang
