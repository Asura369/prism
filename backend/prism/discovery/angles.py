from __future__ import annotations

import sqlite3
from dataclasses import asdict
from datetime import datetime, timezone

from ..adapters.resolver import AdapterResolver
from ..config import Config
from ..domain import Angle, ScoredCandidate, TrendCandidate
from ..errors import AngleGenerationError
from ..plugins.base import extract_json
from ..plugins.registry import PluginInfo, PluginRegistry
from .cache import store_angles
from .llm import call_llm

ANGLE_SCHEMA = {
    "type": "object",
    "properties": {
        "angles": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "hook": {"type": "string"},
                    "framing": {"type": "string"},
                    "target_emotion": {"type": "string"},
                    "format_suggestion": {"type": "string"},
                    "est_slide_count": {"type": "integer"},
                    "why_it_works": {"type": "string"},
                    "recommended_plugin": {"type": "string"},
                    "plugin_reasoning": {"type": "string"},
                },
                "required": [
                    "hook",
                    "framing",
                    "target_emotion",
                    "format_suggestion",
                    "est_slide_count",
                    "why_it_works",
                    "recommended_plugin",
                    "plugin_reasoning",
                ],
            },
        }
    },
    "required": ["angles"],
}


def default_plugin_for(
    candidate: TrendCandidate,
    plugins: list[PluginInfo],
    cfg: Config,
    *,
    format_suggestion: str = "",
) -> str:
    by_name = {plugin.name: plugin for plugin in plugins}

    news = by_name.get("news_carousel")
    if news:
        discovery = news.manifest.get("discovery", {})
        freshness = discovery.get("freshness_window_h")
        preferred = discovery.get("preferred_sources", [])
        age_h = (datetime.now(timezone.utc) - candidate.fetched_at).total_seconds() / 3600
        if candidate.source in preferred and (freshness is None or age_h <= float(freshness)):
            return "news_carousel"

    if format_suggestion == "qa" and "faq_carousel" in by_name:
        return "faq_carousel"
    if "facts_carousel" in by_name:
        return "facts_carousel"
    if plugins:
        return plugins[0].name
    raise AngleGenerationError("No installed plugin is available")


def _plugin_summaries(plugins: list[PluginInfo]) -> str:
    lines = []
    for plugin in plugins:
        policy = plugin.manifest.get("policy", {})
        defaults = plugin.manifest.get("defaults", {})
        lines.append(
            f"- {plugin.name}: {plugin.description}; slide_count={defaults.get('slide_count', '?')}; "
            f"resolution={defaults.get('resolution', '?')}; "
            f"requires_attribution={policy.get('require_attribution', False)}"
        )
    return "\n".join(lines) or "- none"


def _angles_prompt(candidate: TrendCandidate, plugins: list[PluginInfo], count: int) -> str:
    return (
        f"Topic: {candidate.title}\n"
        f"Context: {candidate.snippet}\n"
        f"Sources seen: {candidate.source}\n"
        "Plugin availability (choose only from this list):\n"
        f"{_plugin_summaries(plugins)}\n\n"
        f"Generate exactly {count} angles. Return JSON:\n"
        '{"angles": [{\n'
        '  "hook": "one-line hook a viewer sees first",\n'
        '  "framing": "short description of how the content is structured",\n'
        '  "target_emotion": "surprise | curiosity | awe | concern | delight | ...",\n'
        '  "format_suggestion": "facts | explainer | list | recap | qa",\n'
        '  "est_slide_count": int (5-10),\n'
        '  "why_it_works": "one sentence",\n'
        '  "recommended_plugin": "one of the plugin names above",\n'
        '  "plugin_reasoning": "one sentence justifying the plugin choice"\n'
        "}, ...]}"
    )


def _validate_angles(
    payload: dict,
    candidate: TrendCandidate,
    plugins: list[PluginInfo],
    cfg: Config,
) -> list[Angle]:
    raw_angles = payload.get("angles")
    expected = cfg.discovery.angles.count
    if not isinstance(raw_angles, list) or len(raw_angles) != expected:
        raise AngleGenerationError(f"Expected exactly {expected} angles")
    available = {plugin.name for plugin in plugins}
    angles: list[Angle] = []
    for raw in raw_angles:
        try:
            est_slides = int(raw["est_slide_count"])
        except (KeyError, TypeError, ValueError) as exc:
            raise AngleGenerationError("Invalid est_slide_count") from exc
        if not 5 <= est_slides <= 10:
            raise AngleGenerationError("est_slide_count must be between 5 and 10")
        format_suggestion = str(raw.get("format_suggestion", ""))
        recommended = str(raw.get("recommended_plugin", ""))
        reasoning = str(raw.get("plugin_reasoning", ""))
        if not cfg.discovery.angles.route_plugin_via_llm:
            recommended = default_plugin_for(candidate, plugins, cfg, format_suggestion=format_suggestion)
            reasoning = "auto-routed (LLM routing disabled)"
        elif recommended not in available:
            recommended = default_plugin_for(candidate, plugins, cfg, format_suggestion=format_suggestion)
            reasoning = "auto-routed (LLM recommendation invalid)"
        angles.append(
            Angle(
                hook=str(raw.get("hook", "")),
                framing=str(raw.get("framing", "")),
                target_emotion=str(raw.get("target_emotion", "")),
                format_suggestion=format_suggestion,
                est_slide_count=est_slides,
                why_it_works=str(raw.get("why_it_works", "")),
                recommended_plugin=recommended,
                plugin_reasoning=reasoning,
            )
        )
    return angles


def generate_angles(
    cfg: Config,
    resolver: AdapterResolver,
    registry: PluginRegistry,
    candidate: ScoredCandidate,
) -> list[Angle]:
    plugins = [info for info in registry.list_plugins() if info.available]
    if not plugins:
        raise AngleGenerationError("No installed plugin is available")
    prompt = _angles_prompt(candidate.candidate, plugins, cfg.discovery.angles.count)
    try:
        output = call_llm(cfg, resolver, prompt, json_schema=ANGLE_SCHEMA)
        angles = _validate_angles(extract_json(output), candidate.candidate, plugins, cfg)
    except Exception as exc:  # noqa: BLE001 - one re-prompt
        retry_prompt = (
            f"{prompt}\n\nYour previous response was invalid: {exc}\n"
            "Return exactly the requested JSON shape."
        )
        try:
            output = call_llm(cfg, resolver, retry_prompt, json_schema=ANGLE_SCHEMA)
            angles = _validate_angles(extract_json(output), candidate.candidate, plugins, cfg)
        except Exception as retry_exc:  # noqa: BLE001
            raise AngleGenerationError(str(retry_exc)) from retry_exc
    return angles


def store_generated_angles(
    cfg: Config,
    conn: sqlite3.Connection,
    candidate: ScoredCandidate,
    angles: list[Angle],
) -> None:
    store_angles(
        conn,
        candidate.candidate.id,
        {
            "candidate_id": candidate.candidate.id,
            "title": candidate.candidate.title,
            "angles": [asdict(angle) for angle in angles],
            "generated_at": datetime.now(timezone.utc).isoformat(),
        },
        cfg,
    )
