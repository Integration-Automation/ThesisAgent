"""Generate the project's app icon (.ico + .png) from a Pillow recipe.

Design: a rounded deep-blue square containing a stylised "paper-to-
slide" glyph — a portrait paper-sheet on the left with 4 text lines,
and a landscape slide on the right with a play triangle (the
PowerPoint metaphor). The arrow between them carries the
"transformation" idea without spelling it out.

Run this script whenever the design needs to change; it writes
``assets/icon.ico`` (multi-resolution: 16, 32, 48, 64, 128, 256)
and ``assets/icon-256.png`` (single 256x256 PNG for README / docs /
GUI use). The .ico is committed to the repo so the build pipeline
doesn't need Pillow installed.

Usage:
    .venv\\Scripts\\python.exe assets\\generate_icon.py
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

# Render at 4x the target then downsample for crisper anti-aliasing at
# the small icon sizes Windows actually displays in the taskbar.
_RENDER_SIZE = 1024
_OUTPUT_SIZES = (256, 128, 64, 48, 32, 16)

# Palette — Tailwind blue-800 + amber-500 + clean white.
_BG = (30, 64, 175, 255)         # blue-800: academic, professional
_BG_ACCENT = (37, 99, 235, 255)  # blue-600: subtle inner gradient effect
_PAPER = (255, 255, 255, 255)
_PAPER_LINE = (148, 163, 184, 255)   # slate-400 — text-line placeholders
_SLIDE = (245, 158, 11, 255)     # amber-500: presentation accent
_SLIDE_DARK = (180, 117, 8, 255) # for the slide's small "play" triangle
_SHADOW = (15, 23, 42, 60)       # slate-900 @ 24% — drop shadow


def _rounded_rect(
    draw: ImageDraw.ImageDraw,
    bounds: tuple[int, int, int, int],
    radius: int,
    fill,
) -> None:
    """Wrapper so the call sites stay readable."""
    draw.rounded_rectangle(bounds, radius=radius, fill=fill)


def _draw_icon(size: int) -> Image.Image:
    """Draw the icon at the requested square size."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # 1. Rounded background — leaves a 4-pixel margin so the rounded
    # corners aren't clipped by the taskbar tile boundary.
    margin = size // 20
    _rounded_rect(
        draw,
        (margin, margin, size - margin, size - margin),
        radius=size // 8,
        fill=_BG,
    )

    # 2. Subtle inner highlight — a slightly lighter rounded rect inset
    # from the top so the icon doesn't read as a flat block.
    inset = size // 14
    _rounded_rect(
        draw,
        (inset, inset, size - inset, size // 2),
        radius=size // 12,
        fill=_BG_ACCENT,
    )

    # 3. Paper sheet — left-half portrait rectangle, white, rounded.
    # Geometry is computed off the icon size so it scales cleanly.
    paper_w = size * 0.34
    paper_h = size * 0.50
    paper_x = size * 0.16
    paper_y = (size - paper_h) / 2
    paper_box = (paper_x, paper_y, paper_x + paper_w, paper_y + paper_h)
    # Shadow first, then sheet — gives the slight 3D pop.
    shadow_offset = size * 0.012
    _rounded_rect(
        draw,
        (
            paper_box[0] + shadow_offset,
            paper_box[1] + shadow_offset,
            paper_box[2] + shadow_offset,
            paper_box[3] + shadow_offset,
        ),
        radius=int(size * 0.024),
        fill=_SHADOW,
    )
    _rounded_rect(draw, paper_box, radius=int(size * 0.024), fill=_PAPER)

    # 3a. Text lines on the paper — 4 horizontal slate-400 rules.
    line_count = 4
    line_h = size * 0.018
    line_gap = paper_h / (line_count + 2)
    line_left = paper_x + size * 0.04
    line_right = paper_x + paper_w - size * 0.04
    for i in range(line_count):
        y = paper_y + line_gap * (i + 1.2)
        # The last line is shorter (mimics an abstract's last-line ragged edge).
        right = line_right if i < line_count - 1 else line_left + (line_right - line_left) * 0.6
        _rounded_rect(
            draw,
            (line_left, y, right, y + line_h),
            radius=line_h / 2,
            fill=_PAPER_LINE,
        )

    # 4. Slide tile — right-half landscape rectangle, amber. Overlapping
    # the paper to suggest "the paper becomes the slide".
    slide_w = size * 0.36
    slide_h = size * 0.30
    slide_x = size * 0.46
    slide_y = (size - slide_h) / 2 + size * 0.04
    slide_box = (slide_x, slide_y, slide_x + slide_w, slide_y + slide_h)
    # Shadow first.
    _rounded_rect(
        draw,
        (
            slide_box[0] + shadow_offset,
            slide_box[1] + shadow_offset,
            slide_box[2] + shadow_offset,
            slide_box[3] + shadow_offset,
        ),
        radius=int(size * 0.020),
        fill=_SHADOW,
    )
    _rounded_rect(draw, slide_box, radius=int(size * 0.020), fill=_SLIDE)

    # 4a. Play triangle on the slide — small, centred, slightly to the
    # right so it reads as "presentation in progress" rather than just
    # "media play button".
    cx = slide_x + slide_w * 0.52
    cy = slide_y + slide_h / 2
    tri = size * 0.045
    draw.polygon(
        [
            (cx - tri * 0.6, cy - tri),
            (cx - tri * 0.6, cy + tri),
            (cx + tri, cy),
        ],
        fill=_SLIDE_DARK,
    )

    return img


def _multi_resolution_icon() -> tuple[Image.Image, list[Image.Image]]:
    """Render at high res, downsample to every required size."""
    base = _draw_icon(_RENDER_SIZE)
    variants: list[Image.Image] = []
    for target in _OUTPUT_SIZES:
        # LANCZOS gives the best downsample quality for crisp edges.
        variants.append(base.resize((target, target), Image.Resampling.LANCZOS))
    # Pillow's .ico writer uses the first image's dimensions for the
    # default size and embeds the `sizes` argument as additional
    # resolutions, so we return both the 256x256 master and the full
    # variant list.
    return variants[0], variants


def main() -> int:
    assets_dir = Path(__file__).resolve().parent
    master, variants = _multi_resolution_icon()

    ico_path = assets_dir / "icon.ico"
    master.save(
        ico_path,
        format="ICO",
        sizes=[(v.width, v.height) for v in variants],
    )
    print(f"wrote {ico_path} ({ico_path.stat().st_size} bytes, "
          f"{len(variants)} embedded sizes)")

    png_path = assets_dir / "icon-256.png"
    master.save(png_path, format="PNG", optimize=True)
    print(f"wrote {png_path} ({png_path.stat().st_size} bytes)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
