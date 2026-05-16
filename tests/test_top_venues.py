"""Top-tier venue filter behaviour."""

from __future__ import annotations

import pytest

from autopapertoppt.core.models import Paper
from autopapertoppt.core.top_venues import (
    TOP_VENUE_TOKENS,
    TRUSTED_SOURCES,
    is_top_tier,
)


def _paper(source: str = "openalex", venue: str | None = None) -> Paper:
    return Paper(
        source=source,
        source_id="x",
        title="Title",
        authors=("Author A",),
        year=2025,
        venue=venue,
        abstract="",
        url="https://example.com/x",
    )


# ---------------------------------------------------------------------------
# Source-based passthrough
# ---------------------------------------------------------------------------


def test_arxiv_always_passes():
    assert is_top_tier(_paper(source="arxiv", venue=None))
    assert is_top_tier(_paper(source="arxiv", venue="some random venue"))


def test_non_trusted_source_with_no_venue_fails():
    assert not is_top_tier(_paper(source="openalex", venue=None))
    assert not is_top_tier(_paper(source="openalex", venue=""))


def test_trusted_sources_constant_includes_arxiv():
    assert "arxiv" in TRUSTED_SOURCES


# ---------------------------------------------------------------------------
# Venue-based matching across disciplines
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "venue",
    [
        "IEEE Symposium on Security and Privacy",
        "Proceedings of the 2024 ACM SIGSAC Conference on Computer and Communications Security",
        "Network and Distributed System Security Symposium",
        "32nd USENIX Security Symposium",
        "Symposium on Operating Systems Principles",
        "USENIX Symposium on Operating Systems Design and Implementation",
        "EuroSys '24",
        "Proceedings of the ACM SIGCOMM 2024 Conference",
        "Proceedings of the 2024 International Conference on Management of Data",
        "Proceedings of the VLDB Endowment",
        "International Conference on Software Engineering",
        "ESEC/FSE '24",
        "Advances in Neural Information Processing Systems 36",
        "International Conference on Machine Learning",
        "International Conference on Learning Representations",
        "Proceedings of the AAAI Conference on Artificial Intelligence",
        "Findings of the Association for Computational Linguistics: EMNLP 2024",
        "Conference on Computer Vision and Pattern Recognition",
        "ACM SIGGRAPH 2024 Conference Papers",
        "Proceedings of the CHI Conference on Human Factors in Computing Systems",
        "POPL '25",
        "Symposium on Theory of Computing",
        "Journal of the ACM",
        "Communications of the ACM",
        "IEEE Transactions on Pattern Analysis and Machine Intelligence",
        "International Symposium on Computer Architecture",
        "ASPLOS '25",
        # Multidisciplinary flagship journals (added with the Springer plugin)
        "Nature 632",
        "Nature Machine Intelligence",
        "Nature Communications",
        "Scientific Reports",
        "Science 384",
        "Science Advances",
        "Proceedings of the National Academy of Sciences",
        "Lecture Notes in Computer Science",
        "Machine Learning",
    ],
)
def test_top_tier_venue_match(venue):
    assert is_top_tier(_paper(source="openalex", venue=venue)), (
        f"venue {venue!r} should pass the top-tier filter"
    )


@pytest.mark.parametrize(
    "venue",
    [
        "Generic Workshop on Random Things",
        "Some Tiny Journal of Obscure Topics",
        "Proceedings of XYZ Local Symposium",
        "Predatory Open Access Letters",
        "International Journal of Engineering Trends",
    ],
)
def test_low_tier_venue_rejected(venue):
    assert not is_top_tier(_paper(source="openalex", venue=venue))


def test_matching_is_case_insensitive():
    upper = _paper(source="openalex", venue="NEURIPS")
    lower = _paper(source="openalex", venue="neurips")
    assert is_top_tier(upper)
    assert is_top_tier(lower)


def test_top_venue_tokens_is_lowercase():
    """All patterns must be lowercase so the substring check works."""
    for token in TOP_VENUE_TOKENS:
        assert token == token.lower(), f"{token!r} contains upper-case chars"
