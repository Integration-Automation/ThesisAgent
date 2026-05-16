"""Top-tier CS venue whitelist for filtering search results.

A paper passes the filter if any of:

* it comes from ``arxiv`` — preprints don't have a venue yet, and the user's
  brief explicitly listed arXiv as a trusted top-tier source;
* its ``venue`` contains one of the canonical names in :data:`TOP_VENUE_TOKENS`
  (case-insensitive substring match).

The list is intentionally curated — top conferences + flagship journals across
security, systems, ML/AI, NLP, vision, DB, HCI, SE, networking, PL, theory,
graphics, and hardware. Edit the tuple to taste; tests pin the public surface
so adding a venue is one-line + one assertion.
"""

from __future__ import annotations

from autopapertoppt.core.models import Paper

#: Sources whose papers bypass the venue filter. arXiv preprints rarely have
#: a publication venue attached at submission time, and the user listed arXiv
#: as a trusted top-tier source.
TRUSTED_SOURCES: frozenset[str] = frozenset({"arxiv"})

#: Lower-cased substring patterns. A paper's venue (also lower-cased) must
#: contain at least one of these to count as top-tier. Patterns are chosen
#: to be specific enough that incidental matches are rare ("ccs" alone would
#: collide; "computer and communications security" or "acm ccs" won't).
TOP_VENUE_TOKENS: tuple[str, ...] = (
    # ------------------------------------------------------------------
    # Security
    # ------------------------------------------------------------------
    "ieee symposium on security and privacy",
    "computer and communications security",
    "acm ccs",
    "network and distributed system security",
    "usenix security",
    "cryptology eprint",
    "advances in cryptology",
    "eurocrypt",
    "crypto ",  # "crypto 2024" — the trailing space avoids matching "cryptography"
    "asiacrypt",
    "tches",
    # ------------------------------------------------------------------
    # Systems / OS / Networking / DB
    # ------------------------------------------------------------------
    "symposium on operating systems principles",
    "operating systems design and implementation",
    "eurosys",
    "usenix annual technical conference",
    "networked systems design and implementation",
    "file and storage technologies",
    "sigcomm",
    "internet measurement conference",
    "mobicom",
    "international conference on management of data",
    "sigmod",
    "very large data bases",
    "vldb",
    "international conference on data engineering",
    "icde",
    # ------------------------------------------------------------------
    # Software engineering / PL
    # ------------------------------------------------------------------
    "international conference on software engineering",
    " icse ",
    "esec/fse",
    "foundations of software engineering",
    "automated software engineering",
    "issta",
    "principles of programming languages",
    "popl",
    "programming language design and implementation",
    "pldi",
    "object-oriented programming",
    "oopsla",
    # ------------------------------------------------------------------
    # ML / AI
    # ------------------------------------------------------------------
    "advances in neural information processing systems",
    "neurips",
    "neural information processing systems",
    "international conference on machine learning",
    "international conference on learning representations",
    "iclr",
    "aaai conference on artificial intelligence",
    "ijcai",
    "uncertainty in artificial intelligence",
    "conference on learning theory",
    "journal of machine learning research",
    "ieee transactions on pattern analysis and machine intelligence",
    # ------------------------------------------------------------------
    # NLP
    # ------------------------------------------------------------------
    "association for computational linguistics",
    "empirical methods in natural language processing",
    "north american chapter of the association for computational linguistics",
    "transactions of the association for computational linguistics",
    # ------------------------------------------------------------------
    # Vision / Graphics
    # ------------------------------------------------------------------
    "computer vision and pattern recognition",
    "international conference on computer vision",
    "european conference on computer vision",
    "siggraph",
    # ------------------------------------------------------------------
    # HCI
    # ------------------------------------------------------------------
    "human factors in computing systems",
    "user interface software and technology",
    "computer-supported cooperative work",
    # ------------------------------------------------------------------
    # Theory
    # ------------------------------------------------------------------
    "symposium on theory of computing",
    "symposium on foundations of computer science",
    "symposium on discrete algorithms",
    "journal of the acm",
    # ------------------------------------------------------------------
    # Architecture / Hardware
    # ------------------------------------------------------------------
    "international symposium on computer architecture",
    "international symposium on microarchitecture",
    "high performance computer architecture",
    "architectural support for programming languages",
    "asplos",
    # ------------------------------------------------------------------
    # Surveys / flagship journals
    # ------------------------------------------------------------------
    "acm computing surveys",
    "communications of the acm",
    "ieee transactions on software engineering",
    "acm transactions on programming languages",
    "acm transactions on software engineering",
    "ieee transactions on dependable and secure computing",
    "ieee transactions on information forensics and security",
    # ------------------------------------------------------------------
    # Multidisciplinary flagship journals (Nature / Science / PNAS) and
    # their CS-relevant sister journals. The Springer plugin surfaces
    # these directly; OpenAIRE + Crossref + OpenAlex also commonly route
    # papers here.
    # ------------------------------------------------------------------
    "nature ",  # "Nature 632" — trailing space avoids "Natural" / "Nature-" prefixed venues
    "nature machine intelligence",
    "nature computational science",
    "nature communications",
    "nature methods",
    "scientific reports",
    "science ",  # "Science 384" — trailing space avoids "Sciences" / "Sciencey-"
    "science advances",
    "proceedings of the national academy of sciences",
    "machine learning",  # Springer ML journal — venue string is exactly this
    "lecture notes in computer science",
)


def is_top_tier(paper: Paper) -> bool:
    """True if the paper passes the top-tier venue filter.

    See module docstring for the rule set.
    """
    if paper.source in TRUSTED_SOURCES:
        return True
    venue = (paper.venue or "").lower()
    if not venue:
        return False
    return any(token in venue for token in TOP_VENUE_TOKENS)
