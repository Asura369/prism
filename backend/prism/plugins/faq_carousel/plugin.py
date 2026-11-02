from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from ...domain import ContentSpec, PolicyResult, SlideSpec
from ..base import CarouselPluginBase


class Qa(BaseModel):
    question: str = Field(min_length=3, max_length=90)
    answer: str = Field(min_length=10, max_length=260)


class FaqRaw(BaseModel):
    title: str = Field(min_length=3, max_length=120)
    cover_headline: str = Field(min_length=3, max_length=60)
    questions: list[Qa] = Field(min_length=5, max_length=5)
    cta: str = Field(min_length=3, max_length=80)


class FaqCarouselPlugin(CarouselPluginBase):
    name = "faq_carousel"
    version = "0.1.0"
    raw_model = FaqRaw

    def sample_payload(self) -> dict[str, Any]:
        return {
            "title": "Why the sky changes color",
            "cover_headline": "Why Is the Sky Blue?",
            "questions": [
                {
                    "question": "Why is the sky blue during the day?",
                    "answer": "Short wavelengths of sunlight scatter far more in the atmosphere than long ones.",
                },
            ],
            "cta": "Follow for one clear answer every day.",
        }

    def build_slides(self, spec: ContentSpec) -> list[SlideSpec]:
        raw = spec.raw
        slides = [SlideSpec(kind="cover", heading=raw["cover_headline"], body=None)]
        for item in raw["questions"]:
            slides.append(
                SlideSpec(
                    kind="qa",
                    heading=item["question"],
                    body=item["answer"],
                    meta={"question": item["question"]},
                )
            )
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
        bad = {s.kind for s in spec.slides} - {"cover", "qa", "cta"}
        if bad:
            reasons.append(f"Unexpected slide kinds: {sorted(bad)}")
        return PolicyResult(ok=not reasons, reasons=reasons, warnings=result.warnings)
