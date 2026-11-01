from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from ...domain import ContentSpec, PolicyResult, SlideSpec
from ..base import CarouselPluginBase


class Fact(BaseModel):
    heading: str = Field(min_length=3, max_length=50)
    body: str = Field(min_length=10, max_length=260)


class FactsRaw(BaseModel):
    title: str = Field(min_length=3, max_length=120)
    cover_headline: str = Field(min_length=3, max_length=60)
    facts: list[Fact] = Field(min_length=3, max_length=5)
    cta: str = Field(min_length=3, max_length=80)


class FactsCarouselPlugin(CarouselPluginBase):
    name = "facts_carousel"
    version = "0.1.0"
    raw_model = FactsRaw

    def sample_payload(self) -> dict[str, Any]:
        return {
            "title": "Three things about the ocean",
            "cover_headline": "The Ocean Is Weirder Than You Think",
            "facts": [
                {"heading": "A short fact heading", "body": "Two or three plain sentences that explain the fact."},
            ],
            "cta": "Follow for one surprising fact every day.",
        }

    def build_slides(self, spec: ContentSpec) -> list[SlideSpec]:
        raw = spec.raw
        slides = [SlideSpec(kind="cover", heading=raw["cover_headline"], body=None)]
        for fact in raw["facts"]:
            slides.append(SlideSpec(kind="fact", heading=fact["heading"], body=fact["body"]))
        slides.append(SlideSpec(kind="cta", heading=raw["cta"], body=None))
        return slides

    def policy_check(self, spec: ContentSpec, assets: list, sources: list[dict]) -> PolicyResult:
        result = super().policy_check(spec, assets, sources)
        policy = self.policy_config
        reasons = list(result.reasons)
        if len(spec.slides) < policy.get("min_slides", 5):
            reasons.append(f"Expected at least {policy.get('min_slides', 5)} slides, got {len(spec.slides)}")
        if len(spec.slides) > policy.get("max_slides", 10):
            reasons.append(f"Expected at most {policy.get('max_slides', 10)} slides, got {len(spec.slides)}")
        bad = {s.kind for s in spec.slides} - {"cover", "fact", "cta"}
        if bad:
            reasons.append(f"Unexpected slide kinds: {sorted(bad)}")
        return PolicyResult(ok=not reasons, reasons=reasons, warnings=result.warnings)
