from __future__ import annotations

import hashlib
from pathlib import Path

from ...config import Config, resolve_path
from ...domain import Asset, SlideSpec
from ...render.slides import StylePreset, load_style, render_slide
from ..base import CardRendererAdapter


def _parse_resolution(resolution: str) -> tuple[int, int]:
    width, height = resolution.lower().split("x")
    return int(width), int(height)


class TemplatedCardRenderer(CardRendererAdapter):
    name = "templated"

    def __init__(self, cfg: Config | None = None, styles_dir: Path | None = None, fonts_dir: Path | None = None):
        self.styles_dir = Path(styles_dir) if styles_dir else (resolve_path(cfg.assets.styles_dir, cfg.base_dir) if cfg else None)
        self.fonts_dir = Path(fonts_dir) if fonts_dir else (resolve_path(cfg.assets.fonts_dir, cfg.base_dir) if cfg else None)
        if not self.styles_dir or not self.styles_dir.exists():
            raise FileNotFoundError(f"Styles directory not found: {self.styles_dir}")
        if not self.fonts_dir or not self.fonts_dir.exists():
            raise FileNotFoundError(f"Fonts directory not found: {self.fonts_dir}")

    def available_styles(self) -> list[str]:
        return sorted(p.stem for p in self.styles_dir.glob("*.yaml"))

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
        preset: StylePreset = load_style(style, self.styles_dir)
        image = render_slide(
            slide,
            index,
            total,
            preset,
            _parse_resolution(resolution),
            fonts_dir=self.fonts_dir,
        )
        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        image.save(out_path, format="PNG", optimize=False)
        sha = hashlib.sha256(out_path.read_bytes()).hexdigest()
        return Asset(
            kind="slide",
            path=out_path,
            meta={"sha256": sha, "style": style, "index": index, "width": image.width, "height": image.height},
        )
