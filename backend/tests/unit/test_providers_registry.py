from __future__ import annotations

from pathlib import Path

from prism.providers.registry import ProviderRegistry


def test_shipped_providers_load():
    registry = ProviderRegistry()
    assert registry.names() == ["deepseek", "openai", "opencode_go"]
    for desc in registry.list():
        assert desc.base_url.startswith("https://")
        assert desc.default_model
        assert desc.label


def test_provider_quirks_are_data():
    registry = ProviderRegistry()
    opencode = registry.get("opencode_go")
    assert opencode is not None
    assert opencode.json_mode is False
    assert opencode.headers["x-opencode-session"]
    assert opencode.models == ("deepseek-v4.1-flash",)

    deepseek = registry.get("deepseek")
    assert deepseek is not None
    assert deepseek.json_mode is True
    assert deepseek.default_model == "deepseek-flash"
    assert deepseek.models == ("deepseek-flash",)
    assert deepseek.extra_body == {"thinking": {"type": "disabled"}}


def test_reasoning_provider_parameter_quirks():
    openai = ProviderRegistry().get("openai")
    assert openai is not None
    assert openai.default_model == "gpt-6-luna"
    assert openai.models == ("gpt-6-luna",)
    assert openai.max_tokens_param == "max_completion_tokens"
    assert openai.send_temperature is False


def test_bad_manifest_is_skipped(tmp_path: Path):
    good = tmp_path / "good"
    good.mkdir()
    (good / "manifest.yaml").write_text(
        "name: good\nlabel: Good\nbase_url: https://good.example/v1\ndefault_model: m\n"
    )
    bad = tmp_path / "bad"
    bad.mkdir()
    (bad / "manifest.yaml").write_text("name: bad\nlabel: Bad\nbase_url: file:///etc\ndefault_model: m\n")

    registry = ProviderRegistry(tmp_path)
    assert registry.names() == ["good"]
