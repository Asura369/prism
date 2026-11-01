from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from fastapi import HTTPException, Request

from .. import db


def api_error(status: int, code: str, message: str) -> HTTPException:
    return HTTPException(status_code=status, detail={"error": code, "message": message})


def get_conn(request: Request):
    conn = db.connect(request.app.state.db_path)
    try:
        yield conn
    finally:
        conn.close()


def review_dir(request: Request, job_id: str) -> Path:
    return Path(request.app.state.cfg.base_dir) / request.app.state.cfg.run.output_dir / job_id


def job_payload(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "job_id": row["job_id"],
        "plugin": row["plugin"],
        "topic": row["topic"],
        "angle": json.loads(row["angle_json"]) if row["angle_json"] else None,
        "overrides": json.loads(row["overrides"] or "{}"),
        "status": row["status"],
        "stage": row["stage"],
        "progress": row["progress"],
        "error": json.loads(row["error_json"]) if row["error_json"] else None,
        "seed": row["seed"],
        "recommended_plugin": row["recommended_plugin"],
        "created_at": row["created_at"],
        "started_at": row["started_at"],
        "finished_at": row["finished_at"],
        "heartbeat_at": row["heartbeat_at"],
    }


def event_payload(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "ts": row["ts"],
        "stage": row["stage"],
        "progress": row["progress"],
        "level": row["level"],
        "message": row["message"],
    }


def stage_payloads(request: Request, job: dict[str, Any]) -> list[dict[str, Any]]:
    registry = request.app.state.registry
    names = registry.stages_for(job["plugin"])
    current = job["stage"]
    current_index = names.index(current) if current in names else -1
    out: list[dict[str, Any]] = []
    for index, name in enumerate(names):
        if job["status"] == "REVIEW_READY" or job["status"] == "APPROVED":
            status = "completed"
        elif job["status"] in {"FAILED", "CANCELLED"}:
            if index < current_index:
                status = "completed"
            elif index == current_index:
                status = "failed"
            else:
                status = "pending"
        elif job["status"] == "RUNNING":
            status = "completed" if index < current_index else "running" if index == current_index else "pending"
        else:
            status = "pending"
        out.append({"name": name, "status": status, "progress": job["progress"] if status == "running" else (1.0 if status == "completed" else 0.0)})
    return out


def thumbnail_url(request: Request, job_id: str) -> str | None:
    path = review_dir(request, job_id) / "thumbnail.png"
    return f"/media/review/{job_id}/thumbnail.png" if path.exists() else None


def summary_payload(request: Request, row: sqlite3.Row) -> dict[str, Any]:
    return {
        "job_id": row["job_id"],
        "plugin": row["plugin"],
        "topic": row["topic"],
        "status": row["status"],
        "stage": row["stage"],
        "progress": row["progress"],
        "thumbnail_url": thumbnail_url(request, row["job_id"]),
        "created_at": row["created_at"],
    }
