from __future__ import annotations

import json
from pathlib import Path

import pytest

from prism.adapters.llm.stub import NEWS_SETS
from prism.domain import SlideSpec
from prism.render.slides import load_style, render_slide

STYLE_DIR = Path(__file__).resolve().parents[3] / "assets" / "styles"
FONTS_DIR = Path(__file__).resolve().parents[3] / "assets" / "fonts"

SOURCES = [
    {"name": "ScienceDaily", "url": "https://www.sciencedaily.com/a"},
    {"name": "Reuters", "url": "https://www.reuters.com/b"},
    {"name": "Nature", "url": "https://www.nature.com/c"},
]


def _payload(**overrides):
    payload = json.loads(json.dumps(NEWS_SETS[0]))
    payload.update(overrides)
    return payload


def _spec_with_sources(news_plugin, sources=SOURCES):
    spec = news_plugin.parse_spec(json.dumps(_payload()))
    spec.sources = sources
    spec.slides = news_plugin.build_slides(spec)
    return spec


@pytest.fixture
def news_spec(news_plugin):
    spec = _spec_with_sources(news_plugin)
    spec.caption = " ".join(source["name"] for source in SOURCES)
    return spec


def test_build_slides_order_kinds_and_meta(news_plugin):
    spec = _spec_with_sources(news_plugin)
    assert [s.kind for s in spec.slides] == [
        "cover",
        "news_point",
        "news_point",
        "news_point",
        "news_point",
        "news_point",
        "sources",
        "cta",
    ]
    assert spec.slides[1].meta["source_index"] == 0
    body = spec.slides[-2].body
    assert "ScienceDaily" in body and len(body) <= 260


def test_source_index_is_clamped_to_fetched_sources(news_plugin):
    spec = news_plugin.parse_spec(json.dumps(_payload()))
    spec.raw["news_points"][0]["source_index"] = 7
    spec.sources = SOURCES[:2]
    spec.slides = news_plugin.build_slides(spec)
    assert spec.slides[1].meta["source_index"] == 1


def test_build_slides_without_sources_is_safe(news_plugin):
    spec = news_plugin.parse_spec(json.dumps(_payload()))  # sources still empty
    assert spec.slides[-2].kind == "sources"


def _render_sources_slide(news_plugin, sources):
    spec = _spec_with_sources(news_plugin, sources)
    slide = next(s for s in spec.slides if s.kind == "sources")
    style = load_style("slate", STYLE_DIR)
    render_slide(slide, spec.slides.index(slide) + 1, len(spec.slides), style, (1080, 1350), fonts_dir=FONTS_DIR)


def test_sources_slide_renders_adversarial_sources(news_plugin):
    adversarial = [{"name": "N" * 28, "url": f"https://{'d' * 40}{i}.com"} for i in range(5)]
    _render_sources_slide(news_plugin, adversarial)


def test_sources_slide_renders_realistic_sources(news_plugin):
    _render_sources_slide(news_plugin, SOURCES)


def test_source_names_are_readable_not_chopped(news_plugin):
    sources = [
        {"name": "The New York Times", "url": "https://www.nytimes.com/a"},
        {"name": "Associated Press", "url": "https://apnews.com/b"},
    ]
    body = next(s.body for s in _spec_with_sources(news_plugin, sources).slides if s.kind == "sources")
    assert "The New York Times" in body
    assert "Associated Press" in body


def test_overlong_source_names_end_with_an_ellipsis(news_plugin):
    sources = [{"name": "The Wall Street Journal of Record and Opinion", "url": "https://www.wsj.com/x"}]
    body = next(s.body for s in _spec_with_sources(news_plugin, sources).slides if s.kind == "sources")
    assert body.endswith("…")


def test_five_long_sources_still_render(news_plugin):
    long_sources = [
        {"name": "The Wall Street Journal", "url": "https://www.wsj.com/a"},
        {"name": "The Washington Post", "url": "https://www.washingtonpost.com/b"},
        {"name": "Los Angeles Times", "url": "https://www.latimes.com/c"},
        {"name": "The New York Times", "url": "https://www.nytimes.com/d"},
        {"name": "Associated Press", "url": "https://apnews.com/e"},
    ]
    _render_sources_slide(news_plugin, long_sources)


def test_finalize_caption_appends_missing_sources(news_plugin):
    spec = _spec_with_sources(news_plugin)
    caption = news_plugin.finalize_caption("A recap with no attribution.", spec)
    assert all(s["name"] in caption for s in SOURCES)


def test_finalize_caption_respects_the_caption_limit(news_plugin):
    spec = _spec_with_sources(news_plugin)
    spec.caption = ""
    caption = news_plugin.finalize_caption("x" * 2200, spec)
    assert len(caption) <= news_plugin.cfg.validation.caption_max_chars
    assert all(s["name"] in caption for s in SOURCES)


def test_finalize_caption_without_sources_is_a_no_op(news_plugin):
    spec = news_plugin.parse_spec(json.dumps(_payload()))
    assert news_plugin.finalize_caption("A recap.", spec) == "A recap."


def test_metadata_prompt_names_sources(news_plugin, news_spec):
    prompt = news_plugin.metadata_prompt(news_spec, [])
    assert "Name every source in the caption" in prompt
    for source in SOURCES:
        assert source["name"] in prompt and source["url"] in prompt


def test_manifest_ingest_matches_policy(news_plugin):
    assert news_plugin.ingest_config["params"]["min_sources"] == news_plugin.policy_config["min_sources"]


def test_policy_rejects_too_few_sources(news_plugin, news_spec):
    news_spec.sources = SOURCES[:1]
    result = news_plugin.policy_check(news_spec, [], news_spec.sources)
    assert not result.ok and any("at least 2 sources" in r for r in result.reasons)


def test_policy_rejects_out_of_range_source_index(news_plugin, news_spec):
    news_spec.slides[1].meta["source_index"] = 9
    result = news_plugin.policy_check(news_spec, [], news_spec.sources)
    assert not result.ok and any("source_index" in r for r in result.reasons)


def test_policy_requires_caption_attribution(news_plugin, news_spec):
    news_spec.caption = "A recap with no attribution."
    result = news_plugin.policy_check(news_spec, [], news_spec.sources)
    assert not result.ok and any("source" in r.lower() for r in result.reasons)


def test_policy_blocks_topic(news_plugin, news_spec):
    news_spec.title = "Politics of the seabed"
    assert not news_plugin.policy_check(news_spec, [], news_spec.sources).ok


def test_policy_rejects_two_sources_slides(news_plugin, news_spec):
    news_spec.slides.append(SlideSpec(kind="sources", heading="Sources", body="x"))
    assert not news_plugin.policy_check(news_spec, [], news_spec.sources).ok


def test_policy_accepts_valid_deck(news_plugin, news_spec):
    news_spec.caption = "Sources: ScienceDaily, Reuters, Nature."
    assert news_plugin.policy_check(news_spec, [], news_spec.sources).ok
