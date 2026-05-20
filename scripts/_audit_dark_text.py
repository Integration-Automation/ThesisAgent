"""Find every text run in a dark-mode deck whose colour is missing or
too dark to read against the #12151B slide background.

A run is flagged when:
- ``run.font.color.rgb is None`` (inherits theme default → renders as black)
- ``rgb == (0,0,0)`` (explicit black)
- ``rgb`` luminance below 60 (Rec.709 weights) AND not in the dark
  palette's accepted text set

Usage:
    .venv\\Scripts\\python.exe -m scripts._audit_dark_text <pptx_path>
"""
from __future__ import annotations

import sys
from pathlib import Path

from pptx import Presentation

# Colours we KNOW are intentional on a dark deck — accent red, the
# dark-mode text near-white, mid-greys, light-text on header fills.
_ACCEPTED_DARK_RUN_COLORS = {
    (0xE5, 0xE7, 0xEB),  # dark-mode body text
    (0x9C, 0xA3, 0xAF),  # dark-mode metadata grey
    (0x6B, 0x72, 0x80),  # dark-mode muted grey
    (0xFF, 0xFF, 0xFF),  # table-header white
    (0xC0, 0x39, 0x2B),  # brand accent red (legible on both bgs)
}


def _luminance(rgb: tuple[int, int, int]) -> float:
    return 0.2126 * rgb[0] + 0.7152 * rgb[1] + 0.0722 * rgb[2]


def _iter_runs(prs):
    for slide_idx, slide in enumerate(prs.slides, 1):
        for shape in slide.shapes:
            yield from _shape_runs(slide_idx, shape, "")
            if shape.has_table:
                for r_idx, row in enumerate(shape.table.rows):
                    for c_idx, cell in enumerate(row.cells):
                        yield from _shape_runs(
                            slide_idx, cell, f"table[{r_idx},{c_idx}]"
                        )


def _shape_runs(slide_idx: int, shape_or_cell, where_hint: str):
    text_frame = getattr(shape_or_cell, "text_frame", None)
    if text_frame is None:
        return
    name = getattr(shape_or_cell, "name", "") or where_hint
    for p_idx, paragraph in enumerate(text_frame.paragraphs):
        for r_idx, run in enumerate(paragraph.runs):
            try:
                rgb = run.font.color.rgb
            except (AttributeError, ValueError, TypeError):
                rgb = None
            text = (run.text or "")[:40]
            yield (slide_idx, name, p_idx, r_idx, rgb, text)


def main(pptx_path: Path) -> int:
    prs = Presentation(pptx_path)
    bad: list[str] = []
    for slide_idx, name, p_idx, r_idx, rgb, text in _iter_runs(prs):
        if not text.strip():
            continue
        rgb_tuple = tuple(rgb) if rgb is not None else None
        if rgb_tuple is None:
            bad.append(
                f"slide {slide_idx} {name!r} p{p_idx}r{r_idx}  rgb=None  text={text!r}"
            )
            continue
        if rgb_tuple in _ACCEPTED_DARK_RUN_COLORS:
            continue
        if _luminance(rgb_tuple) < 80:
            bad.append(
                f"slide {slide_idx} {name!r} p{p_idx}r{r_idx}  "
                f"rgb={rgb_tuple}  lum={_luminance(rgb_tuple):.0f}  text={text!r}"
            )
    print(f"audit: {pptx_path.name}")
    print(f"runs flagged: {len(bad)}")
    for line in bad[:40]:
        print("  " + line)
    if len(bad) > 40:
        print(f"  ... ({len(bad) - 40} more)")
    return 0 if not bad else 1


if __name__ == "__main__":
    sys.exit(main(Path(sys.argv[1])))
