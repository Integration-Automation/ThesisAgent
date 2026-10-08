"""Persistent literature library: papers, sightings, citation links, verdicts.

See :mod:`thesisagents.library.store` for the API and
:mod:`thesisagents.library.schema` for the tables and their versioning.
"""

from thesisagents.library.schema import SCHEMA_VERSION
from thesisagents.library.store import (
    LIBRARY_SOURCE,
    VERIFIED_FOR,
    AddReport,
    Library,
    LibraryEntry,
    LibraryRun,
    LibraryStats,
    LibraryVerificationCache,
)

__all__ = [
    "LIBRARY_SOURCE",
    "SCHEMA_VERSION",
    "VERIFIED_FOR",
    "AddReport",
    "Library",
    "LibraryEntry",
    "LibraryRun",
    "LibraryStats",
    "LibraryVerificationCache",
]
