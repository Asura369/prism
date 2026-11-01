from __future__ import annotations

from types import SimpleNamespace

import pytest

from prism.adapters.llm.openai import OpenAIAdapter
from prism.config import OpenAICompatConfig, Secrets


class _FakeCompletions:
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


class _FakeClient:
    def __init__(self, content: str, finish_reason: str = "stop"):
        self.completions = _FakeCompletions(content, finish_reason)
        self.chat = SimpleNamespace(completions=self.completions)


def _adapter(
    content: str,
    base_url: str = "https://api.example.com/v1",
    finish_reason: str = "stop",
    extra_body: dict | None = None,
) -> tuple[OpenAIAdapter, _FakeClient]:
    secrets = Secrets(llm_key="sk-test", fake_adapters=False, prism_config="", prism_db_path="", _env_file=None)
    cfg = OpenAICompatConfig(
        base_url=base_url,
        model="test-model",
        extra_body=extra_body or {},
    )
    adapter = OpenAIAdapter(cfg, secrets)
    client = _FakeClient(content, finish_reason)
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


def test_extra_body_is_omitted_when_not_configured():
    adapter, client = _adapter('{"ok": true}')
    adapter.complete("Return JSON.", json_schema={"type": "object"})
    assert client.completions.kwargs is not None
    assert "extra_body" not in client.completions.kwargs
