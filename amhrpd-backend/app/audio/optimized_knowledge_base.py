"""
Optimized Knowledge Base Engine

Multi-level indexed Q&A lookup using:
- Keyword inverted index   (fast candidate selection)
- Category index           (fast category-based filter)
- N-gram index             (bigram typo tolerance)
- TF-IDF semantic scoring  (numpy-based, no extra deps)
- Multi-stage pipeline:    keyword→TF-IDF→category boost
"""

import json
import math
import os
import re
import time
import logging
from collections import defaultdict
from difflib import SequenceMatcher
from typing import Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Path resolution – same strategy as knowledge_base.py
# ---------------------------------------------------------------------------
_AUDIO_DIR = os.path.dirname(os.path.abspath(__file__))
_QA_FILE = os.path.abspath(os.path.join(_AUDIO_DIR, "../../dataset/query.json"))
# Fallback: query.json sitting next to this file (used in tests / local dev)
_QA_FILE_FALLBACK = os.path.join(_AUDIO_DIR, "query.json")

# ---------------------------------------------------------------------------
# Stop words (filtered from index but kept in TF-IDF denominator calculation)
# ---------------------------------------------------------------------------
_STOP_WORDS: Set[str] = {
    "is", "the", "a", "an", "what", "how", "where", "when", "who", "why",
    "does", "do", "at", "in", "of", "are", "was", "were", "be", "been",
    "being", "have", "has", "had", "will", "would", "could", "should",
    "may", "might", "shall", "can", "to", "for", "and", "or", "but",
    "not", "its", "it", "this", "that", "there", "their", "they",
    "about", "with", "from", "tell", "me", "us", "give", "my",
}

# ---------------------------------------------------------------------------
# Scoring constants (extracted for easy tuning)
# ---------------------------------------------------------------------------

# Stage 1: bigram candidate threshold — item must share at least 1/BGRAM_THRESHOLD_DIVISOR
# of the query bigrams to be included as a candidate.
_BGRAM_THRESHOLD_DIVISOR = 4

# Stage 2 (quick score): fast TF-IDF + bigram pass before running SequenceMatcher
_QUICK_TFIDF_WEIGHT = 0.60
_QUICK_BIGRAM_WEIGHT = 0.40

# Stage 2 (full score): final scoring after SequenceMatcher
_S2_TFIDF_WEIGHT = 0.45
_S2_SEQUENCE_WEIGHT = 0.35
_S2_BIGRAM_WEIGHT = 0.20

# Stage 3: bonus applied when query tokens appear in the category label
_CATEGORY_BOOST = 0.05


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _normalize(text: str) -> str:
    """Lower-case, collapse whitespace, strip punctuation."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _tokens(text: str, include_stop: bool = False) -> List[str]:
    words = _normalize(text).split()
    if not include_stop:
        return [w for w in words if w not in _STOP_WORDS]
    return words


def _bigrams(text: str) -> Set[str]:
    """Character-level bigrams built from content words only (stop words excluded).
    This avoids extremely common bigrams ('wh','ha','is',...) that inflate candidates.
    """
    content_words = _tokens(text)  # already removes stop words
    combined = " ".join(content_words)
    if len(combined) < 2:
        return set()
    return {combined[i : i + 2] for i in range(len(combined) - 1)}


def _bigram_similarity(a: str, b: str) -> float:
    """Jaccard similarity over content-word character bigrams (0-1)."""
    bg_a = _bigrams(a)
    bg_b = _bigrams(b)
    if not bg_a and not bg_b:
        return 1.0
    if not bg_a or not bg_b:
        return 0.0
    return len(bg_a & bg_b) / len(bg_a | bg_b)


def _sequence_similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, _normalize(a), _normalize(b)).ratio()


# ---------------------------------------------------------------------------
# TF-IDF (numpy-free pure Python implementation)
# ---------------------------------------------------------------------------

class _TFIDF:
    """Lightweight TF-IDF scorer – no external ML deps required."""

    def __init__(self, corpus: List[str]):
        self._n = len(corpus)
        self._idf: Dict[str, float] = {}
        self._doc_vecs: List[Dict[str, float]] = []
        self._build(corpus)

    def _build(self, corpus: List[str]) -> None:
        df: Dict[str, int] = defaultdict(int)
        tokenised = [_tokens(doc, include_stop=True) for doc in corpus]

        for toks in tokenised:
            for t in set(toks):
                df[t] += 1

        for term, count in df.items():
            self._idf[term] = math.log((self._n + 1) / (count + 1)) + 1.0

        for toks in tokenised:
            tf: Dict[str, float] = defaultdict(float)
            for t in toks:
                tf[t] += 1.0
            total = max(len(toks), 1)
            vec = {t: (freq / total) * self._idf.get(t, 1.0) for t, freq in tf.items()}
            # L2-normalise
            norm = math.sqrt(sum(v * v for v in vec.values())) or 1.0
            self._doc_vecs.append({t: v / norm for t, v in vec.items()})

    def score(self, query: str, doc_idx: int) -> float:
        """Cosine similarity between query and stored document."""
        toks = _tokens(query, include_stop=True)
        if not toks:
            return 0.0
        tf: Dict[str, float] = defaultdict(float)
        for t in toks:
            tf[t] += 1.0
        total = len(toks)
        q_vec = {t: (freq / total) * self._idf.get(t, 1.0) for t, freq in tf.items()}
        q_norm = math.sqrt(sum(v * v for v in q_vec.values())) or 1.0
        q_vec = {t: v / q_norm for t, v in q_vec.items()}

        d_vec = self._doc_vecs[doc_idx]
        dot = sum(q_vec.get(t, 0.0) * d_vec.get(t, 0.0) for t in q_vec)
        return min(dot, 1.0)


# ---------------------------------------------------------------------------
# QAMatch (public DTO)
# ---------------------------------------------------------------------------

class QAMatch:
    """Result object returned by OptimizedKnowledgeBase.search()."""

    __slots__ = ("question", "answer", "category", "confidence", "index")

    def __init__(
        self,
        question: str,
        answer: str,
        category: str,
        confidence: float,
        index: int = -1,
    ):
        self.question = question
        self.answer = answer
        self.category = category
        self.confidence = confidence
        self.index = index

    def __repr__(self) -> str:  # pragma: no cover
        return f"QAMatch(conf={self.confidence:.3f}, q='{self.question[:40]}')"


# ---------------------------------------------------------------------------
# OptimizedKnowledgeBase
# ---------------------------------------------------------------------------

class OptimizedKnowledgeBase:
    """
    High-performance Q&A engine with pre-built indexes.

    Indexes built once at startup:
    - ``_keyword_index``  : token  → set of qa-record indices
    - ``_category_index`` : category → set of qa-record indices
    - ``_ngram_index``    : 2-char bigram → set of qa-record indices
    - ``_tfidf``          : TF-IDF scorer over all question texts
    """

    def __init__(self) -> None:
        self._qa: List[Dict] = []
        self._keyword_index: Dict[str, Set[int]] = defaultdict(set)
        self._category_index: Dict[str, Set[int]] = defaultdict(set)
        self._ngram_index: Dict[str, Set[int]] = defaultdict(set)
        self._tfidf: Optional[_TFIDF] = None
        # Pre-computed per-question bigrams and normalised text (avoid recompute on every query)
        self._question_bigrams: List[Set[str]] = []
        self._question_normalized: List[str] = []
        self._ready = False
        self._load_and_index()

    # ------------------------------------------------------------------
    # Startup
    # ------------------------------------------------------------------

    def _load_and_index(self) -> None:
        t0 = time.perf_counter()
        qa = self._load_data()
        if not qa:
            logger.warning("OptimizedKnowledgeBase: no data loaded – indexes empty")
            return

        self._qa = qa
        questions = [item.get("query", "") for item in qa]

        self._question_bigrams = []
        self._question_normalized = []

        for idx, item in enumerate(qa):
            question = item.get("query", "")
            category = item.get("category", "Unknown").lower()

            # Pre-compute and cache per-question values
            q_norm = _normalize(question)
            q_bgs = _bigrams(question)
            self._question_normalized.append(q_norm)
            self._question_bigrams.append(q_bgs)

            # keyword index
            for tok in _tokens(question):
                self._keyword_index[tok].add(idx)

            # category index
            self._category_index[category].add(idx)

            # n-gram index (content-word character bigrams from the question)
            for bg in q_bgs:
                self._ngram_index[bg].add(idx)

        # TF-IDF over question corpus
        self._tfidf = _TFIDF(questions)
        self._ready = True

        elapsed = (time.perf_counter() - t0) * 1000
        logger.info(
            f"OptimizedKnowledgeBase: indexed {len(qa)} Q&A pairs in {elapsed:.1f} ms"
        )

    @staticmethod
    def _load_data() -> List[Dict]:
        for path in (_QA_FILE, _QA_FILE_FALLBACK):
            if os.path.exists(path):
                try:
                    with open(path, "r", encoding="utf-8") as fh:
                        data = json.load(fh)
                    logger.info(f"Loaded {len(data)} Q&A pairs from {path}")
                    return data
                except Exception as exc:
                    logger.error(f"Failed to load {path}: {exc}")
        logger.error("query.json not found in either expected location")
        return []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def reload(self) -> None:
        """Force a full reload of data and rebuild all indexes."""
        self._keyword_index = defaultdict(set)
        self._category_index = defaultdict(set)
        self._ngram_index = defaultdict(set)
        self._tfidf = None
        self._question_bigrams = []
        self._question_normalized = []
        self._ready = False
        self._load_and_index()

    def search(
        self,
        query: str,
        top_k: int = 3,
        min_confidence: float = 0.40,
    ) -> List[QAMatch]:
        """
        Multi-stage search returning top-k results sorted by confidence.

        Stage 1 – Keyword + N-gram filter → candidate set (~30-50 items).
        Stage 2 – TF-IDF + bigram scoring for all candidates;
                   SequenceMatcher applied only to the top-30 by TF-IDF.
        Stage 3 – Category boost + confidence calibration.
        """
        if not self._ready or not self._qa:
            return []

        t0 = time.perf_counter()
        candidates = self._stage1_candidates(query)

        # Quick score (TF-IDF + bigram) for all candidates – avoids slow
        # SequenceMatcher on every item.
        quick: List[Tuple[int, float]] = []
        for idx in candidates:
            s = self._quick_score(query, idx)
            quick.append((idx, s))

        # Sort by quick score descending; apply SequenceMatcher only to top-30
        quick.sort(key=lambda x: x[1], reverse=True)
        top_candidates = [idx for idx, _ in quick[:30]]

        results = []
        for idx in top_candidates:
            conf = self._stage2_score(query, idx)
            if conf >= min_confidence:
                item = self._qa[idx]
                conf = self._stage3_boost(query, item, conf)
                results.append(
                    QAMatch(
                        question=item.get("query", ""),
                        answer=item.get("answer", ""),
                        category=item.get("category", "Unknown"),
                        confidence=min(conf, 1.0),
                        index=idx,
                    )
                )

        results.sort(key=lambda m: m.confidence, reverse=True)
        elapsed_ms = (time.perf_counter() - t0) * 1000
        logger.debug(
            f"Search '{query[:40]}' → {len(candidates)} candidates, "
            f"{len(results)} hits, {elapsed_ms:.2f} ms"
        )
        return results[:top_k]

    def get_stats(self) -> Dict:
        """Return index statistics."""
        cats: Dict[str, int] = {}
        for item in self._qa:
            c = item.get("category", "Unknown")
            cats[c] = cats.get(c, 0) + 1
        return {
            "total_qa_pairs": len(self._qa),
            "categories": cats,
            "keyword_index_size": len(self._keyword_index),
            "ngram_index_size": len(self._ngram_index),
            "category_index_size": len(self._category_index),
            "status": "ready" if self._ready else "not_ready",
        }

    # ------------------------------------------------------------------
    # Private stages
    # ------------------------------------------------------------------

    def _stage1_candidates(self, query: str) -> Set[int]:
        """Return candidate indices using keyword + bigram index."""
        toks = _tokens(query)
        bgs = _bigrams(query)

        candidates: Set[int] = set()

        # Exact keyword hits
        for tok in toks:
            candidates.update(self._keyword_index.get(tok, set()))

        # Bigram hits (covers typos / partial words)
        bg_hits: Dict[int, int] = defaultdict(int)
        for bg in bgs:
            for idx in self._ngram_index.get(bg, set()):
                bg_hits[idx] += 1

        # Include items sharing ≥1/_BGRAM_THRESHOLD_DIVISOR of query bigrams (min 1)
        threshold = max(1, len(bgs) // _BGRAM_THRESHOLD_DIVISOR)
        for idx, count in bg_hits.items():
            if count >= threshold:
                candidates.add(idx)

        # If still very few candidates, add the top-N by raw TF-IDF score as a
        # soft fallback rather than scanning all items with SequenceMatcher.
        if len(candidates) < 10 and self._tfidf:
            tfidf_scores = [
                (i, self._tfidf.score(query, i)) for i in range(len(self._qa))
            ]
            tfidf_scores.sort(key=lambda x: x[1], reverse=True)
            for i, _ in tfidf_scores[:30]:
                candidates.add(i)

        return candidates

    def _quick_score(self, query: str, idx: int) -> float:
        """
        Fast first-pass score using only TF-IDF + pre-computed bigram (no SequenceMatcher).
        Used to rank candidates before applying the slower full score.
        Weights: 0.60 TF-IDF + 0.40 bigram
        """
        tfidf_score = self._tfidf.score(query, idx) if self._tfidf else 0.0

        # Use pre-computed bigrams for the stored question
        q_bgs = _bigrams(query)
        doc_bgs = self._question_bigrams[idx]
        if q_bgs or doc_bgs:
            bg_score = len(q_bgs & doc_bgs) / (len(q_bgs | doc_bgs) or 1)
        else:
            bg_score = 0.0

        # Fast substring containment check using pre-computed normalised text
        q_norm = _normalize(query)
        if q_norm in self._question_normalized[idx] or self._question_normalized[idx] in q_norm:
            return 1.0

        return _QUICK_TFIDF_WEIGHT * tfidf_score + _QUICK_BIGRAM_WEIGHT * bg_score

    def _stage2_score(self, query: str, idx: int) -> float:
        """
        Combine TF-IDF cosine, bigram Jaccard, and sequence similarity.
        Weights: 0.45 TF-IDF + 0.35 sequence + 0.20 bigram
        Uses pre-computed normalised text and bigrams for speed.
        """
        tfidf_score = self._tfidf.score(query, idx) if self._tfidf else 0.0

        # Pre-computed normalised question text (avoids re-normalising each call)
        t_norm = self._question_normalized[idx]
        q_norm = _normalize(query)

        # Direct substring containment bonus
        if q_norm in t_norm or t_norm in q_norm:
            return 1.0

        seq_score = SequenceMatcher(None, q_norm, t_norm).ratio()

        # Use pre-computed bigrams for the stored question
        q_bgs = _bigrams(query)
        doc_bgs = self._question_bigrams[idx]
        if q_bgs or doc_bgs:
            bg_score = len(q_bgs & doc_bgs) / (len(q_bgs | doc_bgs) or 1)
        else:
            bg_score = 0.0

        return _S2_TFIDF_WEIGHT * tfidf_score + _S2_SEQUENCE_WEIGHT * seq_score + _S2_BIGRAM_WEIGHT * bg_score

    def _stage3_boost(self, query: str, item: Dict, base_conf: float) -> float:
        """
        Apply a small category-keyword boost when query tokens appear in
        the category label. Caps the result at 1.0.
        """
        category = item.get("category", "").lower()
        query_toks = _tokens(query)
        cat_toks = _tokens(category)
        if set(query_toks) & set(cat_toks):
            return min(base_conf + _CATEGORY_BOOST, 1.0)
        return base_conf


# ---------------------------------------------------------------------------
# Module-level singleton (loaded once at import time)
# ---------------------------------------------------------------------------

_instance: Optional[OptimizedKnowledgeBase] = None


def get_optimized_kb() -> OptimizedKnowledgeBase:
    """Return (or lazily create) the module-level singleton."""
    global _instance
    if _instance is None:
        _instance = OptimizedKnowledgeBase()
    return _instance


def reload_index() -> None:
    """Force a full index rebuild (e.g. after updating query.json)."""
    global _instance
    if _instance is None:
        _instance = OptimizedKnowledgeBase()
    else:
        _instance.reload()
