from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import asdict
from datetime import datetime, timezone

from .. import db
from ..config import Config
from ..domain import ScoredCandidate, TrendCandidate, TrendScore


def config_hash(cfg: Config) -> str:
    payload = json.dumps(cfg.discovery.model_dump(mode="json"), sort_keys=True)
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


def trends_cache_key(region: str, window_h: int, sources: list[str], cfg: Config) -> str:
    day = datetime.now(timezone.utc).date().isoformat()
    names = ",".join(sorted(sources))
    return f"trends:v1:{day}:{region.upper()}:{window_h}:{names}:{config_hash(cfg)}"


def candidate_cache_key(candidate_id: str) -> str:
    return f"candidate:v1:{candidate_id}"


def angles_cache_key(candidate_id: str) -> str:
    return f"angles:v1:{candidate_id}"


def candidate_to_dict(candidate: TrendCandidate) -> dict:
    return {
        "id": candidate.id,
        "title": candidate.title,
        "source": candidate.source,
        "url": candidate.url,
        "snippet": candidate.snippet,
        "metrics": candidate.metrics,
        "fetched_at": db.iso(candidate.fetched_at),
        "cluster_id": candidate.cluster_id,
    }


def candidate_from_dict(data: dict) -> TrendCandidate:
    return TrendCandidate(
        id=str(data["id"]),
        title=str(data["title"]),
        source=str(data["source"]),
        url=str(data.get("url", "")),
        snippet=str(data.get("snippet", "")),
        metrics=dict(data.get("metrics") or {}),
        fetched_at=datetime.fromisoformat(data["fetched_at"]),
        cluster_id=data.get("cluster_id"),
    )


def scored_to_dict(scored: ScoredCandidate) -> dict:
    return {"candidate": candidate_to_dict(scored.candidate), "score": asdict(scored.score)}


def scored_from_dict(data: dict) -> ScoredCandidate:
    return ScoredCandidate(
        candidate=candidate_from_dict(data["candidate"]),
        score=TrendScore(**data["score"]),
    )


def store_scored(conn: sqlite3.Connection, scored: ScoredCandidate, cfg: Config) -> None:
    db.cache_set(
        conn,
        candidate_cache_key(scored.candidate.id),
        json.dumps(scored_to_dict(scored)),
        cfg.discovery.cache_ttl_min,
    )


def load_scored(conn: sqlite3.Connection, candidate_id: str) -> ScoredCandidate | None:
    raw = db.cache_get(conn, candidate_cache_key(candidate_id))
    if not raw:
        return None
    try:
        return scored_from_dict(json.loads(raw))
    except (KeyError, TypeError, ValueError):
        return None


def store_angles(conn: sqlite3.Connection, candidate_id: str, payload: dict, cfg: Config) -> None:
    db.cache_set(conn, angles_cache_key(candidate_id), json.dumps(payload), cfg.discovery.cache_ttl_min)


def load_angles(conn: sqlite3.Connection, candidate_id: str) -> dict | None:
    raw = db.cache_get(conn, angles_cache_key(candidate_id))
    if not raw:
        return None
    try:
        return json.loads(raw)
    except ValueError:
        return None
