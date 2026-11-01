from __future__ import annotations

from fastapi import APIRouter, Request

from .common import api_error

router = APIRouter(prefix="/plugins", tags=["plugins"])


@router.get("")
def list_plugins(request: Request):
    infos = sorted(request.app.state.registry.list_plugins(), key=lambda i: i.name)
    return [
        {
            "name": info.name,
            "version": info.version,
            "description": info.description,
            "output_kind": info.output_kind,
            "defaults": info.defaults,
            "available": info.available,
            "missing_adapters": info.missing_adapters,
        }
        for info in infos
    ]


@router.get("/{name}")
def get_plugin(name: str, request: Request):
    info = request.app.state.registry.get_info(name)
    if info is None:
        raise api_error(404, "plugin_not_found", f"Unknown plugin: {name}")
    return info.to_dict()
