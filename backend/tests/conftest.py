from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from prism.config import Config, Secrets, load_config
from prism.domain import SlideSpec
from prism.plugins.facts_carousel.plugin import FactsCarouselPlugin

REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def cfg(tmp_path: Path) -> Config:
    cfg = load_config(env_file=False)
    cfg.base_dir = REPO_ROOT
    cfg.run.work_dir = str(tmp_path / "work")
    cfg.run.output_dir = str(tmp_path / "review")
    cfg.run.db_path = str(tmp_path / "prism.db")
    cfg.adapters.llm.default = "fake"
    cfg.adapters.llm.fallback = []
    return cfg


@pytest.fixture
def secrets() -> Secrets:
    return Secrets(
        llm_key="",
        fake_adapters=False,
        prism_config="",
        prism_db_path="",
        _env_file=None,
    )


@pytest.fixture
def facts_plugin(cfg: Config) -> FactsCarouselPlugin:
    plugin = FactsCarouselPlugin(cfg)
    manifest = yaml.safe_load((REPO_ROOT / "backend/prism/plugins/facts_carousel/manifest.yaml").read_text())
    plugin.attach_manifest(manifest)
    return plugin


@pytest.fixture
def facts_payload() -> dict:
    from prism.adapters.llm.fake import FACTS_SETS

    return json.loads(json.dumps(FACTS_SETS[0]))


@pytest.fixture
def slides() -> list[SlideSpec]:
    return [
        SlideSpec("cover", "Three Hearts. Blue Blood. No Bones.", None),
        SlideSpec("fact", "Three hearts, one job each", "Two hearts pump blood to the gills, while the third feeds the rest of the body. When an octopus swims, that third heart stops beating."),
        SlideSpec("cta", "Follow for one surprising fact every day.", None),
    ]
