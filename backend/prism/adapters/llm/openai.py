from __future__ import annotations

import importlib.util
import json
from typing import Any

from ...config import OpenAICompatConfig, Secrets
from ..base import LLMAdapter


class OpenAIAdapter(LLMAdapter):
    """Chat completions for any OpenAI-compatible provider."""

    name = "openai_compat"

    def __init__(self, cfg: OpenAICompatConfig, secrets: Secrets | None = None):
        self.cfg = cfg
        self.secrets = secrets or Secrets()
        self._client: Any = None

    def is_available(self) -> bool:
        return bool(self.secrets.llm_key) and importlib.util.find_spec("openai") is not None

    def _get_client(self) -> Any:
        if self._client is None:
            from openai import OpenAI  # imported lazily; optional dependency

            self._client = OpenAI(
                api_key=self.secrets.llm_key,
                base_url=self.cfg.base_url,
                timeout=self.cfg.timeout_s,
            )
        return self._client

    def complete(
        self,
        prompt: str,
        *,
        system: str | None = None,
        json_schema: dict[str, Any] | None = None,
        temperature: float = 0.7,
        max_tokens: int = 1500,
    ) -> str:
        messages: list[dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        if json_schema:
            prompt = f"{prompt}\n\nReturn only JSON matching this schema:\n{json.dumps(json_schema)}"
        messages.append({"role": "user", "content": prompt})
        kwargs: dict[str, Any] = {
            "model": self.cfg.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if json_schema:
            kwargs["response_format"] = {"type": "json_object"}
        if self.cfg.extra_body:
            # Provider-specific request fields (e.g. DeepSeek thinking control).
            kwargs["extra_body"] = self.cfg.extra_body
        response = self._get_client().chat.completions.create(**kwargs)
        choice = response.choices[0]
        if getattr(choice, "finish_reason", None) == "length":
            raise ValueError("Completion truncated at max_tokens; retrying")
        content = choice.message.content or ""
        if not content.strip():
            # JSON Output can return whitespace-only content; retry upstream.
            raise ValueError("Empty completion content; retrying")
        return content

    @property
    def model(self) -> str:
        return self.cfg.model
