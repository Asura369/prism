from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from .. import db
from ..config import OpenAICompatConfig
from .registry import ProviderDescriptor, ProviderRegistry

ACTIVE_KEY = "llm.active_provider"
STUB_ONLY_KEY = "testing.stub_only"
LLM_TIMEOUT_S = 60


def secret_name(provider_id: str) -> str:
    return f"provider.{provider_id}.api_key"


def stub_only_enabled(db_path: str | Path | None = None) -> bool:
    """Testing mode: every job runs on the deterministic stub adapters, no API calls."""
    if db_path is None:
        return False
    conn = db.connect(db_path)
    try:
        return db.get_setting(conn, STUB_ONLY_KEY) == "1"
    finally:
        conn.close()


@lru_cache(maxsize=1)
def _registry() -> ProviderRegistry:
    return ProviderRegistry()


@dataclass(frozen=True)
class EffectiveLLM:
    """The one active connection: descriptor quirks + stored key."""

    config: OpenAICompatConfig
    api_key: str
    provider: str


def _config_from(desc: ProviderDescriptor) -> OpenAICompatConfig:
    return OpenAICompatConfig(
        base_url=desc.base_url,
        model=desc.default_model,
        timeout_s=LLM_TIMEOUT_S,
        extra_body=dict(desc.extra_body),
        headers=dict(desc.headers),
        json_mode=desc.json_mode,
        max_tokens_param=desc.max_tokens_param,
        send_temperature=desc.send_temperature,
    )


def effective_llm(db_path: str | Path | None = None) -> EffectiveLLM | None:
    """One source, the database. No configured provider means no LLM adapter."""
    if db_path is None:
        return None
    conn = db.connect(db_path)
    try:
        active = db.get_setting(conn, ACTIVE_KEY)
        if not active:
            return None
        key = db.get_secret(conn, secret_name(active))
    finally:
        conn.close()

    desc = _registry().get(active) if active else None
    if desc is None or not key:
        return None
    return EffectiveLLM(config=_config_from(desc), api_key=key, provider=desc.name)
