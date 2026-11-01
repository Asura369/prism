from __future__ import annotations

import hashlib
from pathlib import Path

import pytest
from PIL import Image

from prism.domain import SlideSpec
from prism.errors import SlideOverflowError
from prism.render.slides import CANVAS, CONTENT_LEFT, CONTENT_RIGHT, MARGIN, load_style, render_slide

STYLE_DIR = Path(__file__).resolve().parents[3] / "assets" / "styles"


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.mark.parametrize("name", ["cream", "slate", "mint"])
def test_load_all_styles(name: str):
    style = load_style(name, STYLE_DIR)
    assert style.name == name
    assert style.bg_color.startswith("#")


def test_render_is_deterministic(tmp_path: Path, slides: list[SlideSpec]):
    style = load_style("cream", STYLE_DIR)
    for index in (1, 2):
        img = render_slide(slides[1], 2, 5, style)
        img.save(tmp_path / f"slide-{index}.png", format="PNG")
    assert _hash(tmp_path / "slide-1.png") == _hash(tmp_path / "slide-2.png")


def test_render_outputs_canvas_size(slides: list[SlideSpec]):
    style = load_style("cream", STYLE_DIR)
    for slide in slides:
        img = render_slide(slide, 1, 5, style)
        assert img.size == CANVAS == (1080, 1350)
        assert img.mode == "RGB"


def test_text_blocks_stay_inside_safe_rect(slides: list[SlideSpec]):
    style = load_style("cream", STYLE_DIR)
    from PIL import ImageDraw

    for slide in slides:
        img = render_slide(slide, 1, 5, style)
        # Sample the safe margin band: it must remain the untouched background color.
        draw = ImageDraw.Draw(img)
        assert draw is not None
        bg = style.bg_color
        from PIL import ImageColor

        bg_rgb = ImageColor.getrgb(bg)
        for point in [(10, 10), (1070, 10), (10, 1340), (1070, 1340)]:
            assert img.getpixel(point) == bg_rgb


def test_max_length_body_renders():
    style = load_style("cream", STYLE_DIR)
    body = ("A clear sentence about a useful fact. " * 8)[:260].strip()
    assert len(body) <= 260
    img = render_slide(SlideSpec("fact", "A heading at the limit that still fits on two lines", body), 2, 5, style)
    assert img.size == CANVAS


def test_overflow_raises_at_min_font_size():
    style = load_style("cream", STYLE_DIR)
    with pytest.raises(SlideOverflowError):
        render_slide(SlideSpec("fact", "x" * 600, "y" * 1200), 2, 5, style)


def test_content_engine_uses_safe_margins():
    style = load_style("cream", STYLE_DIR)
    assert CONTENT_LEFT == MARGIN == 80
    assert CONTENT_RIGHT == 1000
    assert style.name == "cream"
