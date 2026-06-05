"""LLM-powered enrichment: PDF text extraction + structured summarisation.

Optional extra — install with ``pip install thesisagents[intelligence]``
to pull in ``pypdf`` and the ``anthropic`` SDK.
"""

from thesisagents.intelligence.pdf import fetch_and_extract
from thesisagents.intelligence.summarise import (
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
