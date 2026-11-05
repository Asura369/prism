from __future__ import annotations

from functools import lru_cache
from typing import Any
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field

from .errors import ConfigError


class _Model(BaseModel):
    model_config = ConfigDict(extra="allow")


class RunConfig(_Model):
    output_dir: str = "./review"
    work_dir: str = "./work"
    db_path: str = "./data/prism.db"
    max_retries: int = 3
    retry_backoff_s: list[float] = Field(default_factory=lambda: [1, 4, 16])
    worker_heartbeat_stale_s: int = 15


class OpenAICompatConfig(_Model):
    """Request shape for the shared OpenAI-compatible adapter.

    Built from a provider descriptor plus the stored connection; no YAML of its own.
    """

    base_url: str = "https://api.openai.com/v1"
    model: str = "gpt-4o-mini"
    timeout_s: int = 60
    extra_body: dict[str, Any] = Field(default_factory=dict)
    headers: dict[str, str] = Field(default_factory=dict)  # e.g. gateway routing headers
    json_mode: bool = True  # false for gateways that reject response_format=json_object
    max_tokens_param: str = "max_tokens"  # reasoning models want max_completion_tokens
    send_temperature: bool = True  # reasoning models reject a non-default temperature


class CardsConfig(_Model):
    default: str = "templated"


class ExportConfig(_Model):
    default: str = "zip"


class AdaptersConfig(_Model):
    cards: CardsConfig = Field(default_factory=CardsConfig)
    export: ExportConfig = Field(default_factory=ExportConfig)


class AssetsConfig(_Model):
    fonts_dir: str = "./assets/fonts"
    styles_dir: str = "./assets/styles"


class SourceConfig(_Model):
    enabled: bool = True


class DiscoverySourcesConfig(_Model):
    google_news_rss: SourceConfig = Field(default_factory=SourceConfig)
    hackernews: SourceConfig = Field(default_factory=SourceConfig)


class ClusteringConfig(_Model):
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
    min_file_size_mb: float = 0.05
    caption_max_chars: int = 2200
    hashtags_max: int = 30


class PolicyConfig(_Model):
    ai_disclosure: str = "required"


class Config(_Model):
    base_dir: Path = Field(default_factory=Path.cwd, exclude=True)
    run: RunConfig = Field(default_factory=RunConfig)
    adapters: AdaptersConfig = Field(default_factory=AdaptersConfig)
    assets: AssetsConfig = Field(default_factory=AssetsConfig)
    discovery: DiscoveryConfig = Field(default_factory=DiscoveryConfig)
    validation: ValidationConfig = Field(default_factory=ValidationConfig)
    policy: PolicyConfig = Field(default_factory=PolicyConfig)


def _config_path(explicit: Path | None = None) -> Path | None:
    candidates: list[Path] = []
    if explicit:
        candidates.append(explicit)
    candidates.extend([Path("./config.yaml"), Path("../config.yaml")])
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def load_config(path: Path | None = None) -> Config:
    cfg_path = _config_path(path)
    data: dict = {}
    if cfg_path:
        try:
            data = yaml.safe_load(cfg_path.read_text()) or {}
        except yaml.YAMLError as exc:
            raise ConfigError(f"Invalid YAML in {cfg_path}: {exc}") from exc
    cfg = Config.model_validate(data)
    cfg.base_dir = cfg_path.resolve().parent if cfg_path else Path.cwd()
    return cfg


@lru_cache
def get_config() -> Config:
    return load_config()


def resolve_path(path: str | Path, base: Path | None = None) -> Path:
    p = Path(path)
    if p.is_absolute():
        return p
    return ((base or Path.cwd()) / p).resolve()
