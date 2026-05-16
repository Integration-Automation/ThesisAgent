"""LLM-powered enrichment: PDF text extraction + structured summarisation.

Optional extra — install with ``pip install autopapertoppt[intelligence]``
to pull in ``pypdf`` and the ``anthropic`` SDK.
"""

from autopapertoppt.intelligence.pdf import fetch_and_extract
from autopapertoppt.intelligence.summarise import (
    DEFAULT_MODEL,
    AnthropicSummariser,
    summarise_paper,
)

__all__ = [
    "DEFAULT_MODEL",
    "AnthropicSummariser",
    "fetch_and_extract",
    "summarise_paper",
]
