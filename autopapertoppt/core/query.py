"""Query normalisation. Always run user keywords through here before building a URL."""

from __future__ import annotations

import re
import unicodedata

from autopapertoppt.core.constants import MAX_KEYWORD_LENGTH

_CONTROL_CHARS = re.compile(r"[\x00-\x1f\x7f]")
_WHITESPACE = re.compile(r"\s+")


def normalize_query(raw: str) -> str:
    """Normalise a user-supplied keyword string.

    - NFC-normalise so visually identical inputs hash the same.
    - Drop control characters.
    - Collapse whitespace.
    - Cap length.
    """
    if raw is None:
        raise ValueError("query cannot be None")
    normalised = unicodedata.normalize("NFC", raw)
    normalised = _CONTROL_CHARS.sub(" ", normalised)
    normalised = _WHITESPACE.sub(" ", normalised).strip()
    if not normalised:
        raise ValueError("query is empty after normalisation")
    if len(normalised) > MAX_KEYWORD_LENGTH:
        normalised = normalised[:MAX_KEYWORD_LENGTH].rstrip()
    return normalised
