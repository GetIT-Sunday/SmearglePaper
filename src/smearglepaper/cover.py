from __future__ import annotations

from pathlib import Path

from .config import DATA_DIR
from .storage import ensure_parent, slugify


def create_cover(title: str, subtitle: str = "SmearglePaper") -> str:
    path = DATA_DIR / "covers" / f"{slugify(title)}.png"
    ensure_parent(path)
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        path.write_text(f"{title}\n{subtitle}\n", encoding="utf-8")
        return str(path)

    width, height = 900, 383
    image = Image.new("RGB", (width, height), "#f8fafc")
    draw = ImageDraw.Draw(image)
    for y in range(height):
        shade = int(248 - y * 24 / height)
        draw.line((0, y, width, y), fill=(shade, min(250, shade + 5), 252))
    draw.rectangle((0, height - 72, width, height), fill="#1d4ed8")
    font_title = _font(44)
    font_sub = _font(24)
    draw.text((54, 64), _wrap(title, 22), fill="#111827", font=font_title, spacing=8)
    draw.text((54, height - 54), subtitle, fill="#ffffff", font=font_sub)
    image.save(path)
    return str(path)


def _font(size: int):
    from PIL import ImageFont

    for name in ("Arial Unicode.ttf", "Arial.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _wrap(text: str, limit: int) -> str:
    words = text.split()
    if len(words) <= 1:
        return "\n".join(text[i : i + limit] for i in range(0, min(len(text), limit * 3), limit))
    lines: list[str] = []
    current = ""
    for word in words:
        if len(current) + len(word) + 1 > limit:
            lines.append(current)
            current = word
        else:
            current = f"{current} {word}".strip()
    if current:
        lines.append(current)
    return "\n".join(lines[:3])
