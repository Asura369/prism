from __future__ import annotations

from pathlib import Path

from prism.adapters.resolver import AdapterResolver
from prism.config import Config, load_config


def test_defaults_are_sane():
    cfg = Config()
    assert cfg.validation.min_file_size_mb == 0.05
    assert cfg.discovery.scoring.hard_filter.safety_min == 0.40


def test_explicit_config_path_sets_base_dir(tmp_path: Path):
    path = tmp_path / "config.yaml"
    path.write_text("run:\n  db_path: ./custom.db\n")
    cfg = load_config(path)
    assert cfg.run.db_path == "./custom.db"
    assert cfg.base_dir == tmp_path


def test_resolver_without_a_configured_provider_uses_stub(cfg: Config):
    from prism import db

    db.init_db(cfg.run.db_path)
    resolver = AdapterResolver(cfg, db_path=cfg.run.db_path)
    chain = resolver.resolve("llm")
    assert [a.name for a in chain] == ["stub"]
    completion = resolver.complete("hello")
    assert completion.adapter == "stub"
    assert completion.text
    assert completion.failures == []


def test_stub_only_setting_beats_a_configured_provider(cfg: Config):
    from prism import db
    from prism.providers.config import ACTIVE_KEY, STUB_ONLY_KEY, secret_name

    db.init_db(cfg.run.db_path)
    conn = db.connect(cfg.run.db_path)
    db.set_secret(conn, secret_name("deepseek"), "sk-db")
    db.set_setting(conn, ACTIVE_KEY, "deepseek")
    db.set_setting(conn, STUB_ONLY_KEY, "1")
    conn.close()

    resolver = AdapterResolver(cfg, db_path=cfg.run.db_path)
    assert [a.name for a in resolver.resolve("llm")] == ["stub"]
    assert resolver.stub_only() is True


def test_resolver_uses_the_provider_stored_in_the_db(cfg: Config):
    from prism import db
    from prism.providers.config import ACTIVE_KEY, secret_name

    db.init_db(cfg.run.db_path)
    conn = db.connect(cfg.run.db_path)
    db.set_secret(conn, secret_name("deepseek"), "sk-db")
    db.set_setting(conn, ACTIVE_KEY, "deepseek")
    conn.close()

    resolver = AdapterResolver(cfg, db_path=cfg.run.db_path)
    assert [a.name for a in resolver.resolve("llm")] == ["deepseek", "stub"]
    assert resolver.get("llm").model == "deepseek-flash"
    assert resolver.llm_name == "deepseek"
