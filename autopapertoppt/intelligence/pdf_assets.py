"""Figure / table extraction from a paper PDF using PyMuPDF.

Why PyMuPDF over pypdf: most academic papers ship figures as vector
graphics (Matplotlib-rendered, LaTeX-typeset). ``pypdf.page.images``
only sees embedded raster images and therefore misses most figures.
PyMuPDF can render an arbitrary page region as a bitmap, which is the
only reliable way to surface vector figures in a slide deck.

The flow:

1. ``extract_figures`` walks each page, asks PyMuPDF for image blocks
   *and* layout blocks, filters out tiny / decorative items, and
   renders the bounding box as a PNG. The neighbouring text block
   that begins with ``Figure N`` becomes the caption guess.
2. ``extract_tables`` uses PyMuPDF's ``page.find_tables()`` (≥ 1.23)
   to enumerate tabular regions and return rows of cleaned cell text.

PyMuPDF is an optional dep (``[intelligence]`` extras); the helpers
raise :class:`ConfigError` when the dep is missing.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from autopapertoppt.core.exceptions import ConfigError
from autopapertoppt.utils.logging import get_logger
from autopapertoppt.utils.path_safety import ensure_export_dir, safe_filename

_LOG = get_logger(__name__)

#: PyMuPDF reports widths/heights in PDF points (1 pt = 1/72").
#: A real figure is rarely under 200pt × 100pt; anything smaller is
#: usually a glyph / decorative element / equation snippet.
_MIN_FIGURE_WIDTH_PT: float = 200.0
_MIN_FIGURE_HEIGHT_PT: float = 100.0
#: Render figures at 144 DPI so the slide-embedded PNGs look sharp at
#: ~3" wide on a 13.33" canvas.
_RENDER_DPI: int = 144
#: Cap so a malicious / oversized PDF can't blow out disk.
_MAX_FIGURES_PER_PAPER: int = 20
_MAX_TABLES_PER_PAPER: int = 10

_FIGURE_CAPTION_RE = re.compile(
    r"^\s*(?:Fig(?:ure)?\.?|圖|図)\s*\d+[.:]?\s*(.+)", re.IGNORECASE
)
_TABLE_CAPTION_RE = re.compile(
    r"^\s*(?:Table|表|テーブル)\s*\d+[.:]?\s*(.+)", re.IGNORECASE
)


@dataclass(frozen=True, slots=True)
class ExtractedFigure:
    """One extracted figure: bounding region rendered to PNG + caption guess."""

    page_number: int
    image_path: Path
    caption: str


@dataclass(frozen=True, slots=True)
class ExtractedTable:
    """One extracted table: cleaned rows + caption guess (first row is header)."""

    page_number: int
    caption: str
    rows: tuple[tuple[str, ...], ...]


def extract_figures(
    pdf_path: str | Path, out_dir: str | Path
) -> list[ExtractedFigure]:
    """Render every figure-sized page region in ``pdf_path`` as a PNG.

    Returns a list of ``ExtractedFigure``. The caller (typically an LLM
    agent in the loop) is expected to curate this list — keep the
    meaningful ones, drop the noise — before handing references to the
    exporter.
    """
    fitz = _import_fitz()
    pdf_path = Path(pdf_path)
    out_root = ensure_export_dir(out_dir)
    figures: list[ExtractedFigure] = []
    with fitz.open(str(pdf_path)) as doc:
        for page_index in range(len(doc)):
            page = doc[page_index]
            text_blocks = _text_blocks(page)
            for rect, kind in _figure_rects(page):
                if len(figures) >= _MAX_FIGURES_PER_PAPER:
                    break
                if (
                    rect.width < _MIN_FIGURE_WIDTH_PT
                    or rect.height < _MIN_FIGURE_HEIGHT_PT
                ):
                    continue
                caption = _nearest_caption(rect, text_blocks, _FIGURE_CAPTION_RE)
                if not caption:
                    caption = f"Figure on page {page_index + 1}"
                slug = safe_filename(caption)[:60] or f"figure-p{page_index + 1}"
                image_path = (
                    out_root
                    / f"p{page_index + 1:02d}-{len(figures):02d}-{slug}.png"
                )
                _render_region_to_png(page, rect, image_path, kind=kind)
                figures.append(
                    ExtractedFigure(
                        page_number=page_index + 1,
                        image_path=image_path,
                        caption=caption,
                    )
                )
    _LOG.info(
        "extracted %d figures from %s → %s", len(figures), pdf_path, out_root
    )
    return figures


def extract_tables(pdf_path: str | Path) -> list[ExtractedTable]:
    """Enumerate tabular regions via PyMuPDF and return cleaned rows.

    Tables whose cell text contains very long blobs or whose row count
    is < 2 are skipped — those are usually false positives.
    """
    fitz = _import_fitz()
    pdf_path = Path(pdf_path)
    tables: list[ExtractedTable] = []
    with fitz.open(str(pdf_path)) as doc:
        for page_index in range(len(doc)):
            page = doc[page_index]
            try:
                found = page.find_tables()
            except Exception as err:  # noqa: BLE001  # PyMuPDF raises various
                _LOG.debug("find_tables failed on page %d: %s", page_index + 1, err)
                continue
            text_blocks = _text_blocks(page)
            for table in found.tables:
                if len(tables) >= _MAX_TABLES_PER_PAPER:
                    break
                rows = _clean_table_rows(table.extract())
                if not rows or len(rows) < 2:
                    continue
                caption = _nearest_caption(
                    table.bbox, text_blocks, _TABLE_CAPTION_RE
                ) or f"Table on page {page_index + 1}"
                tables.append(
                    ExtractedTable(
                        page_number=page_index + 1,
                        caption=caption,
                        rows=rows,
                    )
                )
    _LOG.info("extracted %d tables from %s", len(tables), pdf_path)
    return tables


def _import_fitz():
    try:
        import fitz  # type: ignore  # PyMuPDF
    except ImportError as err:
        raise ConfigError(
            "PyMuPDF (fitz) is not installed; install the [intelligence] extra"
        ) from err
    return fitz


def _figure_rects(page):
    """Yield (rect, kind) pairs that could be figures.

    ``kind`` is either ``"image"`` (raster source available) or
    ``"vector"`` (synthesised from a drawing-block bounding box). For
    both we ultimately render the page region as a bitmap so the slide
    embed works identically.
    """
    fitz = _import_fitz()
    # First pass: raster images (PyMuPDF gives the rect already)
    for image_info in page.get_image_info(xrefs=True):
        bbox = image_info.get("bbox")
        if not bbox:
            continue
        yield fitz.Rect(bbox), "image"
    # Second pass: vector / drawing blocks. ``get_text("dict")`` exposes
    # block type 1 = image but skips drawings; ``get_drawings`` returns
    # vector primitives whose unioned bbox usually equals the figure.
    drawing_clusters = _cluster_drawings(page.get_drawings())
    for rect in drawing_clusters:
        yield rect, "vector"


def _cluster_drawings(drawings):
    """Union nearby vector primitives into figure-sized rectangles."""
    fitz = _import_fitz()
    if not drawings:
        return []
    rects: list = []
    for d in drawings:
        rect = d.get("rect")
        if rect is None:
            continue
        rects.append(fitz.Rect(rect))
    if not rects:
        return []
    # Greedy clustering: merge any two rects whose distance is small
    # relative to their size. This collapses a Matplotlib figure's many
    # axis / glyph primitives into one bounding rectangle.
    merged: list = []
    for rect in sorted(rects, key=lambda r: (r.y0, r.x0)):
        if (
            merged
            and rect.y0 - merged[-1].y1 < 30
            and abs(rect.x0 - merged[-1].x0) < merged[-1].width + 50
        ):
            merged[-1].include_rect(rect)
        else:
            merged.append(fitz.Rect(rect))
    return merged


def _text_blocks(page):
    return [
        (block[0], block[1], block[2], block[3], (block[4] or "").strip())
        for block in page.get_text("blocks")
        if len(block) >= 5
    ]


def _nearest_caption(rect, text_blocks, pattern):
    """Find the closest text block matching ``pattern`` below or above
    ``rect``. Returns the regex-captured caption text or ``""``."""
    best_text = ""
    best_distance = float("inf")
    rect_y_bottom = rect.y1 if hasattr(rect, "y1") else rect[3]
    rect_y_top = rect.y0 if hasattr(rect, "y0") else rect[1]
    for _x0, y0, _x1, y1, text in text_blocks:
        match = pattern.match(text)
        if not match:
            continue
        # Prefer captions BELOW the figure (academic convention) but
        # accept above-figure captions for tables.
        if y0 >= rect_y_bottom:
            distance = y0 - rect_y_bottom
        elif y1 <= rect_y_top:
            distance = rect_y_top - y1 + 50  # penalty for above
        else:
            continue
        if distance < best_distance:
            best_distance = distance
            best_text = match.group(1).strip()
    return best_text[:200]


def _render_region_to_png(page, rect, image_path: Path, *, kind: str) -> None:
    _ = kind  # signal for callers; both render the same way
    fitz = _import_fitz()
    zoom = _RENDER_DPI / 72.0
    matrix = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=matrix, clip=rect, alpha=False)
    pix.save(str(image_path))


def _clean_table_rows(raw_rows):
    """Trim whitespace and drop rows that are entirely empty."""
    cleaned: list[tuple[str, ...]] = []
    for row in raw_rows or []:
        cells = tuple(" ".join((cell or "").split()) for cell in row)
        if any(cells):
            cleaned.append(cells)
    return tuple(cleaned)
