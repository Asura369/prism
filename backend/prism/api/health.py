from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends, Request

from .. import db
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
    data = cfg.model_dump(mode="json", exclude={"base_dir"})
    return {
        "config": data,
        "keys": {
            "LLM_KEY": "SET" if secrets.llm_key else "UNSET",
        },
        "adapters": resolver.availability(),
        "styles": resolver.style_names(),
        "fake_adapters": secrets.fake_adapters,
    }


@router.post("/settings/selftest")
def selftest(request: Request):
    resolver = request.app.state.resolver
    result = {}
    for interface in ("llm", "cards", "export"):
        chain = resolver.resolve(interface)
        result[interface] = {
            "available": bool(chain),
            "selected": getattr(chain[0], "name", None) if chain else None,
            "adapters": resolver.availability().get(interface, []),
        }
    return result
