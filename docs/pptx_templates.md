# Deck templates

By default every deck is the built-in navy-band design: python-pptx's
blank layout, with the header band, the cover panel, the fonts and the
colours all drawn by the exporter. A **template** lets your own
PowerPoint file carry the deck instead, so a university or company
template with its background, logo and layouts can be used without
changing the exporter.

This page is the template contract: what a template must offer, what a
config file may override, and what is fixed.

```bash
# See what an export would do with the template. Nothing is rendered.
thesisagents validate-template thesis.pptx --config thesis.toml

# Build the decks on it.
thesisagents --query "graph neural networks" \
    --pptx-template thesis.pptx --pptx-template-config thesis.toml
```

The same options exist everywhere a deck is exported:

| Surface | Template | Config | Check only |
|---|---|---|---|
| CLI | `--pptx-template FILE` | `--pptx-template-config FILE` | `thesisagents validate-template FILE [--config FILE] [--dark-mode] [--json]` |
| MCP | `export(pptx_template=...)` | `export(pptx_template_config=...)` | `pptx_validate_template(path, config, dark_mode)` |
| Python | `ExportOptions(pptx_template=...)` | `ExportOptions(pptx_template_config=...)` | `validate_template(path, config)` |

## What a template must offer

### 1. 16:9 slides

The exporter places every shape for a 13.333 x 7.5 in slide. A template
of another size is handled by `slide_size` in the config:

| `slide_size` | A 4:3 (or other) template is |
|---|---|
| `"normalise"` (default) | resized to 16:9 and reported as a warning. Artwork the template placed for its own size keeps its position, so it may sit off-centre. |
| `"reject"` | refused, with the size it has and the size that is needed. |

The clean fix is a 16:9 version of the template (PowerPoint: Design >
Slide Size).

### 2. A layout for slide content

Every slide the exporter makes has one of six **roles**:

| Role | Slides |
|---|---|
| `cover` | The first slide. |
| `section` | The "Paper N of M" divider of a multi-paper deck. |
| `content` | Every "title on top, content below" slide that is not a table or the references. |
| `table` | Technique, literature, result and paper tables. |
| `references` | The reference list. |
| `qa` | The closing Q&A slide. |

The layout a role uses is the first of these that exists:

1. the layout the config names for it under `[layouts]`,
2. a layout named after the role (`cover`, `section`, `content`,
   `table`, `references` or `reference`, `qa` or `q&a`, in any letter
   case),
3. the layout of the `content` role,
4. for `content` itself: a layout named `Blank`, or failing that the
   first layout with no placeholders.

So a template needs **one** thing: a layout the `content` role can
use. Everything else falls back to it. A template with no such layout
is refused, and the message lists the layouts it does have.

What a layout brings to the slide is its artwork and that of its
master: background, logo, decorative shapes. The **placeholders** a
layout would put on a slide are removed, because the exporter draws its
own named text boxes (`title`, `body`, `meta`, ...) at positions the
overflow check knows. No "Click to add title" box is left behind.

### 3. A title placeholder, when you ask for one

By default the exporter draws the slide title itself, in white, inside
its navy header band. For the `content`, `table` and `references`
roles a config can instead ask for the title to be written into the
layout's own title placeholder, so it sits where the template puts
titles:

```toml
[placeholders]
title = ["content", "table", "references"]
```

For each role listed, the layout must then

- **have a title placeholder**, and
- that placeholder must **end at or above 1.40 in** from the top of
  the slide, which is where the first line under a title starts.

Either one missing is an error that names the layout. On these slides
the header band is not drawn (the template owns the title area) and the
title is set in the `primary` colour.

## What a config may override

A config is a TOML or JSON file. Every part is optional.

```toml
slide_size = "reject"            # or "normalise" (the default)

[layouts]                        # role -> layout name in the template
cover      = "Title Slide"
section    = "Section Header"
content    = "Title Only"
table      = "Title Only"
references = "Title Only"

[placeholders]                   # roles whose title goes into the layout's title placeholder
title = ["content", "table", "references"]

[fonts]                          # replaces the per-language default, one slot at a time
latin      = "Source Sans 3"
east_asian = "Noto Sans TC"

[colors]                         # "#RRGGBB"
primary   = "#0B3D2E"            # body text, header band, cover panel, table header
highlight = "#0E7C61"            # emphasis text (KPI values, the research question), accent rule
muted     = "#4B5563"            # captions, metadata
subtle    = "#9CA3AF"            # footers, page numbers

[chrome]                         # shapes the exporter draws itself
header_band = true               # navy band behind the title of content slides
cover_panel = false              # full-slide navy panel behind the cover
```

`thesisagents validate-template thesis.pptx --config thesis.toml` on a
template with these layouts, run on 2026-10-08, printed:

```
Template thesis.pptx: OK
  config: thesis.toml
  slides: 13.33 x 7.50 in
  cover      -> Title Slide
  section    -> Section Header
  content    -> Title Only
  table      -> Title Only
  references -> Title Only
  qa         -> Title Only
```

**Fonts.** Each of the two slots replaces the built-in choice for that
slot only. A config that sets `latin` and not `east_asian` keeps the
language's East-Asian font (Microsoft JhengHei UI for `zh-tw`, Yu
Gothic UI for `ja`, and so on).

**Colours.** The four names replace the built-in palette wherever it is
used, as text and as fill. Two rules are checked when the config is
read:

- a colour must be dark enough to read on a white slide, and `primary`
  dark enough to carry white titles and table headers,
- `#C0392B` is refused: red text reads as an error or a warning on a
  slide.

Colours are **not applied to a dark-mode export**. Dark mode has its
own palette, tuned for contrast on the dark background, and
`validate-template --dark-mode` reports that as a warning.

**Chrome.** A template that brings its own header or cover artwork
switches the exporter's off. Text that was white because it sat on the
navy is then set in `primary` (titles) and `muted` (the cover's
secondary lines), so it stays readable on the template's background.

## What is fixed

Font **sizes** and **margins** cannot be changed. Slide geometry, the
per-slide content caps and the overflow check are calibrated for the
built-in values, and a deck that passes `thesisagents review` with them
would not be guaranteed to with others. A config with `[sizes]`,
`[styles]` or `[margins]` is refused with a message saying so.

A template is expected to have a **light background** in light mode,
because body text is dark. For a dark deck use `--dark-mode`, which
paints its own background on every slide.

## Checking a template

`validate-template` reports **errors**, which stop an export, and
**warnings**, which do not:

| Code | Kind | Meaning |
|---|---|---|
| `unreadable-template` | error | The file is missing or is not a PowerPoint file. |
| `invalid-config` | error | The config is not valid TOML / JSON, or has a setting that is wrong. Every problem is listed. |
| `slide-size` | error | The slides are not 16:9 and `slide_size = "reject"`. |
| `no-content-layout` | error | No layout can serve the `content` role. |
| `layout-not-found` | error | `[layouts]` names a layout the template does not have. The message lists the ones it has. |
| `missing-title-placeholder` | error | `[placeholders] title` lists a role whose layout has no title placeholder. |
| `title-placeholder-overlaps-content` | error | That placeholder ends below 1.40 in. |
| `slide-size-normalised` | warning | The slides are not 16:9 and the deck is resized. |
| `colors-ignored-in-dark-mode` | warning | `[colors]` is set and the export is dark. |

A broken config reads like this (same run):

```
Template thesis.pptx: NOT USABLE
  config: bad.toml
  slides: 13.33 x 7.50 in
  error: template config bad.toml has 3 problem(s):
  - [margins] is not supported: margins are fixed, because slide geometry and the overflow check are calibrated for the built-in values
  - [placeholders] title cannot include 'cover': the title placeholder is offered for content, table, references
  - [colors] primary = #FDE68A is too light: it is used as text on a white slide, and as the fill behind white titles. Pick a darker colour.
```

The exit code is `0` for a usable template and `2` otherwise. `--json`
prints the report as an object with `ok`, `layouts`,
`available_layouts`, `errors` and `warnings`.

The export runs the same check on the same file before it renders
anything. From the CLI the check happens before the search starts, so
a mistyped layout name costs a second and not the run.

## After the export

A deck built on a template is an ordinary deck. `thesisagents review`
audits it like any other (overflow, colour contracts, section
completeness), and the `pptx_*` editing tools work on it: the semantic
shape names are the same, including `title` when it sits in a
placeholder. A deck with custom `[colors]` gets `off-palette` notes
from the review. They are informational, not failures.

## In Python

```python
from thesisagents.core.models import ExportOptions
from thesisagents.exporters import export_collection
from thesisagents.exporters.template import validate_template

report = validate_template("thesis.pptx", "thesis.toml")
if not report.ok:
    raise SystemExit(report.message())
for role, layout in report.layouts.items():
    print(role, "->", layout)

export_collection(
    collection,
    ExportOptions(
        formats=("pptx",),
        out_dir="./exports",
        pptx_template="thesis.pptx",
        pptx_template_config="thesis.toml",
    ),
)
```

`export_collection` raises `TemplateError` (an `ExportError`) when the
template does not meet the contract, before any file is written.
