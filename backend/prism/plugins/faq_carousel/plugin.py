from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from ...domain import ContentSpec, SlideSpec
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
    slide_kinds = frozenset({"cover", "qa", "cta"})

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
