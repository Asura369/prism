from __future__ import annotations

from pathlib import Path

from prism import db
from prism.config import Config
from prism.providers.config import ACTIVE_KEY, effective_llm, secret_name


def _db(cfg: Config) -> str:
    path = str(Path(cfg.run.db_path))
    db.init_db(path)
    return path


def test_no_provider_configured_means_no_llm(cfg: Config):
    assert effective_llm(_db(cfg)) is None


def test_active_provider_carries_descriptor_quirks(cfg: Config):
    path = _db(cfg)
    conn = db.connect(path)
    db.set_secret(conn, secret_name("opencode_go"), "sk-db")
    db.set_setting(conn, ACTIVE_KEY, "opencode_go")
    conn.close()

    effective = effective_llm(path)
    assert effective is not None
    assert effective.provider == "opencode_go"
    assert effective.api_key == "sk-db"
    assert effective.config.base_url == "https://opencode.ai/inference/go/openai/v1"
    assert effective.config.model == "deepseek-v4.1-flash"
    assert effective.config.json_mode is False
    assert effective.config.headers["x-opencode-session"]
    assert effective.config.extra_body == {"thinking": {"type": "disabled"}}


def test_deepseek_and_openai_presets_map_to_the_shared_adapter(cfg: Config):
    path = _db(cfg)
    conn = db.connect(path)
    db.set_secret(conn, secret_name("deepseek"), "sk-db")
    db.set_setting(conn, ACTIVE_KEY, "deepseek")

    deepseek = effective_llm(path)
    assert deepseek is not None
    assert deepseek.config.model == "deepseek-flash"
    assert deepseek.config.json_mode is True

    db.set_secret(conn, secret_name("openai"), "sk-db2")
    db.set_setting(conn, ACTIVE_KEY, "openai")
    conn.close()

    openai = effective_llm(path)
    assert openai is not None
    assert openai.config.max_tokens_param == "max_completion_tokens"
    assert openai.config.send_temperature is False


def test_active_provider_without_a_stored_key_is_not_usable(cfg: Config):
    path = _db(cfg)
    conn = db.connect(path)
    db.set_setting(conn, ACTIVE_KEY, "deepseek")
    conn.close()

    assert effective_llm(path) is None
