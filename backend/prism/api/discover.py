from __future__ import annotations

import sqlite3
from dataclasses import asdict
from typing import Any

from fastapi import APIRouter, Depends, File, Query, Request, UploadFile
from pydantic import BaseModel, Field

from ..errors import AngleGenerationError, InvalidTrendsCSV
from ..plugins.registry import PluginRegistry
from .common import api_error, get_conn
from ..discovery.angles import (
    default_plugin_for,
    generate_angles,
    store_generated_angles,
)
from ..discovery.cache import load_angles, load_scored, scored_to_dict
from ..discovery.service import fetch_trends, score_and_store
from ..discovery.sources.csv_upload import parse_trends_csv
from ..discovery.sources.manual import create_manual_candidate

router = APIRouter(prefix="/discover", tags=["discover"])


class ManualBody(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    snippet: str = ""
    url: str = ""


class AnglesBody(BaseModel):
    candidate_id: str


class SelectBody(BaseModel):
    candidate_id: str
    angle_index: int = Field(ge=0, le=2)
    plugin: str


def _parse_sources(raw: str | None) -> list[str] | None:
    if raw is None:
        return None
    return [part.strip() for part in raw.split(",") if part.strip()]


@router.get("/trends")
def trends(
    request: Request,
    region: str = "US",
    window_h: int = Query(default=24, ge=1, le=168),
    sources: str | None = None,
    conn: sqlite3.Connection = Depends(get_conn),
):
    payload = fetch_trends(
        request.app.state.cfg,
        conn,
        request.app.state.resolver,
        region=region,
        window_h=window_h,
        sources=_parse_sources(sources),
    )
    return payload


@router.post("/manual")
def manual(body: ManualBody, request: Request, conn: sqlite3.Connection = Depends(get_conn)):
    candidate = create_manual_candidate(body.title, body.snippet, body.url)
    scored = score_and_store(request.app.state.cfg, conn, request.app.state.resolver, [candidate])
    if not scored:
        raise api_error(400, "unsafe_candidate", "This candidate did not pass the safety filter")
    item = scored[0]
    return {
        "candidate_id": item.candidate.id,
        "score": asdict(item.score),
        "candidate": scored_to_dict(item),
    }


@router.post("/trends/upload")
def upload_trends(
    request: Request,
    file: UploadFile = File(...),
    conn: sqlite3.Connection = Depends(get_conn),
):
    content = file.file.read()
    filename = file.filename or "trends.csv"
    try:
        candidates = parse_trends_csv(content, filename)
    except InvalidTrendsCSV as exc:
        raise api_error(400, "invalid_trends_csv", exc.message) from exc
    scored = score_and_store(request.app.state.cfg, conn, request.app.state.resolver, candidates)
    return {
        "imported_count": len(candidates),
        "candidates": [scored_to_dict(item) for item in scored],
    }


@router.post("/angles")
def angles(body: AnglesBody, request: Request, conn: sqlite3.Connection = Depends(get_conn)):
    item = load_scored(conn, body.candidate_id)
    if item is None:
        raise api_error(409, "trend_expired", "Re-discover to continue")
    try:
        generated = generate_angles(request.app.state.cfg, request.app.state.resolver, request.app.state.registry, item)
    except AngleGenerationError as exc:
        raise api_error(502, "angle_generation_failed", exc.message) from exc
    store_generated_angles(request.app.state.cfg, conn, item, generated)
    return {"angles": [asdict(angle) for angle in generated], "candidate": scored_to_dict(item)}


@router.post("/select")
def select(body: SelectBody, request: Request, conn: sqlite3.Connection = Depends(get_conn)):
    item = load_scored(conn, body.candidate_id)
    if item is None:
        raise api_error(409, "trend_expired", "Re-discover to continue")
    cached = load_angles(conn, body.candidate_id)
    if cached is None:
        raise api_error(409, "angles_expired", "Generate angles again to continue")
    registry: PluginRegistry = request.app.state.registry
    info = registry.get_info(body.plugin)
    if info is None or not info.available:
        raise api_error(409, "plugin_unavailable", f"Plugin unavailable: {body.plugin}")
    if body.angle_index >= len(cached["angles"]):
        raise api_error(400, "invalid_angle_index", "angle_index is out of range")
    angle: dict[str, Any] = dict(cached["angles"][body.angle_index])
    if "recommended_plugin" not in angle:
        angle["recommended_plugin"] = default_plugin_for(
            item.candidate,
            [i for i in registry.list_plugins() if i.available],
        )
    return {
        "draft_job_payload": {
            "plugin": body.plugin,
            "topic": item.candidate.title,
            "angle": angle,
            "recommended_plugin": angle["recommended_plugin"],
            "overrides": {},
        }
    }
