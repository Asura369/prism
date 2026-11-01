from __future__ import annotations

import io
import json
import sqlite3
import zipfile
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from .. import db
from ..domain import JobStatus
from .common import api_error, get_conn, job_payload, review_dir, summary_payload

router = APIRouter(prefix="/review", tags=["review"])

PLATFORMS = {"instagram_feed", "instagram_story"}


class MetadataPatch(BaseModel):
    title: str | None = Field(default=None, max_length=120)
    caption: str | None = Field(default=None, max_length=2200)
    hashtags: list[str] | None = None
    platforms: list[str] | None = None
    alt_text: list[str] | None = None


class RejectBody(BaseModel):
    reason: str = Field(min_length=1, max_length=500)


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError:
        return None


def _review_or_404(request: Request, conn: sqlite3.Connection, job_id: str):
    row = db.get_job_row(conn, job_id)
    directory = review_dir(request, job_id)
    if row is None or not directory.exists():
        raise api_error(404, "review_not_found", f"Review artifact not found: {job_id}")
    return row, directory


@router.get("")
def list_review(request: Request, decision: str | None = None, conn: sqlite3.Connection = Depends(get_conn)):
    db.fail_stale_running_jobs(conn, request.app.state.cfg.run.worker_heartbeat_stale_s)
    sql = (
        "SELECT j.*, r.metadata AS review_metadata, r.decision AS review_decision "
        "FROM review_meta r JOIN jobs j ON j.job_id = r.job_id "
    )
    params: list[Any] = []
    if decision:
        sql += "WHERE r.decision = ? "
        params.append(decision)
    else:
        sql += "WHERE j.status = 'REVIEW_READY' AND r.decision IS NULL "
    sql += "ORDER BY j.created_at DESC LIMIT 200"
    items = []
    for row in conn.execute(sql, params).fetchall():
        metadata = json.loads(row["review_metadata"]) if row["review_metadata"] else {}
        summary = summary_payload(request, row)
        summary.update(
            {
                "title": metadata.get("title", row["topic"]),
                "caption": metadata.get("caption", ""),
                "decision": row["review_decision"],
            }
        )
        items.append(summary)
    return items


@router.get("/{job_id}")
def get_review(job_id: str, request: Request, conn: sqlite3.Connection = Depends(get_conn)):
    row, directory = _review_or_404(request, conn, job_id)
    metadata = _read_json(directory / "metadata.json") or {}
    manifest = _read_json(directory / "manifest.json") or {}
    slides = sorted(directory.glob("slides/*.png"))
    total_size = sum(p.stat().st_size for p in directory.rglob("*") if p.is_file())
    return {
        "job": job_payload(row),
        "metadata": metadata,
        "manifest": manifest,
        "technical": {
            "slide_count": len(slides),
            "resolution": manifest.get("resolution", "1080x1350"),
            "style": manifest.get("style", "cream"),
            "total_size_bytes": total_size,
        },
        "artifact_urls": {
            "slides": [f"/media/review/{job_id}/slides/{p.name}" for p in slides],
            "thumbnail": f"/media/review/{job_id}/thumbnail.png",
            "download": f"/api/review/{job_id}/download",
        },
    }


@router.patch("/{job_id}/metadata")
def patch_metadata(
    job_id: str,
    body: MetadataPatch,
    request: Request,
    conn: sqlite3.Connection = Depends(get_conn),
):
    row, directory = _review_or_404(request, conn, job_id)
    metadata_path = directory / "metadata.json"
    metadata = _read_json(metadata_path) or {}

    if body.title is not None:
        metadata["title"] = body.title.strip()
    if body.caption is not None:
        if len(body.caption) > request.app.state.cfg.validation.caption_max_chars:
            raise api_error(400, "caption_too_long", "Caption exceeds the configured limit")
        metadata["caption"] = body.caption
    if body.hashtags is not None:
        hashtags = [h.strip().lstrip("#").strip() for h in body.hashtags if h.strip()]
        if len(hashtags) > request.app.state.cfg.validation.hashtags_max:
            raise api_error(400, "too_many_hashtags", "Too many hashtags")
        metadata["hashtags"] = hashtags
    if body.platforms is not None:
        bad = set(body.platforms) - PLATFORMS
        if bad:
            raise api_error(400, "invalid_platform", f"Unknown platforms: {sorted(bad)}")
        metadata["platforms"] = body.platforms
    if body.alt_text is not None:
        slide_count = len(list((directory / "slides").glob("*.png")))
        if len(body.alt_text) != slide_count:
            raise api_error(400, "alt_text_count_mismatch", f"Expected {slide_count} alt texts")
        if any(not t.strip() for t in body.alt_text):
            raise api_error(400, "empty_alt_text", "Alt text cannot be empty")
        metadata["alt_text"] = [t.strip() for t in body.alt_text]

    metadata["ai_disclosure"] = True
    metadata.setdefault("platforms", ["instagram_feed"])
    temp = metadata_path.with_suffix(".json.tmp")
    temp.write_text(json.dumps(metadata, indent=2))
    temp.replace(metadata_path)

    manifest = _read_json(directory / "manifest.json") or {}
    db.upsert_review_meta(conn, job_id, metadata=metadata, manifest=manifest)
    db.append_event(conn, job_id, stage="review", progress=None, message="Metadata updated")
    return {"metadata": metadata}


def _decision(request: Request, conn: sqlite3.Connection, job_id: str, status: JobStatus, decision: str, reason: str | None = None):
    row, directory = _review_or_404(request, conn, job_id)
    if row["status"] != JobStatus.REVIEW_READY.value:
        raise api_error(409, "not_reviewable", f"Job is {row['status']}; only REVIEW_READY can be decided")
    now = db.iso(db.now_utc())
    db.update_job_status(conn, job_id, status, finished_at=now)
    db.set_review_decision(conn, job_id, decision)
    status_path = directory / "status.json"
    status_data = _read_json(status_path) or {}
    status_data.update({"job_id": job_id, "status": status.value, "decided_at": now, "decision": decision})
    if reason:
        status_data["reason"] = reason
    status_path.write_text(json.dumps(status_data, indent=2))
    db.append_event(
        conn,
        job_id,
        stage="review",
        progress=None,
        message=f"Review {decision}" + (f": {reason}" if reason else ""),
    )


@router.post("/{job_id}/approve")
def approve(job_id: str, request: Request, conn: sqlite3.Connection = Depends(get_conn)):
    _decision(request, conn, job_id, JobStatus.APPROVED, "approved")
    return {"ok": True}


@router.post("/{job_id}/reject")
def reject(
    job_id: str,
    body: RejectBody,
    request: Request,
    conn: sqlite3.Connection = Depends(get_conn),
):
    _decision(request, conn, job_id, JobStatus.REJECTED, "rejected", reason=body.reason.strip())
    return {"ok": True}


@router.get("/{job_id}/download")
def download(job_id: str, request: Request, conn: sqlite3.Connection = Depends(get_conn)):
    _, directory = _review_or_404(request, conn, job_id)
    metadata = _read_json(directory / "metadata.json") or {}
    manifest = _read_json(directory / "manifest.json") or {}
    status_data = _read_json(directory / "status.json") or {}

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for slide in sorted(directory.glob("slides/*.png")):
            zf.write(slide, f"slides/{slide.name}")
        caption = metadata.get("caption", "")
        hashtags = " ".join(f"#{h}" for h in metadata.get("hashtags", []))
        zf.writestr("caption.txt", (caption + ("\n\n" + hashtags if hashtags else "")).strip() + "\n")
        zf.writestr("metadata.json", json.dumps(metadata, indent=2))
        zf.writestr("manifest.json", json.dumps(manifest, indent=2))
        zf.writestr("status.json", json.dumps(status_data, indent=2))
    buffer.seek(0)
    return StreamingResponse(
        buffer,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="prism-{job_id}.zip"'},
    )
