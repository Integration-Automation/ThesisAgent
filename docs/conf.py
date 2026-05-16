# -- Sphinx configuration for AutoPaperToPPT documentation --

project = "AutoPaperToPPT"
author = "AutoPaperToPPT Contributors"
copyright = "2025-2026, AutoPaperToPPT Contributors"  # noqa: A001
release = "0.1"

extensions = [
    "sphinx.ext.autosectionlabel",
    "myst_parser",
]

# Section titles repeat across language indexes; namespace them by document
# path so RTD's link checker stops complaining about duplicates.
autosectionlabel_prefix_document = True
autosectionlabel_maxdepth = 3

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

# Markdown reference pages ship side-by-side with the RST language indexes
# — myst_parser handles the .md → docutils conversion so they slot into
# the toctree directly.
source_suffix = {
    ".rst": "restructuredtext",
    ".md": "markdown",
}

html_theme = "sphinx_rtd_theme"
html_static_path: list[str] = []
html_logo = None
html_favicon = None

# JSON code blocks in mcp.md use literal "..." placeholders for snipped
# content; Pygments' strict JSON lexer choked on them. Tell it to be
# lenient so the build is clean.
highlight_options = {"json": {"ensurenl": False}}

# -- Internationalisation ----------------------------------------------------
language = "en"
locale_dirs = ["locale/"]
gettext_compact = False

# -- Options for HTML output -------------------------------------------------
html_theme_options = {
    "navigation_depth": 3,
    "collapse_navigation": False,
    "sticky_navigation": True,
    "titles_only": False,
}
