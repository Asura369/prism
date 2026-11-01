from __future__ import annotations

from PIL import Image, ImageColor, ImageDraw


def solid_background(width: int, height: int, color: str) -> Image.Image:
    return Image.new("RGB", (width, height), ImageColor.getrgb(color))


def subtle_gradient(width: int, height: int, top_color: str, bottom_color: str) -> Image.Image:
    """Vertical gradient, one row at a time. No numpy, deterministic."""
    top = ImageColor.getrgb(top_color)
    bottom = ImageColor.getrgb(bottom_color)
    img = Image.new("RGB", (width, height))
    draw = ImageDraw.Draw(img)
    for y in range(height):
        t = y / max(1, height - 1)
        color = tuple(round(a + (b - a) * t) for a, b in zip(top, bottom))
        draw.line([(0, y), (width, y)], fill=color)
    return img
