from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

from pydantic import BaseModel, Field

from ...domain import ContentSpec, PolicyResult, SlideSpec
from ..base import CarouselPluginBase

SOURCES_HEADING = "Sources"
SOURCES_PLACEHOLDER = "Sources are attached after ingest."
BODY_MAX = 260
NAME_MAX = 28


class NewsPoint(BaseModel):
    heading: str = Field(min_length=3, max_length=50)
    body: str = Field(min_length=10, max_length=260)
    source_index: int = Field(default=0, ge=0)


class NewsRaw(BaseModel):
    title: str = Field(min_length=3, max_length=120)
    cover_headline: str = Field(min_length=3, max_length=60)
    news_points: list[NewsPoint] = Field(min_length=3, max_length=5)
    cta: str = Field(min_length=3, max_length=80)


def sources_body(sources: list[dict]) -> str:
    lines = [
        f"{i}. {source['name'][:NAME_MAX]} — {urlparse(source['url']).netloc.removeprefix('www.')}"
        for i, source in enumerate(sources, start=1)
    ]
    while len(lines) > 1 and len("\n".join(lines)) > BODY_MAX:
        lines.pop()
    return "\n".join(lines)[:BODY_MAX]


class NewsCarouselPlugin(CarouselPluginBase):
    name = "news_carousel"
    version = "0.1.0"
    raw_model = NewsRaw

    def sample_payload(self) -> dict[str, Any]:
        return {
            "title": "Deep-sea mining talks resume",
            "cover_headline": "The Ocean Floor Is Back on the Agenda",
            "news_points": [
                {
                    "heading": "Talks restart this week",
                    "body": "Delegates are meeting again to discuss rules for extracting metals from the deep seabed.",
                    "source_index": 0,
                },
            ],
            "cta": "Follow for calmer recaps of complicated stories.",
        }

    def build_slides(self, spec: ContentSpec) -> list[SlideSpec]:
        raw = spec.raw
        sources = spec.sources
        slides = [SlideSpec(kind="cover", heading=raw["cover_headline"], body=None)]
        for point in raw["news_points"]:
            index = point["source_index"]
            if sources:
                index = min(index, len(sources) - 1)
            slides.append(
                SlideSpec(
                    kind="news_point",
                    heading=point["heading"],
                    body=point["body"],
                    meta={"source_index": index},
                )
            )
        slides.append(
            SlideSpec(
                kind="sources",
                heading=SOURCES_HEADING,
                body=sources_body(sources) if sources else SOURCES_PLACEHOLDER,
                meta={"sources": sources},
            )
        )
        slides.append(SlideSpec(kind="cta", heading=raw["cta"], body=None))
        return slides

    def metadata_prompt(self, spec: ContentSpec, assets: list) -> str:
        base = super().metadata_prompt(spec, assets)
        if not spec.sources:
            return base
        names = ", ".join(source["name"] for source in spec.sources)
        lines = "\n".join(f"{source['name']} — {source['url']}" for source in spec.sources)
        return f"{base}\nName every source in the caption: {names}.\n{lines}"

    def finalize_caption(self, caption: str, spec: ContentSpec) -> str:
        if not spec.sources:
            return caption
        lowered = caption.lower()
        missing = [source["name"] for source in spec.sources if source["name"].lower() not in lowered]
        if not missing:
            return caption
        suffix = " Sources: " + ", ".join(missing) + "."
        max_chars = self.cfg.validation.caption_max_chars
        return caption[: max_chars - len(suffix)].rstrip() + suffix

    def policy_check(self, spec: ContentSpec, assets: list, sources: list[dict]) -> PolicyResult:
        result = super().policy_check(spec, assets, sources)
        policy = self.policy_config
        reasons = list(result.reasons)

        min_sources = policy.get("min_sources", 2)
        if len(spec.sources) < min_sources:
            reasons.append(f"Needs at least {min_sources} sources, got {len(spec.sources)}")

        sources_slides = [slide for slide in spec.slides if slide.kind == "sources"]
        if len(sources_slides) != 1:
            reasons.append(f"Deck must contain exactly one sources slide, got {len(sources_slides)}")

        unexpected = {slide.kind for slide in spec.slides} - {"cover", "news_point", "sources", "cta"}
        if unexpected:
            reasons.append(f"Unexpected slide kinds: {sorted(unexpected)}")

        for slide in spec.slides:
            index = slide.meta.get("source_index")
            if index is not None and not (isinstance(index, int) and 0 <= index < len(spec.sources)):
                reasons.append(f"Slide source_index {index!r} is outside the fetched sources")
                break

        caption = spec.caption.lower()
        missing = [source["name"] for source in spec.sources if source["name"].lower() not in caption]
        if missing:
            reasons.append(f"Caption is missing source attribution: {', '.join(missing)}")

        haystack = f"{spec.title}\n{spec.caption}".lower()
        blocked = [topic for topic in policy.get("block_topics", []) if topic.lower() in haystack]
        if blocked:
            reasons.append(f"Blocked topics present: {', '.join(blocked)}")

        if any(slide.body and len(slide.body) > BODY_MAX for slide in sources_slides):
            reasons.append(f"Sources slide body exceeds {BODY_MAX} characters")

        min_slides = policy.get("min_slides", 6)
        max_slides = policy.get("max_slides", 10)
        if len(spec.slides) < min_slides:
            reasons.append(f"Expected at least {min_slides} slides, got {len(spec.slides)}")
        if len(spec.slides) > max_slides:
            reasons.append(f"Expected at most {max_slides} slides, got {len(spec.slides)}")

        return PolicyResult(ok=not reasons, reasons=reasons, warnings=result.warnings)
