from __future__ import annotations

import logging

from fastapi.testclient import TestClient

from prism.config import Config, Secrets
from prism.main import create_app

KEY = "sk-test-only-1234567890"


def _client(cfg: Config) -> TestClient:
    secrets = Secrets()
    return TestClient(create_app(cfg, secrets))


def test_lists_shipped_providers_unconfigured(cfg: Config):
    with _client(cfg) as client:
        response = client.get("/api/providers")
        assert response.status_code == 200
        providers = response.json()
    assert [p["name"] for p in providers] == ["deepseek", "openai", "opencode_go"]
    assert all(p["configured"] is False and p["key_set"] is False and p["active"] is False for p in providers)


def test_presets_are_read_only_and_key_is_write_once(cfg: Config, caplog):
    caplog.set_level(logging.DEBUG)
    with _client(cfg) as client:
        saved = client.put("/api/providers/opencode_go", json={"api_key": KEY})
        assert saved.status_code == 200
        body = saved.json()
        assert body["configured"] is True and body["key_set"] is True
        assert body["base_url"] == "https://opencode.ai/inference/go/openai/v1"
        assert body["model"] == "deepseek-v4.1-flash"
        assert KEY not in saved.text

        again = client.put("/api/providers/opencode_go", json={"api_key": "sk-other"})
        assert again.status_code == 409
        assert again.json()["error"] == "key_already_set"

        for path in ("/api/providers", "/api/settings"):
            response = client.get(path)
            assert KEY not in response.text
            assert "api_key" not in response.text

    assert KEY not in caplog.text


def test_saving_a_key_ignores_tampered_endpoints(cfg: Config):
    """The card is read-only; a hand-rolled request must not redirect a key elsewhere."""
    with _client(cfg) as client:
        saved = client.put(
            "/api/providers/deepseek",
            json={"api_key": KEY, "base_url": "https://evil.example/v1", "model": "attacker-model"},
        )
        assert saved.status_code == 200
        body = saved.json()
        assert body["base_url"] == "https://api.deepseek.com"
        assert body["model"] == "deepseek-flash"


def test_activate_switches_the_resolver(cfg: Config):
    with _client(cfg) as client:
        assert client.app.state.resolver.llm_name == "stub"

        client.put("/api/providers/deepseek", json={"api_key": KEY})
        activated = client.post("/api/providers/deepseek/activate")
        assert activated.status_code == 200
        assert activated.json()["active"] is True

        settings = client.get("/api/settings").json()
        assert settings["llm"]["provider"] == "deepseek"
        assert settings["llm"]["model"] == "deepseek-flash"
        assert settings["llm"]["key_set"] is True
        assert client.app.state.resolver.llm_name == "deepseek"

        deleted = client.delete("/api/providers/deepseek/key")
        assert deleted.status_code == 200
        assert deleted.json()["configured"] is False and deleted.json()["key_set"] is False
        assert client.get("/api/settings").json()["llm"]["provider"] is None
        assert client.app.state.resolver.llm_name == "stub"

        again = client.post("/api/providers/deepseek/activate")
        assert again.status_code == 409
        assert again.json()["error"] == "provider_not_configured"


def test_unknown_provider_is_404(cfg: Config):
    with _client(cfg) as client:
        assert client.put("/api/providers/not_a_provider", json={"api_key": KEY}).status_code == 404
        assert client.post("/api/providers/not_a_provider/activate").status_code == 404


def test_test_endpoint_validates_without_saving(cfg: Config, monkeypatch):
    import prism.api.providers as providers_api

    calls: list[dict] = []

    def stub_probe(desc, *, key):
        calls.append({"provider": desc.name, "key": key})

    monkeypatch.setattr(providers_api, "probe", stub_probe)
    with _client(cfg) as client:
        ok = client.post("/api/providers/openai/test", json={"api_key": KEY})
        assert ok.status_code == 200
        assert ok.json()["ok"] is True
        assert KEY not in ok.text
        assert calls == [{"provider": "openai", "key": KEY}]

        assert client.get("/api/providers").json()[1]["key_set"] is False

        missing = client.post("/api/providers/openai/test", json={})
        assert missing.status_code == 400
        assert missing.json()["error"] == "missing_key"


def test_test_endpoint_reports_auth_failure_without_the_key(cfg: Config, monkeypatch):
    import prism.api.providers as providers_api

    class StubAuthError(Exception):
        status_code = 401

    def boom(desc, *, key):
        raise StubAuthError(f"bad key {key}")

    monkeypatch.setattr(providers_api, "probe", boom)
    with _client(cfg) as client:
        response = client.post("/api/providers/openai/test", json={"api_key": KEY})
        assert response.status_code == 200
        body = response.json()
        assert body["ok"] is False
        assert body["error"] == "auth_failed"
        assert KEY not in response.text
