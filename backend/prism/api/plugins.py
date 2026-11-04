from __future__ import annotations

from fastapi import APIRouter, Request

router = APIRouter(prefix="/plugins", tags=["plugins"])


@router.get("")
def list_plugins(request: Request):
    return [info.to_dict() for info in sorted(request.app.state.registry.list_plugins(), key=lambda i: i.name)]
