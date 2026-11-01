from __future__ import annotations

import logging
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from . import db
from .adapters.resolver import AdapterResolver
from .api import health, jobs, plugins, review
from .config import Config, Secrets, get_secrets, load_config, resolve_path
from .errors import AdapterUnavailable, ConfigError, JobNotFound, PrismError
from .plugins.registry import PluginRegistry

log = logging.getLogger("prism.api")
ROOT = Path(__file__).resolve().parents[2]


def create_app(cfg: Config | None = None, secrets: Secrets | None = None) -> FastAPI:
    cfg = cfg or load_config()
    secrets = secrets or get_secrets()
    db_path = resolve_path(cfg.run.db_path, cfg.base_dir)
    review_path = resolve_path(cfg.run.output_dir, cfg.base_dir)
    work_path = resolve_path(cfg.run.work_dir, cfg.base_dir)
    for path in (review_path, work_path, db_path.parent):
        path.mkdir(parents=True, exist_ok=True)
    db.init_db(db_path)

    resolver = AdapterResolver(cfg, secrets)
    registry = PluginRegistry(cfg, resolver)

    app = FastAPI(title="Prism", version="0.1.0")
    app.state.cfg = cfg
    app.state.secrets = secrets
    app.state.db_path = db_path
    app.state.review_path = review_path
    app.state.resolver = resolver
    app.state.registry = registry
    app.state.logger = log

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health.router, prefix="/api")
    app.include_router(jobs.router, prefix="/api")
    app.include_router(plugins.router, prefix="/api")
    app.include_router(review.router, prefix="/api")
    app.mount("/media/review", StaticFiles(directory=str(review_path)), name="review-media")

    @app.exception_handler(HTTPException)
    async def http_error_handler(request: Request, exc: HTTPException):
        if isinstance(exc.detail, dict):
            return JSONResponse(status_code=exc.status_code, content=exc.detail)
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": "http_error", "message": str(exc.detail)},
        )

    @app.exception_handler(PrismError)
    async def prism_error_handler(request: Request, exc: PrismError):
        status = 400
        if isinstance(exc, JobNotFound):
            status = 404
        elif isinstance(exc, AdapterUnavailable):
            status = 409
        elif isinstance(exc, ConfigError):
            status = 500
        code = "".join(("-" + c.lower()) if c.isupper() else c for c in exc.error_class).lstrip("-")
        return JSONResponse(
            status_code=status,
            content={"error": code, "message": exc.message, "context": exc.context},
        )

    dist = ROOT / "frontend" / "dist"
    if (dist / "index.html").exists():
        app.mount("/assets", StaticFiles(directory=str(dist / "assets")), name="frontend-assets")

        @app.get("/{full_path:path}", include_in_schema=False)
        async def spa_fallback(full_path: str):
            dist_root = dist.resolve()
            candidate = (dist / full_path).resolve()
            if full_path and candidate.is_relative_to(dist_root) and candidate.is_file():
                return FileResponse(candidate)
            return FileResponse(dist / "index.html")

    return app


app = create_app()
