from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends, Request

from .. import db
from ..providers.config import effective_llm
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
    secrets = request.app.state.secrets
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
        "stub_adapters": secrets.stub_adapters,
    }

