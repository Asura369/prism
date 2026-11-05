from __future__ import annotations

from types import SimpleNamespace

import pytest

from prism.adapters.llm.openai import OpenAIAdapter
from prism.config import OpenAICompatConfig


class _StubCompletions:
    def __init__(self, content: str, finish_reason: str = "stop"):
        self.content = content
        self.finish_reason = finish_reason
        self.kwargs: dict | None = None

    def create(self, **kwargs):
        self.kwargs = kwargs
        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(content=self.content),
                    finish_reason=self.finish_reason,
                )
            ]
        )


class _StubClient:
    def __init__(self, content: str, finish_reason: str = "stop"):
        self.completions = _StubCompletions(content, finish_reason)
        self.chat = SimpleNamespace(completions=self.completions)


def _adapter(
    content: str,
    base_url: str = "https://api.example.com/v1",
    finish_reason: str = "stop",
    extra_body: dict | None = None,
) -> tuple[OpenAIAdapter, _StubClient]:
    cfg = OpenAICompatConfig(
        base_url=base_url,
        model="test-model",
        extra_body=extra_body or {},
    )
    adapter = OpenAIAdapter(cfg, api_key="sk-test")
    client = _StubClient(content, finish_reason)
    adapter._client = client
    return adapter, client


def test_sends_json_mode_and_provider_extra_body():
    adapter, client = _adapter('{"ok": true}', extra_body={"thinking": {"type": "disabled"}})
    result = adapter.complete("Return JSON. Example: {\"ok\": true}", json_schema={"type": "object"})
    assert result == '{"ok": true}'
    assert client.completions.kwargs is not None
    kwargs = client.completions.kwargs
    assert kwargs["model"] == "test-model"
    assert kwargs["response_format"] == {"type": "json_object"}
    assert kwargs["extra_body"] == {"thinking": {"type": "disabled"}}
    assert "json" in kwargs["messages"][-1]["content"].lower()


def test_blank_json_output_raises_for_retry():
    adapter, _ = _adapter("   \n  ")
    with pytest.raises(ValueError):
        adapter.complete("Return JSON.", json_schema={"type": "object"})


def test_truncated_output_raises_for_retry():
    adapter, _ = _adapter('{"partial":', finish_reason="length")
    with pytest.raises(ValueError):
        adapter.complete("Return JSON.", json_schema={"type": "object"})


def test_reasoning_model_quirks_rename_tokens_and_drop_temperature():
    adapter, client = _adapter('{"ok": true}')
    adapter.cfg.max_tokens_param = "max_completion_tokens"
    adapter.cfg.send_temperature = False
    adapter.complete("Return JSON.", json_schema={"type": "object"}, max_tokens=321)
    assert client.completions.kwargs is not None
    kwargs = client.completions.kwargs
    assert kwargs["max_completion_tokens"] == 321
    assert "max_tokens" not in kwargs
    assert "temperature" not in kwargs


def test_json_mode_off_omits_response_format():
    adapter, client = _adapter('{"ok": true}')
    adapter.cfg.json_mode = False
    adapter.complete("Return JSON.", json_schema={"type": "object"})
    assert client.completions.kwargs is not None
    assert "response_format" not in client.completions.kwargs


def test_extra_body_is_omitted_when_not_configured():
    adapter, client = _adapter('{"ok": true}')
    adapter.complete("Return JSON.", json_schema={"type": "object"})
    assert client.completions.kwargs is not None
    assert "extra_body" not in client.completions.kwargs
