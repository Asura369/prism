from __future__ import annotations

import os
from functools import lru_cache
from typing import Any
from pathlib import Path

import yaml
from dotenv import dotenv_values
from pydantic import BaseModel, ConfigDict, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from .errors import ConfigError


class _Model(BaseModel):
    model_config = ConfigDict(extra="allow")


class RunConfig(_Model):
    output_dir: str = "./review"
    work_dir: str = "./work"
    db_path: str = "./data/prism.db"
    keep_intermediates: bool = False
    max_retries: int = 3
    retry_backoff_s: list[float] = Field(default_factory=lambda: [1, 4, 16])
    worker_heartbeat_stale_s: int = 15


class OpenAICompatConfig(_Model):
    base_url: str = "https://api.openai.com/v1"
    model: str = "gpt-4o-mini"
    timeout_s: int = 60
    extra_body: dict[str, Any] = Field(default_factory=dict)


class LLMConfig(_Model):
    default: str = "openai_compat"
    openai_compat: OpenAICompatConfig = Field(default_factory=OpenAICompatConfig)
    fallback: list[str] = Field(default_factory=lambda: ["fake"])


class TemplatedConfig(_Model):
    style: str = "cream"


class CardsConfig(_Model):
    default: str = "templated"
    templated: TemplatedConfig = Field(default_factory=TemplatedConfig)
    fallback: list[str] = Field(default_factory=list)


class ExportConfig(_Model):
    default: str = "zip"


class AdaptersConfig(_Model):
    llm: LLMConfig = Field(default_factory=LLMConfig)
    cards: CardsConfig = Field(default_factory=CardsConfig)
    export: ExportConfig = Field(default_factory=ExportConfig)


class AssetsConfig(_Model):
    fonts_dir: str = "./assets/fonts"
    styles_dir: str = "./assets/styles"


class SourceConfig(_Model):
    enabled: bool = True
    subs: list[str] = Field(default_factory=list)


class DiscoverySourcesConfig(_Model):
    google_news_rss: SourceConfig = Field(default_factory=SourceConfig)
    hackernews: SourceConfig = Field(default_factory=SourceConfig)
    reddit: SourceConfig = Field(default_factory=lambda: SourceConfig(subs=["todayilearned", "interestingasfuck", "Damnthatsinteresting"]))
    google_trends_csv: SourceConfig = Field(default_factory=SourceConfig)
    manual: SourceConfig = Field(default_factory=SourceConfig)


class ClusteringConfig(_Model):
    method: str = "difflib"
    threshold: float = 0.80


class ScoringWeights(_Model):
    safety: float = 0.30
    angle_ability: float = 0.25
    visual_potential: float = 0.20
    heuristic: float = 0.15
    saturation: float = -0.10


class HardFilter(_Model):
    safety_min: float = 0.40


class ScoringConfig(_Model):
    weights: ScoringWeights = Field(default_factory=ScoringWeights)
    hard_filter: HardFilter = Field(default_factory=HardFilter)
    source_reliability: dict[str, float] = Field(
        default_factory=lambda: {
            "google_news_rss": 1.0,
            "hackernews": 0.9,
            "reddit": 0.8,
            "google_trends_csv": 1.0,
            "manual": 0.7,
        }
    )


class AnglesConfig(_Model):
    count: int = 3
    route_plugin_via_llm: bool = True


class DiscoveryConfig(_Model):
    sources: DiscoverySourcesConfig = Field(default_factory=DiscoverySourcesConfig)
    clustering: ClusteringConfig = Field(default_factory=ClusteringConfig)
    cache_ttl_min: int = 15
    fetch_timeout_s: int = 10
    max_candidates_per_source: int = 40
    top_n_to_ui: int = 12
    scoring: ScoringConfig = Field(default_factory=ScoringConfig)
    angles: AnglesConfig = Field(default_factory=AnglesConfig)


class ValidationConfig(_Model):
    min_slide_count: int = 5
    max_slide_count: int = 12
    min_file_size_mb: float = 0.05
    min_body_font_px: int = 36
    caption_max_chars: int = 2200
    hashtags_max: int = 30


class NewsPolicyConfig(_Model):
    require_attribution: bool = True
    min_sources: int = 2
    attribution: dict[str, bool] = Field(default_factory=lambda: {"caption": True, "sources_slide": True})
    block_topics: list[str] = Field(default_factory=lambda: ["politics", "tragedy", "medical_claims", "active_conflict"])


class PolicyConfig(_Model):
    ai_disclosure: str = "required"
    news_carousel: NewsPolicyConfig = Field(default_factory=NewsPolicyConfig)


class Config(_Model):
    base_dir: Path = Field(default_factory=Path.cwd, exclude=True)
    run: RunConfig = Field(default_factory=RunConfig)
    adapters: AdaptersConfig = Field(default_factory=AdaptersConfig)
    assets: AssetsConfig = Field(default_factory=AssetsConfig)
    discovery: DiscoveryConfig = Field(default_factory=DiscoveryConfig)
    validation: ValidationConfig = Field(default_factory=ValidationConfig)
    policy: PolicyConfig = Field(default_factory=PolicyConfig)


class Secrets(BaseSettings):
    model_config = SettingsConfigDict(env_file=(".env", "../.env"), extra="ignore", populate_by_name=True)

    llm_key: str = Field("", validation_alias="LLM_KEY")
    fake_adapters: bool = Field(False, validation_alias="FAKE_ADAPTERS")
    prism_config: str = Field("", validation_alias="PRISM_CONFIG")
    prism_db_path: str = Field("", validation_alias="PRISM_DB_PATH")


def _config_path(explicit: Path | None = None, env_config: str | None = None) -> Path | None:
    candidates: list[Path] = []
    if explicit:
        candidates.append(explicit)
    if env_config:
        candidates.append(Path(env_config))
    candidates.extend([Path("./config.yaml"), Path("../config.yaml")])
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def _dotenv_values(enabled: bool) -> dict[str, str]:
    if not enabled:
        return {}
    values: dict[str, str] = {}
    for candidate in (Path(".env"), Path("../.env")):
        if candidate.exists():
            values.update({key: value for key, value in dotenv_values(candidate).items() if value is not None})
    return values


def load_config(path: Path | None = None, *, env_file: bool = True) -> Config:
    env = {**_dotenv_values(env_file), **os.environ}
    cfg_path = _config_path(path, env.get("PRISM_CONFIG"))
    data: dict = {}
    if cfg_path:
        try:
            data = yaml.safe_load(cfg_path.read_text()) or {}
        except yaml.YAMLError as exc:
            raise ConfigError(f"Invalid YAML in {cfg_path}: {exc}") from exc
    cfg = Config.model_validate(data)
    cfg.base_dir = cfg_path.resolve().parent if cfg_path else Path.cwd()
    if env.get("PRISM_DB_PATH"):
        cfg.run.db_path = env["PRISM_DB_PATH"]
    return cfg


@lru_cache
def get_config() -> Config:
    return load_config()


@lru_cache
def get_secrets() -> Secrets:
    return Secrets()


def resolve_path(path: str | Path, base: Path | None = None) -> Path:
    p = Path(path)
    if p.is_absolute():
        return p
    return ((base or Path.cwd()) / p).resolve()
