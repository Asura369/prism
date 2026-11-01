from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, ClassVar, TYPE_CHECKING

from ..domain import Asset, ImageSequenceRecipe, SlideSpec

if TYPE_CHECKING:
    from ..domain import TrendCandidate, TrendScore


class BaseAdapter(ABC):
    name: ClassVar[str]

    def is_available(self) -> bool:
        return True


class LLMAdapter(BaseAdapter):
    @abstractmethod
    def complete(
        self,
        prompt: str,
        *,
        system: str | None = None,
        json_schema: dict[str, Any] | None = None,
        temperature: float = 0.7,
        max_tokens: int = 1500,
    ) -> str: ...


class CardRendererAdapter(BaseAdapter):
    @abstractmethod
    def render_slide(
        self,
        slide: SlideSpec,
        *,
        index: int,
        total: int,
        style: str,
        resolution: str,
        out_path: Path,
    ) -> Asset:
        """Render one slide as PNG. Deterministic for the given inputs."""

    @abstractmethod
    def available_styles(self) -> list[str]: ...


class ImageSequenceExportAdapter(BaseAdapter):
    @abstractmethod
    def export(self, slides: list[Path], out_path: Path) -> Path:
        """Zip the slide PNGs in order. No other logic."""


class TrendSourceAdapter(BaseAdapter):
    @abstractmethod
    def fetch(self, *, region: str, limit: int, window_h: int) -> list["TrendCandidate"]: ...


class NewsSourceAdapter(BaseAdapter):
    @abstractmethod
    def fetch_articles(self, *, query: str, max_articles: int, language: str = "en") -> list[dict[str, Any]]:
        """Return [{title, url, snippet, published_at, source_name}, ...]."""


class TrendScorerAdapter(BaseAdapter):
    @abstractmethod
    def score(self, candidates: list["TrendCandidate"]) -> list["TrendScore"]: ...
