"""
Q&A REST API Endpoints

Provides:
  GET  /api/qa/search?q=<query>&limit=3   – smart Q&A search with metrics
  GET  /api/qa/metrics                     – performance metrics & statistics
  GET  /api/qa/cache-stats                 – detailed cache statistics
  POST /api/qa/reload-index                – force reload indexes (admin)
"""

import logging
import time

from fastapi import APIRouter, HTTPException, Query

from app.audio.smart_qa_fetcher import get_fetcher
from app.audio.qa_metrics import get_monitor
from app.audio.optimized_knowledge_base import get_optimized_kb

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/qa", tags=["Q&A"])


@router.get("/search")
async def search_qa(
    q: str = Query(..., min_length=1, description="Search query"),
    limit: int = Query(3, ge=1, le=10, description="Max results to return"),
):
    """
    Smart Q&A search using multi-stage indexing and caching.

    Returns top-K matches sorted by confidence score.
    Includes per-request latency metadata.
    """
    if not q.strip():
        raise HTTPException(status_code=400, detail="Query parameter 'q' must not be blank")

    t0 = time.perf_counter()
    fetcher = get_fetcher()
    results = fetcher.fetch(q, top_k=limit)
    elapsed_ms = round((time.perf_counter() - t0) * 1000, 3)

    return {
        "query": q,
        "results": results,
        "count": len(results),
        "response_time_ms": elapsed_ms,
    }


@router.get("/metrics")
async def get_metrics():
    """
    Return real-time performance metrics for the Q&A system.

    Includes average latency, confidence scores, and cache hit rate.
    """
    monitor = get_monitor()
    metrics = monitor.get_metrics()
    recent = monitor.get_recent_queries(limit=10)

    kb = get_optimized_kb()
    kb_stats = kb.get_stats()

    return {
        "performance": metrics,
        "knowledge_base": kb_stats,
        "recent_queries": recent,
    }


@router.get("/cache-stats")
async def get_cache_stats():
    """
    Return detailed cache statistics (LRU + semantic cache).
    """
    fetcher = get_fetcher()
    return fetcher.cache_stats()


@router.post("/reload-index")
async def reload_index():
    """
    Force a full reload of the Q&A indexes and clear all caches.

    This is an admin operation. It may take a few milliseconds.
    """
    t0 = time.perf_counter()
    fetcher = get_fetcher()
    fetcher.reload()
    elapsed_ms = round((time.perf_counter() - t0) * 1000, 3)

    kb = get_optimized_kb()
    stats = kb.get_stats()

    logger.info(f"QA index reloaded in {elapsed_ms:.1f} ms ({stats['total_qa_pairs']} pairs)")
    return {
        "status": "reloaded",
        "reload_time_ms": elapsed_ms,
        "knowledge_base": stats,
    }
