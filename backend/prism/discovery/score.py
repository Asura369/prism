from __future__ import annotations

import logging
from datetime import datetime, timezone

from ..adapters.base import TrendScorerAdapter
from ..adapters.resolver import AdapterResolver
from ..config import Config
from ..domain import ScoredCandidate, TrendCandidate, TrendScore
from ..plugins.base import extract_json
from .llm import call_llm

log = logging.getLogger(__name__)

SCORE_SCHEMA = {
    "type": "object",
    "properties": {
        "scores": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "safety": {"type": "number"},
                    "visual_potential": {"type": "number"},
                    "angle_ability": {"type": "number"},
                    "saturation": {"type": "number"},
                    "reasoning": {"type": "string"},
                },
                "required": ["id", "safety", "visual_potential", "angle_ability", "saturation", "reasoning"],
            },
        }
    },
    "required": ["scores"],
}


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


def _engagement(candidate: TrendCandidate) -> float:
    metrics = candidate.metrics
    if candidate.source == "hackernews":
        return _clamp(max(float(metrics.get("points", 0)) / 500, float(metrics.get("descendants", 0)) / 200))
    if candidate.source == "reddit":
        return _clamp(max(float(metrics.get("upvotes", 0)) / 1000, float(metrics.get("comment_velocity", 0)) / 20))
    if candidate.source == "google_trends_csv":
        return _clamp(float(metrics.get("score", 0.5)))
    if candidate.source == "manual":
        return 1.0
    return 0.5


def heuristic_score(candidate: TrendCandidate, cfg: Config) -> float:
    recency_h = float(candidate.metrics.get("recency_h", 24.0))
    recency_score = max(0.0, 1.0 - recency_h / 48)
    heuristic = 0.6 * _engagement(candidate) + 0.4 * recency_score
    reliability = cfg.discovery.scoring.source_reliability.get(candidate.source, 0.7)
    return _clamp(heuristic * reliability)


def combine(candidate: TrendCandidate, *, safety: float, visual: float, angle: float, saturation: float, cfg: Config) -> float:
    weights = cfg.discovery.scoring.weights
    heuristic = heuristic_score(candidate, cfg)
    positive = max(0.0001, sum(w for w in (weights.safety, weights.angle_ability, weights.visual_potential, weights.heuristic) if w > 0))
    raw = (
        weights.safety * safety
        + weights.angle_ability * angle
        + weights.visual_potential * visual
        + weights.heuristic * heuristic
        + weights.saturation * saturation
    )
    return _clamp(raw / positive)


class HeuristicOnlyScorer(TrendScorerAdapter):
    name = "heuristic_only"

    def __init__(self, cfg: Config):
        self.cfg = cfg

    def score(self, candidates: list[TrendCandidate]) -> list[TrendScore]:
        out: list[TrendScore] = []
        for candidate in candidates:
            heuristic = heuristic_score(candidate, self.cfg)
            out.append(
                TrendScore(
                    heuristic=heuristic,
                    safety=0.6,
                    visual_potential=0.5,
                    angle_ability=0.5,
                    saturation=0.5,
                    combined=combine(
                        candidate,
                        safety=0.6,
                        visual=0.5,
                        angle=0.5,
                        saturation=0.5,
                        cfg=self.cfg,
                    ),
                    reasoning="heuristic-only mode",
                )
            )
        return out


class HeuristicLLMScorer(TrendScorerAdapter):
    name = "heuristic_llm"

    def __init__(self, cfg: Config, resolver: AdapterResolver):
        self.cfg = cfg
        self.resolver = resolver

    def _prompt(self, candidates: list[TrendCandidate]) -> str:
        today = datetime.now(timezone.utc).date().isoformat()
        lines = "\n".join(
            f"{index}. candidate_id={candidate.id}\n"
            f"   title: {candidate.title}\n"
            f"   source: {candidate.source}\n"
            f"   snippet: {candidate.snippet[:300]}"
            for index, candidate in enumerate(candidates, start=1)
        )
        return (
            "You are scoring topic candidates for an educational Instagram carousel channel.\n\n"
            f"Today is {today}. Channel focuses on facts, trivia, explainers, and timely-but-safe recaps.\n\n"
            "For each candidate, score 0.0–1.0 on:\n"
            "- safety:       safe for a general audience; no politics, tragedy, medical claims,\n"
            "                active conflict, or potentially defamatory content\n"
            "- visual_potential: how well this works as a text-first carousel (clear concepts,\n"
            "                easy to distill into short headings and 2–3 sentence bodies)\n"
            "- angle_ability:    how easily can you produce 3 distinct, engaging angles\n"
            "- saturation:       how likely is this already flooded on Instagram\n"
            "- reasoning:        one sentence justifying the combined assessment\n\n"
            f"Candidates:\n{lines}\n\n"
            'Return JSON: {"scores": [{"id": "<candidate id>", "safety": float, '
            '"visual_potential": float, "angle_ability": float, "saturation": float, "reasoning": str}, ...]}'
        )

    def score(self, candidates: list[TrendCandidate]) -> list[TrendScore]:
        by_id: dict[str, dict] = {}
        for start in range(0, len(candidates), 20):
            batch = candidates[start : start + 20]
            output = call_llm(self.cfg, self.resolver, self._prompt(batch), json_schema=SCORE_SCHEMA)
            payload = extract_json(output)
            for item in payload.get("scores", []):
                if isinstance(item, dict) and item.get("id"):
                    by_id[str(item["id"])] = item

        out: list[TrendScore] = []
        for candidate in candidates:
            item = by_id.get(candidate.id)
            if not item:
                heuristic = heuristic_score(candidate, self.cfg)
                out.append(
                    TrendScore(
                        heuristic=heuristic,
                        safety=0.6,
                        visual_potential=0.5,
                        angle_ability=0.5,
                        saturation=0.5,
                        combined=combine(candidate, safety=0.6, visual=0.5, angle=0.5, saturation=0.5, cfg=self.cfg),
                        reasoning="heuristic-only mode",
                    )
                )
                continue
            safety = _clamp(float(item.get("safety", 0.5)))
            visual = _clamp(float(item.get("visual_potential", 0.5)))
            angle = _clamp(float(item.get("angle_ability", 0.5)))
            saturation = _clamp(float(item.get("saturation", 0.5)))
            out.append(
                TrendScore(
                    heuristic=heuristic_score(candidate, self.cfg),
                    safety=safety,
                    visual_potential=visual,
                    angle_ability=angle,
                    saturation=saturation,
                    combined=combine(
                        candidate,
                        safety=safety,
                        visual=visual,
                        angle=angle,
                        saturation=saturation,
                        cfg=self.cfg,
                    ),
                    reasoning=str(item.get("reasoning", "")),
                )
            )
        return out


def score_candidates(cfg: Config, resolver: AdapterResolver, candidates: list[TrendCandidate]) -> list[ScoredCandidate]:
    if not candidates:
        return []
    scores: list[TrendScore]
    if resolver.resolve("llm"):
        try:
            scores = HeuristicLLMScorer(cfg, resolver).score(candidates)
        except Exception as exc:  # noqa: BLE001 - fallback scorer
            log.warning("LLM scoring failed; using heuristic-only scorer: %s", exc)
            scores = HeuristicOnlyScorer(cfg).score(candidates)
    else:
        scores = HeuristicOnlyScorer(cfg).score(candidates)

    passed = [
        ScoredCandidate(candidate, score)
        for candidate, score in zip(candidates, scores)
        if score.safety >= cfg.discovery.scoring.hard_filter.safety_min
    ]
    return sorted(passed, key=lambda item: item.score.combined, reverse=True)
