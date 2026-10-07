"""The literature library: papers kept across runs in one SQLite file.

A search produces a ``PaperCollection`` that is gone when the process ends.
:class:`Library` keeps what the runs found: the papers, which run and source
saw each one and how it scored, the citation links between them, and the
export preflight's verdict on their DOIs and URLs.

An import is a merge, never a blind append. A paper is recognised by the same
identity keys search de-duplication uses (:meth:`Paper.identity_keys`: DOI,
arXiv ID, title hash) and by the same rules (``dedup.fuzzy_link_allowed``,
``dedup.merge_papers``), so adding the same search twice leaves the paper
count unchanged and only records a second sighting.

SQLite because it ships with Python, is transactional and needs no server.
The schema, its version and its migrations live in :mod:`.schema`.

Example::

    with Library("thesis.db") as library:
        report = library.add_collection(collection)      # merge a search in
        hits = library.search("graph neural network", limit=10)
        cache = library.verification_cache()             # for export_collection
"""

from __future__ import annotations

import json
import sqlite3
import threading
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from thesisagents.core.dedup import (
    FUZZY_KEY_PREFIX,
    fuzzy_link_allowed,
    merge_papers,
)
from thesisagents.core.diagnostics import (
    PaperRelation,
    PaperScore,
    RelationKind,
    RelevanceScore,
    SearchDiagnostics,
)
from thesisagents.core.exceptions import LibraryError
from thesisagents.core.export_validation import Verdict, VerificationStatus
from thesisagents.core.models import FieldProvenance, Paper, PaperCollection, Query
from thesisagents.core.pruning import recommend_pruning
from thesisagents.core.ranking import RankedPaper, rank_with_scores
from thesisagents.library.schema import prepare, transaction
from thesisagents.utils.path_safety import resolve_library_path

#: How long a second process waits for another one's write to finish before
#: giving up with "database is locked". An import takes well under a second,
#: so half a minute only runs out when something is stuck.
BUSY_TIMEOUT_SECONDS: float = 30.0

#: How long a DOI or URL that was verified stays verified. Links do rot, and
#: a thesis is written over months, so "checked once" must not mean "checked
#: forever": after a month the export preflight asks again. Only verdicts that
#: let an export through are reused at all, see :class:`LibraryVerificationCache`.
VERIFIED_FOR: timedelta = timedelta(days=30)

#: The ``sources`` entry of the query a library export is built with. A
#: ``Query`` needs at least one source and a library is not one of the search
#: sources, so exports name where the papers came from this way.
LIBRARY_SOURCE: str = "library"

#: Kinds of run, recorded with each import so the history says how a paper
#: got in.
RUN_SEARCH: str = "search"
RUN_MANUAL: str = "manual"

_CITATION_FIELD = "citation_count"


@dataclass(frozen=True, slots=True)
class AddReport:
    """What one import changed.

    ``added`` and ``merged`` sum to the number of papers handed in.
    ``relations_skipped`` counts citation links whose other end is not in the
    library, which cannot be stored because a link needs two papers.
    """

    run_id: int
    added: int
    merged: int
    relations_added: int
    relations_skipped: int
    total: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "added": self.added,
            "merged": self.merged,
            "relations_added": self.relations_added,
            "relations_skipped": self.relations_skipped,
            "total": self.total,
        }


@dataclass(frozen=True, slots=True)
class LibraryEntry:
    """One stored paper with what the library knows about its history.

    ``sources`` lists every search source that returned the paper in any run,
    which is the run-level counterpart of the field-level ``Paper.provenance``.
    ``score`` is set by :meth:`Library.search` when a query was given.
    """

    paper: Paper
    first_seen: str
    last_seen: str
    times_seen: int
    sources: tuple[str, ...] = ()
    score: RelevanceScore | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "paper": self.paper.to_dict(),
            "first_seen": self.first_seen,
            "last_seen": self.last_seen,
            "times_seen": self.times_seen,
            "sources": list(self.sources),
            "score": None if self.score is None else self.score.to_dict(),
        }


@dataclass(frozen=True, slots=True)
class LibraryRun:
    """One import: when it ran, what was asked, and what each source returned."""

    run_id: int
    started_at: str
    kind: str
    keywords: str
    papers: int
    query: Mapping[str, Any]
    source_stats: tuple[Mapping[str, Any], ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "started_at": self.started_at,
            "kind": self.kind,
            "keywords": self.keywords,
            "papers": self.papers,
            "query": dict(self.query),
            "source_stats": [dict(stat) for stat in self.source_stats],
        }


@dataclass(frozen=True, slots=True)
class LibraryStats:
    """Size and coverage of a library, for a one-screen summary.

    ``sources`` counts the papers each source has returned (a paper returned
    by two sources counts once for each). ``verifications`` counts the stored
    DOI / URL verdicts by status.
    """

    path: str
    schema_version: int
    papers: int
    runs: int
    relations: int
    year_min: int | None
    year_max: int | None
    first_run: str | None
    last_run: str | None
    sources: Mapping[str, int]
    verifications: Mapping[str, int]

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "schema_version": self.schema_version,
            "papers": self.papers,
            "runs": self.runs,
            "relations": self.relations,
            "year_min": self.year_min,
            "year_max": self.year_max,
            "first_run": self.first_run,
            "last_run": self.last_run,
            "sources": dict(self.sources),
            "verifications": dict(self.verifications),
        }


class Library:
    """A literature library in one SQLite file. See the module docstring.

    ``create=False`` refuses a path that does not exist. Reads use it so that a
    mistyped ``--library`` path says "no library there" instead of quietly
    creating an empty one and reporting no results.

    One object owns one connection, guarded by a lock, so it can be handed to
    code that runs on another thread (the export preflight does). Separate
    processes each open their own ``Library``: the file is in WAL mode, where
    readers do not block a writer and a writer does not block readers.

    ``now`` pins the clock for tests.
    """

    def __init__(
        self,
        path: str | Path,
        *,
        create: bool = True,
        now: Callable[[], datetime] | None = None,
    ) -> None:
        try:
            self._path = resolve_library_path(path)
        except ValueError as err:
            raise LibraryError(str(err)) from err
        self._now = now if now is not None else _utc_now
        self._lock = threading.RLock()
        if not self._path.exists():
            if not create:
                raise LibraryError(
                    f"no library at {self._path}. A library is created the "
                    "first time papers are added to it (--library-add, or the "
                    "library_add tool)."
                )
            self._path.parent.mkdir(parents=True, exist_ok=True)
        try:
            self._conn = sqlite3.connect(
                self._path,
                isolation_level=None,          # autocommit: see schema.transaction
                check_same_thread=False,       # guarded by self._lock instead
                timeout=BUSY_TIMEOUT_SECONDS,
            )
        except sqlite3.Error as err:
            raise LibraryError(f"cannot open the library at {self._path}: {err}") from err
        try:
            self._version = prepare(self._conn, str(self._path))
            self._conn.execute("PRAGMA foreign_keys = ON")
            # WAL lets other processes read while this one writes. Where the
            # filesystem cannot do it (some network drives) SQLite keeps the
            # default journal and the library still works, one user at a time.
            self._conn.execute("PRAGMA journal_mode = WAL")
        except sqlite3.Error as err:
            self._conn.close()
            raise LibraryError(f"cannot use the library at {self._path}: {err}") from err
        except LibraryError:
            self._conn.close()
            raise

    # ------------------------------------------------------------ lifecycle

    @property
    def path(self) -> Path:
        return self._path

    @property
    def schema_version(self) -> int:
        return self._version

    def close(self) -> None:
        """Release the file. Safe to call twice."""
        with self._lock:
            self._conn.close()

    def __enter__(self) -> Library:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()

    def __len__(self) -> int:
        with self._lock:
            return int(self._conn.execute("SELECT count(*) FROM papers").fetchone()[0])

    # --------------------------------------------------------------- writes

    def add_collection(
        self, collection: PaperCollection, *, kind: str = RUN_SEARCH
    ) -> AddReport:
        """Merge a search result into the library and record the run.

        Everything the collection knows goes in: the papers, the query, what
        each source returned, each paper's rank, score and pruning
        recommendation, and the citation links found by snowballing.

        Example: adding the same collection twice reports ``added=N, merged=0``
        and then ``added=0, merged=N``, with two runs and N papers stored.
        """
        diagnostics = collection.diagnostics
        return self._import(
            collection.papers,
            kind=kind,
            keywords=collection.query.keywords,
            query=_query_record(collection.query),
            diagnostics=diagnostics,
            relations=diagnostics.relations if diagnostics is not None else (),
        )

    def add_papers(
        self,
        papers: Iterable[Paper],
        *,
        keywords: str = "",
        kind: str = RUN_MANUAL,
        relations: Iterable[PaperRelation] = (),
    ) -> AddReport:
        """Merge papers that did not come from ``run_search``.

        For a caller that holds papers and nothing else: the MCP
        ``library_add`` tool, a script. ``relations`` are citation links
        between papers, named by ``Paper.dedup_key()`` as ``snowball`` returns
        them. A link is stored when both of its papers are in the library
        after this import, whether they arrived now or earlier.
        """
        return self._import(
            tuple(papers),
            kind=kind,
            keywords=keywords,
            query={"keywords": keywords},
            diagnostics=None,
            relations=tuple(relations),
        )

    def _import(
        self,
        papers: Iterable[Paper],
        *,
        kind: str,
        keywords: str,
        query: Mapping[str, Any],
        diagnostics: SearchDiagnostics | None,
        relations: Iterable[PaperRelation],
    ) -> AddReport:
        stamp = self._stamp()
        scores = {entry.paper_key: entry for entry in diagnostics.scores} if diagnostics else {}
        advice = {entry.paper_key: entry for entry in diagnostics.pruning} if diagnostics else {}
        stats = [stat.to_dict() for stat in diagnostics.source_stats] if diagnostics else []
        added = merged = 0
        ids_by_key: dict[str, int] = {}
        with self._lock, transaction(self._conn):
            run_id = self._conn.execute(
                "INSERT INTO runs (started_at, kind, keywords, query, source_stats) "
                "VALUES (?, ?, ?, ?, ?)",
                (stamp, kind, keywords, _dump(query), _dump(stats)),
            ).lastrowid
            for paper in papers:
                paper_id, is_new = self._upsert(paper, stamp)
                added += is_new
                merged += not is_new
                key = paper.dedup_key()
                ids_by_key[key] = paper_id
                score = scores.get(key)
                recommendation = advice.get(key)
                self._conn.execute(
                    "INSERT OR IGNORE INTO observations "
                    "(run_id, paper_id, source, source_id, rank, score, recommendation) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (
                        run_id,
                        paper_id,
                        paper.source,
                        paper.source_id,
                        score.rank if score else None,
                        _dump(score.score.to_dict()) if score else None,
                        _dump(recommendation.to_dict()) if recommendation else None,
                    ),
                )
            linked, skipped = self._store_relations(relations, ids_by_key, run_id)
            total = int(self._conn.execute("SELECT count(*) FROM papers").fetchone()[0])
        return AddReport(
            run_id=int(run_id),
            added=added,
            merged=merged,
            relations_added=linked,
            relations_skipped=skipped,
            total=total,
        )

    def _upsert(self, paper: Paper, stamp: str) -> tuple[int, bool]:
        """Store ``paper`` or merge it into the stored paper it is. Returns ``(id, is_new)``.

        The same matching as ``dedup.IdentityIndex.add``, against rows instead
        of a list: every identity key is looked up, a title-hash match is
        subject to the conflicting-DOI guard, and a paper that matches two
        stored papers (it carries the DOI of one and the arXiv ID of the
        other) joins them into one.
        """
        matches: set[int] = set()
        for key in paper.identity_keys():
            row = self._conn.execute(
                "SELECT paper_id FROM identity_keys WHERE key = ?", (key,)
            ).fetchone()
            if row is None:
                continue
            if key.startswith(FUZZY_KEY_PREFIX) and not fuzzy_link_allowed(
                self._load(row[0]), paper
            ):
                continue
            matches.add(int(row[0]))
        if not matches:
            paper_id = int(
                self._conn.execute(
                    "INSERT INTO papers (record, title, year, first_seen, last_seen) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (_dump(paper.to_dict()), paper.title, paper.year, stamp, stamp),
                ).lastrowid
            )
            self._claim_keys(paper_id, paper)
            return paper_id, True
        paper_id = min(matches)
        stored = self._load(paper_id)
        for absorbed in sorted(matches - {paper_id}):
            stored = merge_papers(stored, self._load(absorbed))
            self._absorb(absorbed, paper_id)
        stored = _with_latest_citations(merge_papers(stored, paper), paper)
        self._conn.execute(
            "UPDATE papers SET record = ?, title = ?, year = ?, last_seen = ? WHERE id = ?",
            (_dump(stored.to_dict()), stored.title, stored.year, stamp, paper_id),
        )
        # Both the incoming record's keys and the merged record's: the merge
        # can give the stored paper a DOI or a year it did not have, and with
        # them keys neither record carried alone.
        self._claim_keys(paper_id, paper)
        self._claim_keys(paper_id, stored)
        return paper_id, False

    def _claim_keys(self, paper_id: int, paper: Paper) -> None:
        # OR IGNORE: a key already owned by another paper was refused by the
        # conflict guard, so it stays with its owner.
        self._conn.executemany(
            "INSERT OR IGNORE INTO identity_keys (key, paper_id) VALUES (?, ?)",
            [(key, paper_id) for key in paper.identity_keys()],
        )

    def _absorb(self, absorbed: int, survivor: int) -> None:
        """Fold the row ``absorbed`` into ``survivor``: keys, sightings, links."""
        conn = self._conn
        conn.execute(
            "UPDATE identity_keys SET paper_id = ? WHERE paper_id = ?", (survivor, absorbed)
        )
        conn.execute(
            "INSERT OR IGNORE INTO observations "
            "(run_id, paper_id, source, source_id, rank, score, recommendation) "
            "SELECT run_id, ?, source, source_id, rank, score, recommendation "
            "FROM observations WHERE paper_id = ?",
            (survivor, absorbed),
        )
        conn.execute(
            "INSERT OR IGNORE INTO relations "
            "(source_id, target_id, relation, provider, depth, run_id) "
            "SELECT CASE WHEN source_id = ?1 THEN ?2 ELSE source_id END, "
            "CASE WHEN target_id = ?1 THEN ?2 ELSE target_id END, "
            "relation, provider, depth, run_id "
            "FROM relations WHERE source_id = ?1 OR target_id = ?1",
            (absorbed, survivor),
        )
        # Two papers that cited each other and turned out to be one paper.
        conn.execute("DELETE FROM relations WHERE source_id = target_id")
        conn.execute(
            "UPDATE papers SET first_seen = min(first_seen, "
            "(SELECT first_seen FROM papers WHERE id = ?)) WHERE id = ?",
            (absorbed, survivor),
        )
        # Cascades to what is left of the absorbed row's sightings and links.
        conn.execute("DELETE FROM papers WHERE id = ?", (absorbed,))

    def _store_relations(
        self,
        relations: Iterable[PaperRelation],
        ids_by_key: Mapping[str, int],
        run_id: int,
    ) -> tuple[int, int]:
        linked = skipped = 0
        for relation in relations:
            source = self._paper_id(relation.source_key, ids_by_key)
            target = self._paper_id(relation.target_key, ids_by_key)
            if source is None or target is None or source == target:
                skipped += 1
                continue
            cursor = self._conn.execute(
                "INSERT OR IGNORE INTO relations "
                "(source_id, target_id, relation, provider, depth, run_id) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (
                    source,
                    target,
                    RelationKind(relation.relation).value,
                    relation.provider,
                    relation.depth,
                    run_id,
                ),
            )
            linked += cursor.rowcount
        return linked, skipped

    def _paper_id(self, key: str, ids_by_key: Mapping[str, int]) -> int | None:
        known = ids_by_key.get(key)
        if known is not None:
            # A later paper of the same import may have absorbed this row.
            alive = self._conn.execute(
                "SELECT 1 FROM papers WHERE id = ?", (known,)
            ).fetchone()
            if alive is not None:
                return known
        row = self._conn.execute(
            "SELECT paper_id FROM identity_keys WHERE key = ?", (key,)
        ).fetchone()
        return None if row is None else int(row[0])

    def _load(self, paper_id: int) -> Paper:
        row = self._conn.execute(
            "SELECT record FROM papers WHERE id = ?", (paper_id,)
        ).fetchone()
        return Paper.from_dict(json.loads(row[0]))

    # ---------------------------------------------------------------- reads

    def entries(
        self, *, year_from: int | None = None, year_to: int | None = None
    ) -> list[LibraryEntry]:
        """Every stored paper, most recently seen first."""
        with self._lock:
            rows = self._conn.execute(
                "SELECT p.record, p.first_seen, p.last_seen, "
                "(SELECT count(*) FROM observations o WHERE o.paper_id = p.id), "
                "(SELECT group_concat(DISTINCT o.source) FROM observations o "
                " WHERE o.paper_id = p.id) "
                "FROM papers p "
                "WHERE (?1 IS NULL OR p.year >= ?1) AND (?2 IS NULL OR p.year <= ?2) "
                "ORDER BY p.last_seen DESC, p.id",
                (year_from, year_to),
            ).fetchall()
        return [
            LibraryEntry(
                paper=Paper.from_dict(json.loads(record)),
                first_seen=first_seen,
                last_seen=last_seen,
                times_seen=int(times_seen),
                sources=tuple(sorted(sources.split(","))) if sources else (),
            )
            for record, first_seen, last_seen, times_seen, sources in rows
        ]

    def search(
        self,
        query: str = "",
        *,
        limit: int | None = 50,
        year_from: int | None = None,
        year_to: int | None = None,
    ) -> list[LibraryEntry]:
        """Stored papers that match ``query``, best first. No network.

        Scored by the search ranker (``rank_with_scores``), so a library
        lookup understands a query the way a search does: stemming, phrases,
        acronyms, CJK text. Only papers that match at least one query term
        are returned, each with its score.

        An empty ``query`` lists the library, most recently seen first.
        ``limit=None`` returns every match.

        Example: ``library.search("graph neural network", limit=5)``.
        """
        if limit is not None and limit < 1:
            raise ValueError("limit must be at least 1")
        entries = self.entries(year_from=year_from, year_to=year_to)
        if not query.strip():
            return entries[:limit]
        by_identity = {id(entry.paper): entry for entry in entries}
        matched = [
            replace(by_identity[id(ranked.paper)], score=ranked.score)
            for ranked in rank_with_scores([entry.paper for entry in entries], query)
            if ranked.score.relevance > 0
        ]
        return matched[:limit]

    def collection(
        self,
        query: str = "",
        *,
        limit: int | None = None,
        year_from: int | None = None,
        year_to: int | None = None,
    ) -> PaperCollection:
        """The library, or the part matching ``query``, as a ``PaperCollection``.

        This is how stored papers reach the exporters. The citation links
        between the returned papers come along in ``diagnostics.relations``.
        With a ``query``, so do each paper's score against it and the same
        advisory pruning recommendations a search gives.
        """
        entries = self.search(query, limit=limit, year_from=year_from, year_to=year_to)
        papers = tuple(entry.paper for entry in entries)
        keys = {paper.dedup_key() for paper in papers}
        links = tuple(
            relation
            for relation in self.relations()
            if relation.source_key in keys and relation.target_key in keys
        )
        ranked = [
            RankedPaper(paper=entry.paper, score=entry.score, rank=position)
            for position, entry in enumerate(entries, start=1)
            if entry.score is not None
        ]
        return PaperCollection(
            query=Query(
                keywords=query.strip() or LIBRARY_SOURCE,
                sources=(LIBRARY_SOURCE,),
                max_results=Query.clamp_max_results(len(papers)),
            ),
            papers=papers,
            diagnostics=SearchDiagnostics(
                scores=tuple(
                    PaperScore(entry.paper.dedup_key(), entry.rank, entry.score)
                    for entry in ranked
                ),
                pruning=recommend_pruning(ranked),
                relations=links,
            ),
        )

    def relations(self) -> tuple[PaperRelation, ...]:
        """Every stored citation link, named by its papers' ``dedup_key()``."""
        with self._lock:
            keys = {
                int(paper_id): Paper.from_dict(json.loads(record)).dedup_key()
                for paper_id, record in self._conn.execute("SELECT id, record FROM papers")
            }
            rows = self._conn.execute(
                "SELECT source_id, target_id, relation, provider, depth "
                "FROM relations ORDER BY source_id, target_id, relation"
            ).fetchall()
        return tuple(
            PaperRelation(
                source_key=keys[source],
                target_key=keys[target],
                relation=RelationKind(relation),
                provider=provider,
                depth=int(depth),
            )
            for source, target, relation, provider, depth in rows
        )

    def runs(self) -> list[LibraryRun]:
        """Every import, newest first."""
        with self._lock:
            rows = self._conn.execute(
                "SELECT r.id, r.started_at, r.kind, r.keywords, r.query, r.source_stats, "
                "(SELECT count(*) FROM observations o WHERE o.run_id = r.id) "
                "FROM runs r ORDER BY r.id DESC"
            ).fetchall()
        return [
            LibraryRun(
                run_id=int(run_id),
                started_at=started_at,
                kind=kind,
                keywords=keywords,
                papers=int(papers),
                query=json.loads(query),
                source_stats=tuple(json.loads(source_stats)),
            )
            for run_id, started_at, kind, keywords, query, source_stats, papers in rows
        ]

    def stats(self) -> LibraryStats:
        """Counts for a one-screen summary of the library."""
        with self._lock:
            conn = self._conn
            papers, year_min, year_max = conn.execute(
                "SELECT count(*), min(year), max(year) FROM papers"
            ).fetchone()
            runs, first_run, last_run = conn.execute(
                "SELECT count(*), min(started_at), max(started_at) FROM runs"
            ).fetchone()
            relations = conn.execute("SELECT count(*) FROM relations").fetchone()[0]
            sources = dict(
                conn.execute(
                    "SELECT source, count(DISTINCT paper_id) FROM observations "
                    "GROUP BY source ORDER BY source"
                ).fetchall()
            )
            verifications = dict(
                conn.execute(
                    "SELECT status, count(*) FROM verifications GROUP BY status ORDER BY status"
                ).fetchall()
            )
        return LibraryStats(
            path=str(self._path),
            schema_version=self._version,
            papers=int(papers),
            runs=int(runs),
            relations=int(relations),
            year_min=year_min,
            year_max=year_max,
            first_run=first_run,
            last_run=last_run,
            sources=sources,
            verifications=verifications,
        )

    # --------------------------------------------------- verification cache

    def verification_cache(self) -> LibraryVerificationCache:
        """A ``VerificationCache`` for ``export_collection`` backed by this library."""
        return LibraryVerificationCache(self)

    def stored_verdict(self, kind: str, value: str) -> tuple[Verdict, datetime] | None:
        """The last recorded verdict on an identifier and when it was reached."""
        with self._lock:
            row = self._conn.execute(
                "SELECT status, resolved_url, detail, checked_at FROM verifications "
                "WHERE kind = ? AND value = ?",
                (kind, value),
            ).fetchone()
        if row is None:
            return None
        status, resolved_url, detail, checked_at = row
        return (
            Verdict(VerificationStatus(status), resolved_url, detail),
            datetime.fromisoformat(checked_at),
        )

    def record_verdict(self, kind: str, value: str, verdict: Verdict) -> None:
        """Record the latest verdict on an identifier, replacing the previous one."""
        with self._lock:
            self._conn.execute(
                "INSERT INTO verifications (kind, value, status, resolved_url, detail, checked_at) "
                "VALUES (?, ?, ?, ?, ?, ?) "
                "ON CONFLICT (kind, value) DO UPDATE SET status = excluded.status, "
                "resolved_url = excluded.resolved_url, detail = excluded.detail, "
                "checked_at = excluded.checked_at",
                (
                    kind,
                    value,
                    verdict.status.value,
                    verdict.resolved_url,
                    verdict.detail,
                    self._stamp(),
                ),
            )

    def now(self) -> datetime:
        return self._now()

    def _stamp(self) -> str:
        return self._now().astimezone(UTC).isoformat(timespec="seconds")


class LibraryVerificationCache:
    """The export preflight's memory, kept in the library between runs.

    Implements ``core.export_validation.VerificationCache``.

    The boundary this guards: a verdict reached in one run being trusted in a
    later one. Only a verdict that lets an export through crosses that
    boundary: a DOI or URL that verified (``ok``), or one that cannot be
    checked without a browser (``skipped``), is not asked about again for
    :data:`VERIFIED_FOR`. A failure is recorded (it shows in the library's
    statistics) and never reused, because a failed check stops an export:
    reusing a timeout from last week would keep failing the export after the
    network came back, with no request made that could ever clear it.

    Within one object, every verdict is reused, failures included, so a run
    that exports twenty decks asks about each identifier once.

    Example::

        with Library("thesis.db") as library:
            export_collection(
                collection, options, verification_cache=library.verification_cache()
            )
    """

    def __init__(self, library: Library) -> None:
        self._library = library
        self._this_run: dict[tuple[str, str], Verdict] = {}

    def get(self, kind: str, value: str) -> Verdict | None:
        seen = self._this_run.get((kind, value))
        if seen is not None:
            return seen
        stored = self._library.stored_verdict(kind, value)
        if stored is None:
            return None
        verdict, checked_at = stored
        if verdict.blocking:
            return None
        if self._library.now() - checked_at > VERIFIED_FOR:
            return None
        return verdict

    def put(self, kind: str, value: str, verdict: Verdict) -> None:
        self._this_run[(kind, value)] = verdict
        self._library.record_verdict(kind, value, verdict)


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _dump(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _query_record(query: Query) -> dict[str, Any]:
    return {
        "keywords": query.keywords,
        "sources": list(query.sources),
        "max_results": query.max_results,
        "year_from": query.year_from,
        "year_to": query.year_to,
        "min_citations": query.min_citations,
        "top_tier_only": query.top_tier_only,
    }


def _with_latest_citations(stored: Paper, incoming: Paper) -> Paper:
    """Take the incoming citation count when it is higher than the stored one.

    The one place the library departs from ``merge_papers``, which keeps the
    first non-empty value of every field. That rule is right inside one
    search, where all records are equally fresh. Across months it would
    freeze the count at whatever the first run saw, and a citation table in a
    thesis would then quote a number that is a year old.

    Counts only grow, so the higher one is the more recent (or the more
    complete source). The provenance entry for the field is replaced, not
    appended, so repeated imports do not grow the record.

    Example: stored 120 (from ``crossref``), incoming 180 (from ``openalex``)
    gives 180 with ``FieldProvenance("citation_count", "openalex", "W…")``.
    """
    if incoming.citation_count is None:
        return stored
    if stored.citation_count is not None and incoming.citation_count <= stored.citation_count:
        return stored
    provenance = tuple(
        entry for entry in stored.provenance if entry.field != _CITATION_FIELD
    )
    if (incoming.source, incoming.source_id) != (stored.source, stored.source_id):
        provenance += (
            FieldProvenance(_CITATION_FIELD, incoming.source, incoming.source_id),
        )
    return replace(stored, citation_count=incoming.citation_count, provenance=provenance)
