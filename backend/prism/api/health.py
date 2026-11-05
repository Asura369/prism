from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel

from .. import db
from ..providers.config import STUB_ONLY_KEY, effective_llm
from .common import get_conn

router = APIRouter(tags=["health"])


@router.get("/health")
def health(request: Request, conn: sqlite3.Connection = Depends(get_conn)):
    cfg = request.app.state.cfg
    alive, last = db.worker_alive(conn, cfg.run.worker_heartbeat_stale_s)
    return {
        "web": "ok",
        "worker": {"last_heartbeat": last, "alive": alive},
        "db": "ok",
    }


@router.get("/settings")
def settings(request: Request):
    cfg = request.app.state.cfg
    resolver = request.app.state.resolver
    effective = effective_llm(request.app.state.db_path)
    data = cfg.model_dump(mode="json", exclude={"base_dir"})
    return {
        "config": data,
        "llm": {
            "provider": effective.provider if effective else None,
            "model": effective.config.model if effective else None,
            "base_url": effective.config.base_url if effective else None,
            "key_set": effective is not None,
        },
        "adapters": resolver.availability(),
        "styles": resolver.style_names(),
        "stub_only": resolver.stub_only(),
    }


class StubOnlyBody(BaseModel):
    enabled: bool


@router.put("/settings/stub-only")
def set_stub_only(body: StubOnlyBody, request: Request, conn=Depends(get_conn)):
    """Testing mode: run every job on the stub adapters, so feature work costs no API calls."""
    if body.enabled:
        db.set_setting(conn, STUB_ONLY_KEY, "1")
    else:
        db.delete_setting(conn, STUB_ONLY_KEY)
    request.app.state.resolver.refresh_llm()
    return {"stub_only": body.enabled}

