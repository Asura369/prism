from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

log = logging.getLogger(__name__)

REQUIRED = ("name", "label", "base_url", "default_model")


@dataclass(frozen=True)
class ProviderDescriptor:
    """A provider is data, not a class: every one of them speaks OpenAI chat."""

    name: str
    label: str
    base_url: str
    default_model: str
    models: tuple[str, ...] = ()
    json_mode: bool = True
    headers: dict[str, str] = field(default_factory=dict)
    extra_body: dict[str, Any] = field(default_factory=dict)
    max_tokens_param: str = "max_tokens"
    send_temperature: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "label": self.label,
            "base_url": self.base_url,
            "default_model": self.default_model,
            "models": list(self.models),
            "json_mode": self.json_mode,
            "max_tokens_param": self.max_tokens_param,
            "send_temperature": self.send_temperature,
        }


def _parse(raw: dict[str, Any], path: Path) -> ProviderDescriptor:
    missing = [key for key in REQUIRED if not isinstance(raw.get(key), str) or not raw[key].strip()]
    if missing:
        raise ValueError(f"missing required field(s): {', '.join(missing)}")
    base_url = raw["base_url"].strip()
    if not base_url.startswith(("http://", "https://")):
        raise ValueError(f"base_url must be http(s): {base_url!r}")
    models = raw.get("models") or []
    if not isinstance(models, list) or not all(isinstance(m, str) for m in models):
        raise ValueError("models must be a list of strings")
    headers = raw.get("headers") or {}
    if not isinstance(headers, dict) or not all(
        isinstance(k, str) and isinstance(v, str) for k, v in headers.items()
    ):
        raise ValueError("headers must be a string map")
    extra_body = raw.get("extra_body") or {}
    if not isinstance(extra_body, dict):
        raise ValueError("extra_body must be a mapping")
    json_mode = raw.get("json_mode", True)
    if not isinstance(json_mode, bool):
        raise ValueError("json_mode must be a boolean")
    max_tokens_param = raw.get("max_tokens_param", "max_tokens")
    if max_tokens_param not in ("max_tokens", "max_completion_tokens"):
        raise ValueError("max_tokens_param must be max_tokens or max_completion_tokens")
    send_temperature = raw.get("send_temperature", True)
    if not isinstance(send_temperature, bool):
        raise ValueError("send_temperature must be a boolean")
    return ProviderDescriptor(
        name=raw["name"].strip(),
        label=raw["label"].strip(),
        base_url=base_url,
        default_model=raw["default_model"].strip(),
        models=tuple(models),
        json_mode=json_mode,
        headers={k: v for k, v in headers.items()},
        extra_body=extra_body,
        max_tokens_param=max_tokens_param,
        send_temperature=send_temperature,
    )


class ProviderRegistry:
    """Scans providers/*/manifest.yaml. A bad manifest is skipped, not fatal."""

    def __init__(self, providers_dir: Path | None = None):
        self.providers_dir = providers_dir or Path(__file__).resolve().parent
        self._providers: dict[str, ProviderDescriptor] = {}
        self._scan()

    def _scan(self) -> None:
        for manifest_path in sorted(self.providers_dir.glob("*/manifest.yaml")):
            try:
                raw = yaml.safe_load(manifest_path.read_text()) or {}
                descriptor = _parse(raw, manifest_path)
                self._providers[descriptor.name] = descriptor
            except Exception as exc:  # noqa: BLE001 - one bad provider must not stop the app
                log.warning("Skipping provider at %s: %s", manifest_path, exc)

    def list(self) -> list[ProviderDescriptor]:
        return list(self._providers.values())

    def get(self, name: str) -> ProviderDescriptor | None:
        return self._providers.get(name)

    def names(self) -> list[str]:
        return list(self._providers)
