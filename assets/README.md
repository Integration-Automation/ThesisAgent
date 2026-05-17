# Assets

The project's visual assets — the app icon shipped on the Windows
executable and the desktop GUI's window/taskbar/Alt-Tab icon.

## Files

| File | Purpose |
|---|---|
| `icon.ico` | Multi-resolution Windows icon (16, 32, 48, 64, 128, 256 px). Wired into Nuitka via `--windows-icon-from-ico=` and into PySide6 via `QApplication.setWindowIcon`. |
| `icon-256.png` | Single 256×256 PNG. Used by docs / READMEs and as a fallback for platforms that don't read `.ico`. |
| `generate_icon.py` | The reproducible Pillow recipe that produces both files. Re-run when the design changes. |

## Design

A rounded deep-blue square containing a stylised **paper → slide**
glyph:

- **Background** — Tailwind blue-800 (`#1E40AF`) rounded square with
  a subtle blue-600 top-half highlight so it doesn't read as a flat
  tile.
- **Paper** — white rounded portrait rectangle with four slate-400
  text-line placeholders, evoking an academic paper's body. The last
  line is shorter to mimic a ragged-edge abstract.
- **Slide** — amber-500 (`#F59E0B`) landscape rectangle overlapping
  the paper from the right, with a darker amber play triangle. This
  is the "PowerPoint" half of the metaphor.
- **Shadows** — slate-900 at 24% alpha, 1.2% offset, on both the
  paper and the slide. Gives the layered "stacked on top" feel
  without going full skeuomorphism.

The metaphor: the project takes academic papers as input (the white
sheet on the left) and produces slide decks as output (the amber
landscape tile on the right). The overlap and the play triangle make
the transformation read at a glance.

## Re-generating

```powershell
.\.venv\Scripts\python.exe assets\generate_icon.py
```

Output:

```
wrote D:\...\assets\icon.ico (~19 KB, 6 embedded sizes)
wrote D:\...\assets\icon-256.png (~8 KB)
```

The script renders at 1024×1024 then LANCZOS-downsamples to each
target size, so the small icon sizes Windows actually displays in
the taskbar stay crisp.

## Why not SVG

We considered shipping an SVG source for the icon and converting at
build time, but:

1. The Nuitka step on `windows-latest` would need an extra
   SVG → ICO toolchain (Inkscape, rsvg-convert, or
   Pillow + cairosvg with its native cairo dep).
2. The icon barely changes — committing the `.ico` directly avoids
   per-build conversion.
3. Pillow + ImageDraw with the high-res-then-downsample pattern
   gives anti-aliasing quality on par with SVG → raster for an icon
   that's mostly rounded rectangles and a triangle.

Re-rendering when the design changes is `python assets/generate_icon.py` —
one command, no toolchain install.

## Adding new icon-derived assets

To produce a Windows ICO from a new design:

1. Edit the geometry / colours in `generate_icon.py`.
2. Re-run the script.
3. Commit both `icon.ico` and `icon-256.png`. The build pipeline
   reads `icon.ico` from the repo, so it must be checked in.

To produce a macOS `.icns` (for a future macOS bundle):

1. Generate the same set of PNG sizes (`16`, `32`, `64`, `128`,
   `256`, `512`, `1024`) via `_draw_icon(size)`.
2. Use `iconutil -c icns <iconset>` on macOS, or `png2icns` on
   Linux. Both require system tools we don't currently use in CI.

The Linux case (`.desktop` icon) accepts the 256×256 PNG directly —
no extra conversion needed.
