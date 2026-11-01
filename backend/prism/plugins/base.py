from __future__ import annotations

import json
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, ClassVar

from pydantic import BaseModel, ValidationError as PydanticValidationError

from ..config import Config
from ..domain import (
    Asset,
    AssetRequest,
    ContentSpec,
    ImageSequenceRecipe,
    Job,
    OutputKind,
    PolicyResult,
    SlideSpec,
)
from ..errors import SlideOverflowError, SlideRenderError, SpecValidationError

if TYPE_CHECKING:
    from ..adapters.resolver import AdapterResolver


@dataclass
class RenderContext:
    job: Job
    work_dir: Path
    resolver: "AdapterResolver"
    emit: Callable[[str, float, str], None]
    seed: int
    sources: list[dict]


def extract_json(text: str) -> Any:
    text = text.strip()
    fenced = re.search(r"```(?:json)?\s*(.*?)```", text, flags=re.DOTALL)
    if fenced:
        text = fenced.group(1).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if start >= 0 and end > start:
            try:
                return json.loads(text[start : end + 1])
            except json.JSONDecodeError:
                pass
    raise ValueError("Response did not contain valid JSON")


class CarouselPluginBase(ABC):
    name: ClassVar[str]
    version: ClassVar[str]
    output_kind: ClassVar[str] = "image_sequence"
    raw_model: ClassVar[type[BaseModel]]

    def __init__(self, cfg: Config, assets_dir: Path | None = None):
        self.cfg = cfg
        self.assets_dir = assets_dir or Path.cwd()

    @property
    def manifest_defaults(self) -> dict[str, Any]:
        return getattr(self, "_manifest", {}).get("defaults", {})

    @property
    def policy_config(self) -> dict[str, Any]:
        return getattr(self, "_manifest", {}).get("policy", {})

    def attach_manifest(self, manifest: dict[str, Any]) -> None:
        self._manifest = manifest

    def spec_schema(self) -> dict:
        return self.raw_model.model_json_schema()

    def spec_prompt(self, topic: str, angle: dict | None) -> str:
        schema = json.dumps(self.spec_schema(), indent=2)
        angle_text = json.dumps(angle, indent=2) if angle else "none — choose a strong angle yourself"
        sample = json.dumps(self.sample_payload(), indent=2)
        return (
            f"Write a {self.name.replace('_', ' ')} for an educational Instagram carousel channel.\n"
            f"Topic: {topic}\n"
            f"Angle: {angle_text}\n\n"
            "Hard rules: every field must respect its maxLength. Body copy must be 260 characters or fewer, "
            "plain language, no emoji, no hashtags, no source URLs in slide text.\n\n"
            "Return JSON only, matching this schema:\n"
            f"{schema}\n\n"
            "Example shape (content is illustrative, not a template):\n"
            f"{sample}\n"
        )

    def sample_payload(self) -> dict[str, Any]:
        return {"title": "Sample title", "cover_headline": "A sample cover headline", "cta": "Follow for more."}

    def parse_spec(self, llm_output: str) -> ContentSpec:
        try:
            payload = extract_json(llm_output)
        except ValueError as exc:
            raise SpecValidationError(str(exc), payload=llm_output) from exc
        try:
            model = self.raw_model.model_validate(payload)
        except PydanticValidationError as exc:
            raise SpecValidationError(str(exc), payload=payload) from exc
        kwargs: dict[str, Any] = {
            "raw": model.model_dump(),
            "slides": [],
            "aspect_ratio": self.manifest_defaults.get("aspect_ratio", "4:5"),
            "resolution": self.manifest_defaults.get("resolution", "1080x1350"),
            "style": self.manifest_defaults.get("style", "cream"),
            "title": getattr(model, "title", ""),
            "caption": "",
            "hashtags": [],
            "output_kind": OutputKind.IMAGE_SEQUENCE,
            "sources": [],
        }
        spec = ContentSpec(**kwargs)
        spec.slides = self.build_slides(spec)
        return spec

    @abstractmethod
    def build_slides(self, spec: ContentSpec) -> list[SlideSpec]: ...

    def required_assets(self, spec: ContentSpec) -> list[AssetRequest]:
        assets = getattr(self, "_manifest", {}).get("assets", [])
        return [
            AssetRequest(kind=item["kind"], adapter_hint=item.get("adapter"), params=item.get("params", {}))
            for item in assets
        ]

    def build_assets(self, spec: ContentSpec, ctx: RenderContext) -> list[Asset]:
        cards_chain = ctx.resolver.require("cards")
        total = len(spec.slides)
        out_dir = ctx.work_dir / "slides"
        out_dir.mkdir(parents=True, exist_ok=True)
        assets: list[Asset] = []
        for index, slide in enumerate(spec.slides, start=1):
            last_error: Exception | None = None
            rendered: Asset | None = None
            for card in cards_chain:
                for attempt in range(1, self.cfg.run.max_retries + 1):
                    ctx.emit("render", (index - 1) / total, f"Rendering slide {index}/{total} (attempt {attempt})")
                    try:
                        rendered = card.render_slide(  # type: ignore[union-attr]
                            slide,
                            index=index,
                            total=total,
                            style=spec.style,
                            resolution=spec.resolution,
                            out_path=out_dir / f"{index:02d}.png",
                        )
                        break
                    except SlideOverflowError:
                        raise
                    except Exception as exc:  # noqa: BLE001 - adapter boundary
                        last_error = exc
                if rendered:
                    break
            if rendered is None:
                raise SlideRenderError(index, str(last_error) if last_error else "no card renderer available")
            assets.append(rendered)
            ctx.emit("render", index / total, f"Rendered slide {index}/{total}")
        return assets

    def build_recipe(self, spec: ContentSpec, assets: list[Asset]) -> ImageSequenceRecipe:
        slide_paths = [a.path for a in sorted(assets, key=lambda a: a.meta.get("index", 0))]
        return ImageSequenceRecipe(
            slides=slide_paths,
            style=spec.style,
            resolution=spec.resolution,
            out_zip_name="carousel.zip",
        )

    def metadata_prompt(self, spec: ContentSpec, assets: list[Asset]) -> str:
        slide_lines = "\n".join(
            f"{i}. {slide.heading}" for i, slide in enumerate(spec.slides, start=1)
        )
        return (
            f"Write Instagram metadata for this {self.name.replace('_', ' ')} titled {spec.title!r}.\n"
            f"Slides:\n{slide_lines}\n\n"
            "Return JSON only: {\"caption\": string (<= 2200 chars), "
            "\"hashtags\": [10-20 strings without the # symbol], "
            f"\"alt_text\": [one accessible description per slide, {len(spec.slides)} items]}}.\n"
            "Caption should be plain, useful, and end with a short call to action. "
            "Do not invent claims that are not in the slide text."
        )

    def policy_check(self, spec: ContentSpec, assets: list[Asset], sources: list[dict]) -> PolicyResult:
        reasons: list[str] = []
        if not spec.slides:
            reasons.append("Deck has no slides")
        if self.cfg.policy.ai_disclosure == "required" and not spec.raw.get("ai_disclosure", True):
            reasons.append("AI disclosure is required")
        return PolicyResult(ok=not reasons, reasons=reasons)
