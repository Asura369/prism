from __future__ import annotations

import json
import random
import sqlite3
import uuid
from typing import Any

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field

from .. import db
from ..domain import Job, JobStatus
from .common import api_error, event_payload, get_conn, job_payload, stage_payloads, summary_payload

router = APIRouter(prefix="/jobs", tags=["jobs"])


class CreateJobBody(BaseModel):
    plugin: str
    topic: str = Field(min_length=1, max_length=200)
    angle: dict[str, Any] | None = None
    recommended_plugin: str | None = None
    overrides: dict[str, Any] = Field(default_factory=dict)


class RetryBody(BaseModel):
    overrides: dict[str, Any] | None = None


def _new_seed() -> int:
    return random.SystemRandom().randint(0, 2**31 - 1)


def _build_job(conn: sqlite3.Connection, body: CreateJobBody, plugin: str, seed: int) -> str:
    job_id = "job_" + uuid.uuid4().hex[:12]
    overrides = dict(body.overrides)
    overrides["seed"] = seed
    job = Job(
        job_id=job_id,
        plugin=plugin,
        topic=body.topic.strip(),
        angle=body.angle,
        overrides=overrides,
        status=JobStatus.QUEUED,
        stage=None,
        progress=0.0,
        error=None,
        created_at=db.now_utc(),
        started_at=None,
        finished_at=None,
    )
    db.insert_job(conn, job, seed, body.recommended_plugin)
    db.append_event(conn, job_id, stage=None, progress=0.0, message="Job queued")
    return job_id


@router.post("", status_code=201)
def create_job(body: CreateJobBody, request: Request, conn: sqlite3.Connection = Depends(get_conn)):
    info = request.app.state.registry.get_info(body.plugin)
    if info is None:
        raise api_error(404, "plugin_not_found", f"Unknown plugin: {body.plugin}")
    if not info.available:
        raise api_error(
            409,
            "plugin_unavailable",
            f"{body.plugin} is missing adapters: {', '.join(info.missing_adapters)}",
        )
    seed = body.overrides.get("seed")
    seed = int(seed) if isinstance(seed, (int, str)) and str(seed).isdigit() else _new_seed()
    job_id = _build_job(conn, body, body.plugin, seed)
    return {"job_id": job_id}


@router.get("")
def list_jobs(
    request: Request,
    status: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    conn: sqlite3.Connection = Depends(get_conn),
):
    if status and status not in {s.value for s in JobStatus}:
        raise api_error(400, "invalid_status", f"Unknown status: {status}")
    stale = db.fail_stale_running_jobs(conn, request.app.state.cfg.run.worker_heartbeat_stale_s)
    if stale:
        request.app.state.logger.info("marked %d stale RUNNING job(s) FAILED", len(stale))
    rows, total = db.list_jobs(conn, status=status, limit=limit, offset=offset)
    return {"items": [summary_payload(request, row) for row in rows], "total": total}


@router.get("/{job_id}")
def get_job(job_id: str, request: Request, conn: sqlite3.Connection = Depends(get_conn)):
    db.fail_stale_running_jobs(conn, request.app.state.cfg.run.worker_heartbeat_stale_s)
    row = db.get_job_row(conn, job_id)
    if row is None:
        raise api_error(404, "job_not_found", f"Job not found: {job_id}")
    job = job_payload(row)
    events = db.list_events(conn, job_id)
    return {
        "job": job,
        "stages": stage_payloads(request, job),
        "events_tail": [event_payload(e) for e in events[-20:]],
    }


@router.get("/{job_id}/events")
def get_events(job_id: str, since: int = 0, conn: sqlite3.Connection = Depends(get_conn)):
    if db.get_job(conn, job_id) is None:
        raise api_error(404, "job_not_found", f"Job not found: {job_id}")
    return [event_payload(row) for row in db.list_events(conn, job_id, since=since)]


@router.get("/{job_id}/logs", response_class=PlainTextResponse)
def get_logs(job_id: str, conn: sqlite3.Connection = Depends(get_conn)):
    if db.get_job(conn, job_id) is None:
        raise api_error(404, "job_not_found", f"Job not found: {job_id}")
    lines = []
    for row in db.list_events(conn, job_id, limit=10_000):
        lines.append(f"{row['ts']} [{row['level']}] {row['stage'] or '-'}: {row['message']}")
    return "\n".join(lines) + ("\n" if lines else "")


@router.post("/{job_id}/cancel")
def cancel_job(job_id: str, conn: sqlite3.Connection = Depends(get_conn)):
    job = db.get_job(conn, job_id)
    if job is None:
        raise api_error(404, "job_not_found", f"Job not found: {job_id}")
    if job.status not in (JobStatus.QUEUED, JobStatus.RUNNING):
        raise api_error(409, "not_cancellable", f"Job is {job.status.value}; only QUEUED or RUNNING can be cancelled")
    db.update_job_status(
        conn, job_id, JobStatus.CANCELLED, finished_at=db.iso(db.now_utc())
    )
    db.append_event(conn, job_id, stage=job.stage, progress=None, message="Cancelled by user")
    return {"ok": True}


@router.post("/{job_id}/retry", status_code=201)
def retry_job(job_id: str, request: Request, body: RetryBody | None = None, conn: sqlite3.Connection = Depends(get_conn)):
    row = db.get_job_row(conn, job_id)
    if row is None:
        raise api_error(404, "job_not_found", f"Job not found: {job_id}")
    if row["status"] in ("RUNNING", "QUEUED"):
        raise api_error(409, "not_retryable", f"Job is {row['status']}; wait for it to finish")
    info = request.app.state.registry.get_info(row["plugin"])
    if info is None or not info.available:
        raise api_error(409, "plugin_unavailable", f"Plugin unavailable: {row['plugin']}")
    overrides = json.loads(row["overrides"] or "{}")
    if body and body.overrides:
        overrides.update(body.overrides)
    seed = _new_seed()
    overrides["seed"] = seed
    new_id = "job_" + uuid.uuid4().hex[:12]
    job = Job(
        job_id=new_id,
        plugin=row["plugin"],
        topic=row["topic"],
        angle=json.loads(row["angle_json"]) if row["angle_json"] else None,
        overrides=overrides,
        status=JobStatus.QUEUED,
        stage=None,
        progress=0.0,
        error=None,
        created_at=db.now_utc(),
        started_at=None,
        finished_at=None,
    )
    db.insert_job(conn, job, seed, row["recommended_plugin"])
    db.append_event(conn, new_id, stage=None, progress=0.0, message=f"Retry of {job_id}")
    return {"job_id": new_id}
