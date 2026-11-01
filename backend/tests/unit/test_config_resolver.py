from __future__ import annotations

from pathlib import Path

from prism.adapters.resolver import AdapterResolver
from prism.config import Config, Secrets, load_config


def test_defaults_are_sane():
    cfg = Config()
    assert cfg.validation.min_slide_count == 5
    assert cfg.discovery.scoring.hard_filter.safety_min == 0.40
    assert cfg.adapters.llm.default == "openai_compat"
    assert cfg.adapters.llm.openai_compat.base_url.startswith("https://")
    assert cfg.adapters.llm.openai_compat.extra_body == {}
    assert cfg.adapters.llm.fallback == ["fake"]


def test_env_db_path_overrides_config(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("PRISM_DB_PATH", str(tmp_path / "env.db"))
    cfg = load_config()
    assert cfg.run.db_path == str(tmp_path / "env.db")


def test_explicit_config_path_sets_base_dir(tmp_path: Path):
    path = tmp_path / "config.yaml"
    path.write_text("run:\n  db_path: ./custom.db\n")
    cfg = load_config(path)
    assert cfg.run.db_path == "./custom.db"
    assert cfg.base_dir == tmp_path


def test_resolver_no_key_falls_through_to_fake(cfg: Config):
    cfg.adapters.llm.default = "openai_compat"
    cfg.adapters.llm.fallback = ["fake"]
    secrets = Secrets(llm_key="", fake_adapters=False, prism_config="", prism_db_path="", _env_file=None)
    resolver = AdapterResolver(cfg, secrets)
    chain = resolver.resolve("llm")
    assert [a.name for a in chain] == ["fake"]
    chosen, used_fallback = resolver.use("llm")
    assert chosen.name == "fake"
    assert used_fallback is True
    assert "llm:fake" in resolver.fallbacks_used


def test_resolver_fake_adapters_flag_forces_fake(cfg: Config):
    cfg.adapters.llm.default = "openai_compat"
    secrets = Secrets(llm_key="sk-test", fake_adapters=True, prism_config="", prism_db_path="", _env_file=None)
    resolver = AdapterResolver(cfg, secrets)
    assert [a.name for a in resolver.resolve("llm")] == ["fake"]


def test_resolver_uses_llm_key(cfg: Config):
    cfg.adapters.llm.default = "openai_compat"
    cfg.adapters.llm.fallback = ["fake"]
    secrets = Secrets(
        llm_key="sk-test",
        fake_adapters=False,
        prism_config="",
        prism_db_path="",
        _env_file=None,
    )
    resolver = AdapterResolver(cfg, secrets)
    assert [a.name for a in resolver.resolve("llm")] == ["openai_compat", "fake"]
    assert resolver.get("llm").model == cfg.adapters.llm.openai_compat.model
