from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import yaml
from PIL import Image, ImageDraw, ImageFont

from ..domain import SlideSpec
from ..errors import ConfigError, SlideOverflowError
from .frames import solid_background, subtle_gradient

CANVAS = (1080, 1350)
MARGIN = 80
CONTENT_LEFT = MARGIN
CONTENT_RIGHT = CANVAS[0] - MARGIN  # 1000
CONTENT_WIDTH = CONTENT_RIGHT - CONTENT_LEFT  # 920
HEADING_TOP = 120
HEADING_BOTTOM = 580
BODY_TOP = 620
BODY_BOTTOM = 1180
FOOTER_TOP = 1200
SAFE_RECT = (MARGIN, MARGIN, CONTENT_RIGHT, 1270)
DEFAULT_HANDLE = "@prism"

HEADING_SIZES = {"cover": (84, 72, 64), "default": (56, 48, 40)}
BODY_SIZES = (40, 38, 36)
MAX_HEADING_LINES = 3
MAX_BODY_LINES = 6


@dataclass
class StylePreset:
    name: str
    bg_color: str
    bg_gradient: tuple[str, str] | None
    heading_color: str
    body_color: str
    accent_color: str
    footer_color: str
    font_family: str = "Inter"


def load_style(name: str, styles_dir: Path) -> StylePreset:
    path = Path(styles_dir) / f"{name}.yaml"
    if not path.exists():
        raise ConfigError(f"Style preset not found: {path}")
    data = yaml.safe_load(path.read_text()) or {}
    gradient = data.get("bg_gradient")
    return StylePreset(
        name=data.get("name", name),
        bg_color=data["bg_color"],
        bg_gradient=(gradient["top"], gradient["bottom"]) if gradient else None,
        heading_color=data["heading_color"],
        body_color=data["body_color"],
        accent_color=data["accent_color"],
        footer_color=data["footer_color"],
        font_family=data.get("font_family", "Inter"),
    )


_DEFAULT_FONTS_DIR = Path(__file__).resolve().parents[3] / "assets" / "fonts"


@lru_cache(maxsize=64)
def _font(fonts_dir: str, size: int, bold: bool) -> ImageFont.FreeTypeFont:
    name = "Inter-Bold.ttf" if bold else "Inter-Regular.ttf"
    path = Path(fonts_dir) / name
    if not path.exists():
        raise ConfigError(f"Missing font file: {path}")
    return ImageFont.truetype(str(path), size)


def _wrap(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
    lines: list[str] = []
    for paragraph in text.split("\n"):
        words = paragraph.split()
        if not words:
            lines.append("")
            continue
        current = words[0]
        for word in words[1:]:
            candidate = f"{current} {word}"
            if draw.textlength(candidate, font=font) <= max_width:
                current = candidate
            else:
                lines.append(current)
                current = word
        lines.append(current)
    return lines


def _fit(
    draw: ImageDraw.ImageDraw,
    text: str,
    *,
    fonts_dir: str,
    sizes: tuple[int, ...],
    bold: bool,
    max_lines: int,
    line_factor: float,
    zone_height: int,
) -> tuple[ImageFont.FreeTypeFont, list[str], int]:
    for size in sizes:
        font = _font(fonts_dir, size, bold)
        lines = _wrap(draw, text, font, CONTENT_WIDTH)
        line_height = round(size * line_factor)
        if len(lines) <= max_lines and len(lines) * line_height <= zone_height:
            return font, lines, line_height
    raise SlideOverflowError(0, "text")


def _bbox_inside(bbox: tuple[float, float, float, float]) -> bool:
    left, top, right, bottom = SAFE_RECT
    return bbox[0] >= left - 1 and bbox[1] >= top - 1 and bbox[2] <= right + 1 and bbox[3] <= bottom + 1


def _check_bbox(draw: ImageDraw.ImageDraw, xy: tuple[int, int], text: str, font: ImageFont.FreeTypeFont, spacing: int, field: str) -> None:
    bbox = draw.multiline_textbbox(xy, text, font=font, spacing=spacing)
    if not _bbox_inside(bbox):
        raise SlideOverflowError(0, field)


def render_slide(
    slide: SlideSpec,
    index: int,
    total: int,
    style: StylePreset,
    resolution: tuple[int, int] = CANVAS,
    *,
    fonts_dir: Path | None = None,
) -> Image.Image:
    """Render one slide deterministically. Raises SlideOverflowError when text cannot fit."""
    width, height = resolution
    if style.bg_gradient:
        img = subtle_gradient(width, height, *style.bg_gradient)
    else:
        img = solid_background(width, height, style.bg_color)
    draw = ImageDraw.Draw(img)
    fonts = str(fonts_dir or _DEFAULT_FONTS_DIR)

    try:
        heading_text = slide.heading.strip()
        if not heading_text:
            raise SlideOverflowError(index, "heading")

        heading_zone = HEADING_BOTTOM - HEADING_TOP
        heading_sizes = HEADING_SIZES["cover"] if slide.kind == "cover" else HEADING_SIZES["default"]
        heading_font, heading_lines, heading_line_h = _fit(
            draw,
            heading_text,
            fonts_dir=fonts,
            sizes=heading_sizes,
            bold=True,
            max_lines=MAX_HEADING_LINES,
            line_factor=1.1 if slide.kind == "cover" else 1.15,
            zone_height=heading_zone,
        )

        accent_y = HEADING_TOP
        heading_y = HEADING_TOP + 40
        heading_spacing = max(0, heading_line_h - int(heading_font.size * 0.78))
        heading_text_block = "\n".join(heading_lines)
        _check_bbox(draw, (CONTENT_LEFT, heading_y), heading_text_block, heading_font, heading_spacing, "heading")
        heading_bottom = draw.multiline_textbbox(
            (CONTENT_LEFT, heading_y), heading_text_block, font=heading_font, spacing=heading_spacing
        )[3]
        if heading_bottom > BODY_TOP - 20:
            raise SlideOverflowError(index, "heading")

        if slide.body:
            body_text = slide.body.strip()
            body_font, body_lines, body_line_h = _fit(
                draw,
                body_text,
                fonts_dir=fonts,
                sizes=BODY_SIZES,
                bold=False,
                max_lines=MAX_BODY_LINES,
                line_factor=1.4,
                zone_height=BODY_BOTTOM - BODY_TOP,
            )
            body_spacing = max(0, body_line_h - int(body_font.size * 0.8))
            body_block = "\n".join(body_lines)
            _check_bbox(draw, (CONTENT_LEFT, BODY_TOP), body_block, body_font, body_spacing, "body")

        footer_font = _font(fonts, 24, False)
        page_text = f"{index} / {total}"
        _check_bbox(draw, (CONTENT_LEFT, FOOTER_TOP), DEFAULT_HANDLE, footer_font, 0, "footer_handle")
        page_width = draw.textlength(page_text, font=footer_font)
        _check_bbox(draw, (int(CONTENT_RIGHT - page_width), FOOTER_TOP), page_text, footer_font, 0, "footer_page")

        draw.rectangle((CONTENT_LEFT, accent_y, CONTENT_LEFT + 64, accent_y + 6), fill=style.accent_color)
        draw.multiline_text(
            (CONTENT_LEFT, heading_y),
            heading_text_block,
            font=heading_font,
            fill=style.heading_color,
            spacing=heading_spacing,
        )
        if slide.body:
            draw.multiline_text(
                (CONTENT_LEFT, BODY_TOP),
                "\n".join(body_lines),
                font=body_font,
                fill=style.body_color,
                spacing=body_spacing,
            )
        draw.text((CONTENT_LEFT, FOOTER_TOP), DEFAULT_HANDLE, font=footer_font, fill=style.footer_color)
        draw.text((CONTENT_RIGHT - page_width, FOOTER_TOP), page_text, font=footer_font, fill=style.footer_color)
    except SlideOverflowError as exc:
        exc.slide_index = index
        raise

    return img
