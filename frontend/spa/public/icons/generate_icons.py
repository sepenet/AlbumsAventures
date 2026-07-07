"""Generate the PWA icon set for AlbumsAventures.

Renders real PNG icons (no external asset dependency) from the project's
Tailwind brand palette (``docs/GUIDELINES_UI.md``): a sky -> blue diagonal
gradient background with a white "A" glyph. Produces the sizes required by the
web app manifest and iOS:

* ``icon-192.png``       (192x192, ``purpose: any``)
* ``icon-512.png``       (512x512, ``purpose: any``)
* ``icon-maskable-512.png`` (512x512, ``purpose: maskable`` — glyph kept inside
  the ~80% safe zone so Android adaptive masks never clip it)
* ``apple-touch-icon.png`` (180x180, iOS home-screen icon, opaque background)

Run once from the SPA root to (re)generate the icons committed under
``public/icons/``::

    ../../Scripts/python.exe public/icons/generate_icons.py

These are brand-derived placeholders; swap in a designed asset later without
touching the manifest (filenames are stable).
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

# Tailwind brand palette (docs/GUIDELINES_UI.md): sky-500 -> blue-600.
SKY_500 = (14, 165, 233)
BLUE_600 = (37, 99, 235)
WHITE = (255, 255, 255)

OUT_DIR = Path(__file__).resolve().parent


def _gradient(size: int) -> Image.Image:
    """Return a square RGBA diagonal sky->blue gradient of ``size`` px."""
    base = Image.new("RGB", (size, size), SKY_500)
    top = Image.new("RGB", (size, size), BLUE_600)
    mask = Image.new("L", (size, size))
    mask_px = mask.load()
    for y in range(size):
        for x in range(size):
            # Diagonal blend: 0 at top-left (sky) -> 255 at bottom-right (blue).
            mask_px[x, y] = int((x + y) / (2 * (size - 1)) * 255)
    return Image.composite(top, base, mask).convert("RGBA")


def _load_font(px: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Best-effort bold font at ``px`` size; fall back to PIL's default."""
    for name in ("arialbd.ttf", "Arial Bold.ttf", "DejaVuSans-Bold.ttf", "arial.ttf"):
        try:
            return ImageFont.truetype(name, px)
        except OSError:
            continue
    return ImageFont.load_default()


def _draw_glyph(img: Image.Image, glyph_ratio: float) -> None:
    """Center a white "A" glyph occupying ``glyph_ratio`` of the icon height."""
    size = img.width
    draw = ImageDraw.Draw(img)
    font = _load_font(int(size * glyph_ratio))
    left, top, right, bottom = draw.textbbox((0, 0), "A", font=font)
    x = (size - (right - left)) / 2 - left
    y = (size - (bottom - top)) / 2 - top
    draw.text((x, y), "A", font=font, fill=WHITE)


def _rounded(img: Image.Image, radius_ratio: float) -> Image.Image:
    """Apply rounded corners (for ``purpose: any`` and Apple icons)."""
    size = img.width
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, size - 1, size - 1), radius=int(size * radius_ratio), fill=255)
    out = img.copy()
    out.putalpha(mask)
    return out


def make_any(size: int) -> Image.Image:
    img = _gradient(size)
    _draw_glyph(img, glyph_ratio=0.62)
    return _rounded(img, radius_ratio=0.18)


def make_maskable(size: int) -> Image.Image:
    # Full-bleed background (no rounded corners) and a smaller glyph kept inside
    # the ~80% safe zone so adaptive masks never clip it.
    img = _gradient(size)
    _draw_glyph(img, glyph_ratio=0.46)
    return img


def make_apple(size: int) -> Image.Image:
    # iOS ignores transparency and applies its own mask: keep it opaque + square.
    img = _gradient(size)
    _draw_glyph(img, glyph_ratio=0.62)
    return img


def main() -> None:
    make_any(192).save(OUT_DIR / "icon-192.png")
    make_any(512).save(OUT_DIR / "icon-512.png")
    make_maskable(512).save(OUT_DIR / "icon-maskable-512.png")
    make_apple(180).save(OUT_DIR / "apple-touch-icon.png")
    print(f"Icons written to {OUT_DIR}")


if __name__ == "__main__":
    main()
