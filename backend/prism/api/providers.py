from __future__ import annotations

import time
from typing import Any

import httpx
from fastapi import APIRouter, Depends, Request
from openai import OpenAI
from pydantic import BaseModel, Field

from .. import db
from ..providers.config import ACTIVE_KEY, secret_name
from ..providers.registry import ProviderDescriptor, ProviderRegistry
from .common import api_error, get_conn

router = APIRouter(tags=["providers"])

MAX_KEY = 400


class ProviderKeyBody(BaseModel):
    api_key: str = Field(min_length=1, max_length=MAX_KEY)


class ProviderTestBody(BaseModel):
    api_key: str | None = Field(default=None, max_length=MAX_KEY)


def _registry(request: Request) -> ProviderRegistry:
    registry = getattr(request.app.state, "providers", None)
    if registry is None:
        registry = ProviderRegistry()
        request.app.state.providers = registry
    return registry


def _descriptor(request: Request, provider_id: str) -> ProviderDescriptor:
    desc = _registry(request).get(provider_id)
    if desc is None:
        raise api_error(404, "provider_not_found", f"Unknown provider: {provider_id}")
    return desc


def _state(conn, desc: ProviderDescriptor) -> dict[str, Any]:
    """Everything the UI may know about a provider. Never the key itself."""
    stored = db.get_secret(conn, secret_name(desc.name))
    return {
        "name": desc.name,
        "label": desc.label,
        "models": list(desc.models),
        "default_model": desc.default_model,
        "json_mode": desc.json_mode,
        "base_url": desc.base_url,
        "model": desc.default_model,
        "configured": bool(stored),
        "key_set": bool(stored),
        "active": db.get_setting(conn, ACTIVE_KEY) == desc.name,
    }


@router.get("/providers")
def list_providers(request: Request, conn=Depends(get_conn)):
    return [_state(conn, desc) for desc in _registry(request).list()]


@router.put("/providers/{provider_id}")
def save_provider_key(
    provider_id: str,
    body: ProviderKeyBody,
    request: Request,
    conn=Depends(get_conn),
):
    desc = _descriptor(request, provider_id)
    if db.get_secret(conn, secret_name(desc.name)):
        raise api_error(409, "key_already_set", "A key is already stored. Delete it before entering a new one.")

    # Base URL and model come from the manifest; the stored key *is* the configuration.
    db.set_secret(conn, secret_name(desc.name), body.api_key.strip())
    request.app.state.resolver.refresh_llm()
    return _state(conn, desc)


@router.delete("/providers/{provider_id}/key")
def delete_provider_key(provider_id: str, request: Request, conn=Depends(get_conn)):
    desc = _descriptor(request, provider_id)
    db.delete_secret(conn, secret_name(desc.name))
    if db.get_setting(conn, ACTIVE_KEY) == desc.name:
        # Active but keyless would degrade every job silently; go back to no provider.
        db.delete_setting(conn, ACTIVE_KEY)
    request.app.state.resolver.refresh_llm()
    return _state(conn, desc)


@router.post("/providers/{provider_id}/activate")
def activate_provider(provider_id: str, request: Request, conn=Depends(get_conn)):
    desc = _descriptor(request, provider_id)
    if not db.get_secret(conn, secret_name(desc.name)):
        raise api_error(409, "provider_not_configured", f"Add a key to {desc.label} before activating it.")
    db.set_setting(conn, ACTIVE_KEY, desc.name)
    request.app.state.resolver.refresh_llm()
    return _state(conn, desc)


@router.post("/providers/{provider_id}/test")
def test_provider(
    provider_id: str,
    body: ProviderTestBody,
    request: Request,
    conn=Depends(get_conn),
):
    desc = _descriptor(request, provider_id)
    key = (body.api_key or "").strip() or db.get_secret(conn, secret_name(desc.name)) or ""
    if not key:
        raise api_error(400, "missing_key", "Enter an API key first.")

    started = time.perf_counter()
    try:
        probe(desc, key=key)
    except Exception as exc:  # noqa: BLE001 - reported to the caller as a code
        return {
            "ok": False,
            "latency_ms": int((time.perf_counter() - started) * 1000),
            **_describe_failure(exc, key),
        }
    return {"ok": True, "latency_ms": int((time.perf_counter() - started) * 1000)}


def probe(desc: ProviderDescriptor, *, key: str) -> None:
    """One minimal completion against the preset. No redirects, short timeout, body discarded."""
    extra_body = dict(desc.extra_body)
    kwargs: dict[str, Any] = {
        "model": desc.default_model,
        "messages": [{"role": "user", "content": "Reply with the single word: ok"}],
        desc.max_tokens_param: 16,
    }
    if extra_body:
        kwargs["extra_body"] = extra_body
    client = OpenAI(
        api_key=key,
        base_url=desc.base_url,
        timeout=10,
        max_retries=0,
        default_headers=dict(desc.headers) or None,
        http_client=httpx.Client(follow_redirects=False, timeout=10),
    )
    client.chat.completions.create(**kwargs)


def _describe_failure(exc: Exception, key: str) -> dict[str, Any]:
    status = getattr(exc, "status_code", None)
    name = type(exc).__name__
    if "Authentication" in name or status == 401:
        code = "auth_failed"
    elif "Permission" in name or status == 403:
        code = "forbidden"
    elif status == 404:
        code = "model_not_found"
    elif "Connection" in name or "Timeout" in name:
        code = "unreachable"
    elif status:
        code = f"http_{status}"
    else:
        code = "failed"
    message = str(exc)[:300].replace(key, "***") if key else str(exc)[:300]
    return {"error": code, "message": message}
