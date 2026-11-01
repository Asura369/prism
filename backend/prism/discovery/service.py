from __future__ import annotations

import json
import logging
import sqlite3
from concurrent.futures import ThreadPoolExecutor, wait
from datetime import datetime, timezone

from .. import db
from ..adapters.resolver import AdapterResolver
from ..config import Config
from ..domain import ScoredCandidate, TrendCandidate
from .cache import scored_to_dict, store_scored, trends_cache_key
from .cluster import cluster
from .score import score_candidates
from .sources import build_sources, enabled_fetchable

log = logging.getLogger(__name__)


def fetch_trends(
    cfg: Config,
    conn: sqlite3.Connection,
    resolver: AdapterResolver,
    *,
    region: str = "US",
    window_h: int = 24,
    sources: list[str] | None = None,
) -> dict:
    region = (region or "US").upper()
    enabled = enabled_fetchable(cfg)
    selected = [name for name in (sources if sources is not None else enabled) if name in enabled]
    key = trends_cache_key(region, window_h, selected, cfg)
    cached = db.cache_get(conn, key)
    if cached:
        return json.loads(cached)

    available = build_sources(cfg)
    available = {name: source for name, source in available.items() if name in selected}
    sources_used: list[str] = []
    sources_failed: list[str] = []
    candidates: list[TrendCandidate] = []

    executor = ThreadPoolExecutor(max_workers=max(1, len(available)))
    futures = {
        executor.submit(
            source.fetch,
            region=region,
            limit=cfg.discovery.max_candidates_per_source,
            window_h=window_h,
        ): name
        for name, source in available.items()
    }
    done, not_done = wait(futures, timeout=cfg.discovery.fetch_timeout_s)
    for future in done:
        name = futures[future]
        try:
            candidates.extend(future.result())
            sources_used.append(name)
        except Exception as exc:  # noqa: BLE001 - source failure is isolated
            log.warning("trend source %s failed: %s", name, exc)
            sources_failed.append(name)
    for future in not_done:
        name = futures[future]
        future.cancel()
        sources_failed.append(name)
    executor.shutdown(wait=False, cancel_futures=True)
    sources_used.sort()
    sources_failed.sort()

    reps = cluster(candidates, cfg.discovery.clustering.threshold, cfg.discovery.scoring.source_reliability)
    scored = score_candidates(cfg, resolver, reps)[: cfg.discovery.top_n_to_ui]
    for item in scored:
        store_scored(conn, item, cfg)

    payload = {
        "fetched_at": db.iso(datetime.now(timezone.utc)),
        "sources_used": sources_used,
        "sources_failed": sources_failed,
        "candidates": [scored_to_dict(item) for item in scored],
    }
    db.cache_set(conn, key, json.dumps(payload), cfg.discovery.cache_ttl_min)
    return payload


def score_and_store(cfg: Config, conn: sqlite3.Connection, resolver: AdapterResolver, candidates: list[TrendCandidate]) -> list[ScoredCandidate]:
    scored = score_candidates(cfg, resolver, candidates)
    for item in scored:
        store_scored(conn, item, cfg)
    return scored
