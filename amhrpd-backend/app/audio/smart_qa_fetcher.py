"""
Smart Q&A Fetcher

Multi-stage query processing with:
- LRU cache (top 200 queries, 24-hour TTL)
- Semantic cache (serve cached results for ≥95% similar queries)
- Reranking via OptimizedKnowledgeBase multi-stage pipeline
- Integration with PerformanceMonitor for real-time metrics
"""

import time
import threading
import logging
from collections import OrderedDict
from difflib import SequenceMatcher
from typing import Any, Dict, List, Optional, Tuple

from app.audio.optimized_knowledge_base import (
    OptimizedKnowledgeBase,
    QAMatch,
    get_optimized_kb,
    reload_index,
)
from app.audio.qa_metrics import PerformanceMonitor, get_monitor

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

LRU_CAPACITY = 200          # max cached entries
CACHE_TTL_SECONDS = 86400   # 24 hours
SEMANTIC_CACHE_THRESHOLD = 0.95   # similarity required for semantic cache hit

DEFAULT_TOP_K = 3
DEFAULT_MIN_CONFIDENCE = 0.40


# ---------------------------------------------------------------------------
# LRU Cache with TTL
# ---------------------------------------------------------------------------

class _LRUCacheTTL:
    """
    Thread-safe LRU cache with per-entry TTL.

    Keys are normalised query strings (lower-cased, stripped).
    Values are cached search result dicts plus expiry timestamp.
    """

    def __init__(self, capacity: int = LRU_CAPACITY, ttl: float = CACHE_TTL_SECONDS) -> None:
        self._capacity = capacity
        self._ttl = ttl
        self._cache: OrderedDict[str, Tuple[Any, float]] = OrderedDict()
        self._lock = threading.Lock()

        # statistics
        self._hits = 0
        self._misses = 0
        self._evictions = 0

    # ------------------------------------------------------------------

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            if key not in self._cache:
                self._misses += 1
                return None
            value, expiry = self._cache[key]
            if time.time() > expiry:
                del self._cache[key]
                self._evictions += 1
                self._misses += 1
                return None
            # Move to end (most recently used)
            self._cache.move_to_end(key)
            self._hits += 1
            return value

    def set(self, key: str, value: Any) -> bool:
        """Store value. Returns True if an eviction occurred."""
        evicted = False
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
            elif len(self._cache) >= self._capacity:
                self._cache.popitem(last=False)  # remove LRU entry
                self._evictions += 1
                evicted = True
            self._cache[key] = (value, time.time() + self._ttl)
        return evicted

    def stats(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "size": len(self._cache),
                "capacity": self._capacity,
                "ttl_seconds": self._ttl,
                "hits": self._hits,
                "misses": self._misses,
                "evictions": self._evictions,
                "hit_rate": round(self._hits / max(self._hits + self._misses, 1), 4),
            }

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()


# ---------------------------------------------------------------------------
# Semantic Cache
# ---------------------------------------------------------------------------

class _SemanticCache:
    """
    Keeps a small pool of (query, result) pairs and looks up by similarity.

    If an incoming query is ≥ SEMANTIC_CACHE_THRESHOLD similar to a stored
    query, the cached result is returned directly.
    """

    MAX_ENTRIES = 100

    def __init__(self, threshold: float = SEMANTIC_CACHE_THRESHOLD) -> None:
        self._threshold = threshold
        self._entries: List[Tuple[str, Any]] = []   # [(normalised_query, result)]
        self._lock = threading.Lock()
        self._hits = 0
        self._misses = 0

    @staticmethod
    def _similarity(a: str, b: str) -> float:
        return SequenceMatcher(None, a, b).ratio()

    def get(self, query: str) -> Optional[Any]:
        normalised = query.lower().strip()
        with self._lock:
            for stored_q, result in self._entries:
                if self._similarity(normalised, stored_q) >= self._threshold:
                    self._hits += 1
                    return result
            self._misses += 1
            return None

    def set(self, query: str, result: Any) -> None:
        normalised = query.lower().strip()
        with self._lock:
            # Evict oldest if full
            if len(self._entries) >= self.MAX_ENTRIES:
                self._entries.pop(0)
            self._entries.append((normalised, result))

    def stats(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "size": len(self._entries),
                "capacity": self.MAX_ENTRIES,
                "threshold": self._threshold,
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": round(self._hits / max(self._hits + self._misses, 1), 4),
            }

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()


# ---------------------------------------------------------------------------
# SmartQAFetcher
# ---------------------------------------------------------------------------

class SmartQAFetcher:
    """
    High-level Q&A fetcher combining:
    1. Exact LRU cache lookup
    2. Semantic cache lookup (similar queries)
    3. OptimizedKnowledgeBase multi-stage search
    4. PerformanceMonitor recording
    """

    def __init__(
        self,
        kb: Optional[OptimizedKnowledgeBase] = None,
        monitor: Optional[PerformanceMonitor] = None,
    ) -> None:
        self._kb = kb or get_optimized_kb()
        self._monitor = monitor or get_monitor()
        self._lru = _LRUCacheTTL()
        self._semantic_cache = _SemanticCache()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def fetch(
        self,
        query: str,
        top_k: int = DEFAULT_TOP_K,
        min_confidence: float = DEFAULT_MIN_CONFIDENCE,
    ) -> List[Dict[str, Any]]:
        """
        Fetch top-k answers for the given query.

        Returns a list of dicts:
        ``[{"question": ..., "answer": ..., "category": ..., "confidence": ...}]``
        """
        if not query or not query.strip():
            return []

        t0 = time.perf_counter()
        cache_key = query.lower().strip()

        # Stage 0a – exact LRU cache
        cached = self._lru.get(cache_key)
        if cached is not None:
            elapsed = (time.perf_counter() - t0) * 1000
            self._monitor.record_query(query, elapsed, cached[0]["confidence"] if cached else 0.0, cache_hit=True)
            return cached

        # Stage 0b – semantic cache
        sem_cached = self._semantic_cache.get(query)
        if sem_cached is not None:
            # Also populate LRU for future exact hits
            self._lru.set(cache_key, sem_cached)
            elapsed = (time.perf_counter() - t0) * 1000
            self._monitor.record_query(query, elapsed, sem_cached[0]["confidence"] if sem_cached else 0.0, cache_hit=True)
            return sem_cached

        # Stage 1-3 – full indexed search
        matches: List[QAMatch] = self._kb.search(query, top_k=top_k, min_confidence=min_confidence)
        result = [
            {
                "question": m.question,
                "answer": m.answer,
                "category": m.category,
                "confidence": round(m.confidence, 4),
            }
            for m in matches
        ]

        # Populate caches
        evicted = self._lru.set(cache_key, result)
        if evicted:
            self._monitor.record_cache_eviction()
        self._semantic_cache.set(query, result)

        elapsed = (time.perf_counter() - t0) * 1000
        top_conf = result[0]["confidence"] if result else 0.0
        self._monitor.record_query(query, elapsed, top_conf, cache_hit=False)

        return result

    def get_answer(self, query: str) -> Optional[str]:
        """Return the single best answer string, or None."""
        results = self.fetch(query, top_k=1)
        if results and results[0]["confidence"] >= DEFAULT_MIN_CONFIDENCE:
            return results[0]["answer"]
        return None

    def reload(self) -> None:
        """Rebuild indexes and clear all caches."""
        reload_index()
        self._kb = get_optimized_kb()
        self._lru.clear()
        self._semantic_cache.clear()
        logger.info("SmartQAFetcher: indexes reloaded, caches cleared")

    def cache_stats(self) -> Dict[str, Any]:
        """Return combined cache statistics."""
        lru = self._lru.stats()
        sem = self._semantic_cache.stats()
        return {
            "lru_cache": lru,
            "semantic_cache": sem,
            "total_cached_queries": lru["size"] + sem["size"],
            "combined_hit_rate": round(
                (lru["hits"] + sem["hits"])
                / max(lru["hits"] + lru["misses"] + sem["hits"] + sem["misses"], 1),
                4,
            ),
        }


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

_fetcher: Optional[SmartQAFetcher] = None


def get_fetcher() -> SmartQAFetcher:
    global _fetcher
    if _fetcher is None:
        _fetcher = SmartQAFetcher()
    return _fetcher
