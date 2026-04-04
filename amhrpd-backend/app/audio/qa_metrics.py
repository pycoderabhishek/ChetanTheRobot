"""
QA Performance Metrics & Monitoring

Tracks per-query latency, confidence scores, and cache statistics.
Thread-safe – safe to call from async FastAPI handlers.
"""

import threading
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Deque, Dict, List, Optional


# ---------------------------------------------------------------------------
# Per-query record
# ---------------------------------------------------------------------------

@dataclass
class QueryRecord:
    query: str
    response_time_ms: float
    confidence: float
    cache_hit: bool
    timestamp: float = field(default_factory=time.time)


# ---------------------------------------------------------------------------
# PerformanceMonitor
# ---------------------------------------------------------------------------

class PerformanceMonitor:
    """
    Collects real-time metrics for the Q&A system.

    All public methods are thread-safe.
    """

    MAX_RECORDS = 1000  # keep the last N query records in memory

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._records: Deque[QueryRecord] = deque(maxlen=self.MAX_RECORDS)

        # aggregate counters (never reset)
        self._total_queries: int = 0
        self._cache_hits: int = 0
        self._cache_misses: int = 0
        self._total_latency_ms: float = 0.0
        self._total_confidence: float = 0.0

        # cache eviction counter (incremented externally by SmartQAFetcher)
        self._cache_evictions: int = 0

        self._started_at: float = time.time()

    # ------------------------------------------------------------------
    # Recording
    # ------------------------------------------------------------------

    def record_query(
        self,
        query: str,
        response_time_ms: float,
        confidence: float,
        cache_hit: bool = False,
    ) -> None:
        with self._lock:
            rec = QueryRecord(
                query=query,
                response_time_ms=response_time_ms,
                confidence=confidence,
                cache_hit=cache_hit,
            )
            self._records.append(rec)
            self._total_queries += 1
            self._total_latency_ms += response_time_ms
            self._total_confidence += confidence
            if cache_hit:
                self._cache_hits += 1
            else:
                self._cache_misses += 1

    def record_cache_eviction(self) -> None:
        with self._lock:
            self._cache_evictions += 1

    # ------------------------------------------------------------------
    # Retrieval
    # ------------------------------------------------------------------

    def get_metrics(self) -> Dict[str, Any]:
        """Return aggregated performance metrics."""
        with self._lock:
            total = self._total_queries
            if total == 0:
                return {
                    "total_queries": 0,
                    "avg_response_time_ms": 0.0,
                    "avg_confidence": 0.0,
                    "cache_hit_rate": 0.0,
                    "cache_hits": 0,
                    "cache_misses": 0,
                    "cache_evictions": self._cache_evictions,
                    "uptime_seconds": round(time.time() - self._started_at, 1),
                }

            # recent-window stats (last 100 queries)
            recent = list(self._records)[-100:]
            recent_latencies = [r.response_time_ms for r in recent]
            recent_confidences = [r.confidence for r in recent]

            return {
                "total_queries": total,
                "avg_response_time_ms": round(self._total_latency_ms / total, 3),
                "recent_avg_response_time_ms": round(
                    sum(recent_latencies) / max(len(recent_latencies), 1), 3
                ),
                "min_response_time_ms": round(min(recent_latencies), 3) if recent_latencies else 0.0,
                "max_response_time_ms": round(max(recent_latencies), 3) if recent_latencies else 0.0,
                "avg_confidence": round(self._total_confidence / total, 4),
                "recent_avg_confidence": round(
                    sum(recent_confidences) / max(len(recent_confidences), 1), 4
                ),
                "cache_hits": self._cache_hits,
                "cache_misses": self._cache_misses,
                "cache_hit_rate": round(self._cache_hits / total, 4),
                "cache_evictions": self._cache_evictions,
                "uptime_seconds": round(time.time() - self._started_at, 1),
            }

    def get_recent_queries(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Return the most recent query records."""
        with self._lock:
            recs = list(self._records)[-limit:]
        return [
            {
                "query": r.query,
                "response_time_ms": round(r.response_time_ms, 3),
                "confidence": round(r.confidence, 4),
                "cache_hit": r.cache_hit,
                "timestamp": r.timestamp,
            }
            for r in reversed(recs)
        ]

    def reset(self) -> None:
        """Reset all counters (useful for testing)."""
        with self._lock:
            self._records.clear()
            self._total_queries = 0
            self._cache_hits = 0
            self._cache_misses = 0
            self._total_latency_ms = 0.0
            self._total_confidence = 0.0
            self._cache_evictions = 0
            self._started_at = time.time()


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

_monitor: Optional[PerformanceMonitor] = None


def get_monitor() -> PerformanceMonitor:
    global _monitor
    if _monitor is None:
        _monitor = PerformanceMonitor()
    return _monitor
