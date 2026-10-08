"""The literature library: merging imports, history, links, the verdict cache, the schema."""

from __future__ import annotations

import sqlite3
import threading
from datetime import UTC, datetime, timedelta

import pytest

from thesisagents.core.diagnostics import (
    PaperRelation,
    PaperScore,
    PruningAction,
    PruningRecommendation,
    RelationKind,
    RelevanceScore,
    SearchDiagnostics,
    SourceStat,
)
from thesisagents.core.exceptions import LibraryError
from thesisagents.core.export_validation import (
    KIND_DOI,
    KIND_URL,
    Verdict,
    VerificationStatus,
    verify_collection_blocking,
)
from thesisagents.core.models import Paper, PaperCollection, PaperSummary, Query
from thesisagents.library import (
    LIBRARY_SOURCE,
    SCHEMA_VERSION,
    VERIFIED_FOR,
    Library,
    schema,
)


def _paper(source_id: str, title: str, **fields) -> Paper:
    defaults = {
        "source": "arxiv",
        "authors": ("Ada Lovelace",),
        "year": 2024,
        "venue": None,
        "abstract": "",
        "url": f"https://example.org/{source_id}",
    }
    defaults.update(fields)
    return Paper(source_id=source_id, title=title, **defaults)


GNN_ARXIV = _paper(
    "2401.00001", "Graph Neural Networks for Molecules",
    abstract="We study graph neural networks for molecular property prediction.",
    arxiv_id="2401.00001",
)
GNN_OPENALEX = _paper(
    "W1", "Graph neural networks for molecules.", source="openalex",
    authors=("Lovelace, Ada",), venue="NeurIPS", doi="10.1000/gnn", citation_count=12,
)
FOLDING = _paper(
    "10.1000/fold", "Protein Folding with Attention", source="crossref",
    authors=("Alan Turing",), year=2021, venue="Nature",
    abstract="Attention models for protein structure.", doi="10.1000/fold",
    citation_count=900,
)


def _collection(*papers: Paper, keywords: str = "graph neural network", **kwargs):
    return PaperCollection(Query(keywords, ("arxiv",)), tuple(papers), **kwargs)


def _link(source: Paper, target: Paper, relation=RelationKind.REFERENCES) -> PaperRelation:
    return PaperRelation(source.dedup_key(), target.dedup_key(), relation, "openalex", 1)


@pytest.fixture()
def path(tmp_path):
    return tmp_path / "thesis.db"


# --------------------------------------------------------- add / search


def test_add_then_search_round_trip(path):
    with Library(path) as library:
        report = library.add_collection(_collection(GNN_ARXIV, FOLDING))
        assert (report.added, report.merged, report.total) == (2, 0, 2)

    with Library(path, create=False) as library:      # a new process
        found = library.search("graph neural network")

    assert [entry.paper for entry in found] == [GNN_ARXIV]
    assert found[0].score.relevance > 0
    assert found[0].times_seen == 1
    assert found[0].sources == ("arxiv",)


def test_search_returns_only_papers_matching_the_query(path):
    with Library(path) as library:
        library.add_collection(_collection(GNN_ARXIV, FOLDING))
        assert library.search("quantum chromodynamics") == []
        assert [e.paper.title for e in library.search("attention")] == [FOLDING.title]


def test_empty_query_lists_the_library_most_recently_seen_first(path):
    clock = _Clock()
    with Library(path, now=clock) as library:
        library.add_papers([GNN_ARXIV])
        clock.advance(hours=1)
        library.add_papers([FOLDING])
        listed = library.search("")
    assert [entry.paper.title for entry in listed] == [FOLDING.title, GNN_ARXIV.title]
    assert listed[0].score is None


def test_search_honours_limit_and_year_range(path):
    with Library(path) as library:
        library.add_papers([GNN_ARXIV, FOLDING])
        assert len(library.search("", limit=1)) == 1
        assert [e.paper.year for e in library.search("", year_to=2022)] == [2021]
        assert [e.paper.year for e in library.search("", year_from=2023)] == [2024]
        with pytest.raises(ValueError, match="limit must be at least 1"):
            library.search("", limit=0)


def test_a_paper_keeps_its_summary(path):
    summary = PaperSummary(language="en", motivation=("Why it matters",))
    with Library(path) as library:
        library.add_papers([_paper("s1", "Summarised", summary=summary)])
    with Library(path) as library:
        assert library.search("")[0].paper.summary.motivation == ("Why it matters",)


# ------------------------------------------------- merge, never duplicate


def test_repeated_add_is_idempotent_on_identity(path):
    with Library(path) as library:
        first = library.add_collection(_collection(GNN_ARXIV, FOLDING))
        second = library.add_collection(_collection(GNN_ARXIV, FOLDING))
        assert (first.added, first.merged) == (2, 0)
        assert (second.added, second.merged) == (0, 2)
        assert second.total == len(library) == 2
        assert len(library.runs()) == 2
        assert [entry.times_seen for entry in library.search("")] == [2, 2]


def test_the_same_paper_from_two_sources_is_one_paper(path):
    with Library(path) as library:
        library.add_papers([GNN_ARXIV])
        report = library.add_papers([GNN_OPENALEX])     # same title, author, year
        assert (report.added, report.merged, report.total) == (0, 1, 1)
        stored = library.search("")[0].paper

    # The first record stays canonical and gains what the second one knew.
    assert (stored.source, stored.url) == ("arxiv", GNN_ARXIV.url)
    assert (stored.doi, stored.venue, stored.arxiv_id) == ("10.1000/gnn", "NeurIPS", "2401.00001")


def test_provenance_from_multiple_sources_is_retained(path):
    with Library(path) as library:
        library.add_papers([GNN_ARXIV])
        library.add_papers([GNN_OPENALEX])
    with Library(path) as library:
        entry = library.search("")[0]

    # Run level: every source that returned the paper.
    assert entry.sources == ("arxiv", "openalex")
    # Field level: which source supplied each backfilled field.
    supplied = {(p.field, p.source, p.source_id) for p in entry.paper.provenance}
    assert supplied == {
        ("doi", "openalex", "W1"),
        ("venue", "openalex", "W1"),
        ("citation_count", "openalex", "W1"),
    }


def test_a_backfilled_identifier_is_recognised_by_later_imports(path):
    doi_only = _paper("D1", "A Different Title Entirely", source="crossref", doi="10.1000/gnn")
    with Library(path) as library:
        library.add_papers([GNN_ARXIV])
        library.add_papers([GNN_OPENALEX])              # gives the stored paper its DOI
        report = library.add_papers([doi_only])         # matches on that DOI alone
        assert (report.added, report.total) == (0, 1)


def test_a_paper_bridging_two_stored_papers_joins_them(path):
    by_arxiv = _paper("2401.00009", "Preprint Title", arxiv_id="2401.00009")
    by_doi = _paper("10.1000/j", "Journal Title", source="crossref", doi="10.1000/j", year=2025)
    bridge = _paper(
        "W9", "Journal Title (Extended)", source="openalex",
        doi="10.1000/j", arxiv_id="2401.00009", year=2025,
    )
    link = _link(by_arxiv, FOLDING)
    with Library(path) as library:
        library.add_papers([by_arxiv, by_doi, FOLDING], relations=[link])
        assert len(library) == 3
        report = library.add_papers([bridge])
        assert (report.added, report.merged, report.total) == (0, 1, 2)
        merged = next(e for e in library.search("") if e.paper.arxiv_id)
        relations = library.relations()

    assert (merged.paper.doi, merged.paper.arxiv_id) == ("10.1000/j", "2401.00009")
    assert merged.times_seen == 2                      # both runs that saw either half
    # The link of the absorbed row now starts at the surviving paper.
    assert [(r.source_key, r.target_key) for r in relations] == [
        ("doi:10.1000/j", FOLDING.dedup_key())
    ]


def test_same_title_with_conflicting_dois_stays_two_papers(path):
    workshop = _paper("W", "Robust Widgets", source="crossref", doi="10.1000/workshop")
    journal = _paper("J", "Robust Widgets", source="crossref", doi="10.1000/journal")
    with Library(path) as library:
        report = library.add_papers([workshop, journal])
        assert (report.added, report.total) == (2, 2)


def test_duplicates_inside_one_import_are_merged(path):
    with Library(path) as library:
        report = library.add_papers([GNN_ARXIV, GNN_OPENALEX])
        assert (report.added, report.merged, report.total) == (1, 1, 1)


def test_citation_count_follows_the_higher_later_value(path):
    stale = _paper("C", "Counted", source="crossref", doi="10.1000/c", citation_count=120)
    fresh = _paper("W", "Counted", source="openalex", doi="10.1000/c", citation_count=180)
    lower = _paper("S", "Counted", source="semantic_scholar", doi="10.1000/c", citation_count=90)
    with Library(path) as library:
        for paper in (stale, fresh, lower, fresh):
            library.add_papers([paper])
        stored = library.search("")[0].paper

    assert stored.citation_count == 180
    # Replaced, not appended: one provenance entry however often it is refreshed.
    assert [(p.source, p.source_id) for p in stored.provenance if p.field == "citation_count"] == [
        ("openalex", "W")
    ]


# ------------------------------------------------- runs and observations


def test_a_run_records_the_query_the_sources_and_each_score(path):
    score = RelevanceScore(total=5.5, relevance=4.0, recency=1.0, citation=0.5)
    diagnostics = SearchDiagnostics(
        scores=(PaperScore(GNN_ARXIV.dedup_key(), 1, score),),
        pruning=(PruningRecommendation(GNN_ARXIV.dedup_key(), 1, PruningAction.KEEP),),
        source_stats=(SourceStat("arxiv", requested=25, returned=1, after_dedup=1),),
    )
    with Library(path) as library:
        library.add_collection(_collection(GNN_ARXIV, diagnostics=diagnostics))
        run = library.runs()[0]
        row = library._conn.execute(
            "SELECT source, source_id, rank, score, recommendation FROM observations"
        ).fetchone()

    assert (run.kind, run.keywords, run.papers) == ("search", "graph neural network", 1)
    assert run.query["sources"] == ["arxiv"]
    assert run.source_stats[0]["returned"] == 1
    assert row[:3] == ("arxiv", "2401.00001", 1)
    assert '"total": 5.5' in row[3]
    assert '"action": "keep"' in row[4]


def test_stats_summarise_the_library(path):
    with Library(path) as library:
        library.add_collection(_collection(GNN_ARXIV, FOLDING))
        library.add_papers([GNN_OPENALEX])
        library.record_verdict(KIND_DOI, "10.1000/gnn", Verdict(VerificationStatus.OK))
        library.record_verdict(KIND_URL, "https://x.test", Verdict(VerificationStatus.TIMEOUT))
        stats = library.stats().to_dict()

    assert stats["papers"] == 2
    assert stats["runs"] == 2
    assert (stats["year_min"], stats["year_max"]) == (2021, 2024)
    assert stats["sources"] == {"arxiv": 1, "crossref": 1, "openalex": 1}
    assert stats["verifications"] == {"ok": 1, "timeout": 1}
    assert stats["schema_version"] == SCHEMA_VERSION


# -------------------------------------------------------------- relations


def test_citation_relations_survive_restart(path):
    link = _link(GNN_ARXIV, FOLDING)
    with Library(path) as library:
        report = library.add_collection(
            _collection(GNN_ARXIV, FOLDING, diagnostics=SearchDiagnostics(relations=(link,)))
        )
        assert (report.relations_added, report.relations_skipped) == (1, 0)

    with Library(path, create=False) as library:
        assert library.relations() == (link,)
        assert library.stats().relations == 1


def test_a_relation_is_stored_once(path):
    link = _link(GNN_ARXIV, FOLDING, RelationKind.CITED_BY)
    with Library(path) as library:
        library.add_papers([GNN_ARXIV, FOLDING], relations=[link])
        again = library.add_papers([GNN_ARXIV, FOLDING], relations=[link])
        assert again.relations_added == 0
        assert len(library.relations()) == 1


def test_a_relation_to_a_paper_outside_the_library_is_skipped_and_counted(path):
    dangling = PaperRelation(
        GNN_ARXIV.dedup_key(), "doi:10.9999/unknown", RelationKind.REFERENCES, "openalex", 1
    )
    with Library(path) as library:
        report = library.add_papers([GNN_ARXIV], relations=[dangling])
        assert (report.relations_added, report.relations_skipped) == (0, 1)


def test_a_relation_may_point_at_a_paper_stored_earlier(path):
    link = _link(GNN_ARXIV, FOLDING)
    with Library(path) as library:
        library.add_papers([FOLDING])
        report = library.add_papers([GNN_ARXIV], relations=[link])
        assert report.relations_added == 1


# -------------------------------------------------------------- collection


def test_collection_is_ready_for_the_exporters(path):
    link = _link(GNN_ARXIV, FOLDING)
    with Library(path) as library:
        library.add_papers([GNN_ARXIV, FOLDING], relations=[link])
        everything = library.collection()
        matching = library.collection("graph neural network")

    assert len(everything) == 2
    assert everything.query.sources == (LIBRARY_SOURCE,)
    assert everything.diagnostics.relations == (link,)
    assert everything.diagnostics.scores == ()
    assert [paper.title for paper in matching] == [GNN_ARXIV.title]
    assert matching.query.keywords == "graph neural network"
    # A link is carried only when both of its papers are in the collection.
    assert matching.diagnostics.relations == ()
    assert matching.diagnostics.scores[0].rank == 1
    assert matching.diagnostics.pruning[0].paper_key == GNN_ARXIV.dedup_key()


# ------------------------------------------------------ verification cache


class _Clock:
    def __init__(self) -> None:
        self.moment = datetime(2026, 10, 8, 12, 0, tzinfo=UTC)

    def __call__(self) -> datetime:
        return self.moment

    def advance(self, **delta) -> None:
        self.moment += timedelta(**delta)


def test_verification_cache_survives_restart(path):
    verdict = Verdict(VerificationStatus.OK, "https://doi.org/10.1000/gnn", "resolved")
    with Library(path) as library:
        library.verification_cache().put(KIND_DOI, "10.1000/gnn", verdict)

    with Library(path, create=False) as library:
        cache = library.verification_cache()
        assert cache.get(KIND_DOI, "10.1000/gnn") == verdict
        assert cache.get(KIND_DOI, "10.1000/never-checked") is None
        assert cache.get(KIND_URL, "10.1000/gnn") is None      # kind is part of the key


def test_a_verified_identifier_is_checked_again_after_thirty_days(path):
    clock = _Clock()
    with Library(path, now=clock) as library:
        library.verification_cache().put(KIND_DOI, "10.1000/gnn", Verdict(VerificationStatus.OK))
        clock.advance(days=VERIFIED_FOR.days, seconds=-1)
        assert library.verification_cache().get(KIND_DOI, "10.1000/gnn") is not None
        clock.advance(seconds=2)
        assert library.verification_cache().get(KIND_DOI, "10.1000/gnn") is None


@pytest.mark.parametrize(
    "status",
    [VerificationStatus.INVALID, VerificationStatus.UNREACHABLE, VerificationStatus.TIMEOUT],
)
def test_a_failure_is_never_reused_by_a_later_run(path, status):
    failure = Verdict(status, detail="no answer")
    with Library(path) as library:
        cache = library.verification_cache()
        cache.put(KIND_URL, "https://x.test/a", failure)
        # Within the run that saw it, it is reused: twenty decks, one request.
        assert cache.get(KIND_URL, "https://x.test/a") == failure
        # It is on record all the same.
        assert library.stored_verdict(KIND_URL, "https://x.test/a")[0] == failure

    with Library(path) as library:
        assert library.verification_cache().get(KIND_URL, "https://x.test/a") is None


def test_a_verdict_that_cannot_be_checked_is_reused_like_a_good_one(path):
    not_checkable = Verdict(VerificationStatus.SKIPPED, detail="needs a browser")
    with Library(path) as library:
        library.verification_cache().put(KIND_URL, "https://x.test/a", not_checkable)
    with Library(path) as library:
        assert library.verification_cache().get(KIND_URL, "https://x.test/a") == not_checkable


def test_a_later_verdict_replaces_the_earlier_one(path):
    with Library(path) as library:
        library.record_verdict(KIND_URL, "https://x.test/a", Verdict(VerificationStatus.TIMEOUT))
        library.record_verdict(KIND_URL, "https://x.test/a", Verdict(VerificationStatus.OK))
        assert library.stats().verifications == {"ok": 1}
        assert library.verification_cache().get(KIND_URL, "https://x.test/a").status == "ok"


def test_the_export_preflight_asks_only_about_identifiers_it_has_not_verified(path, monkeypatch):
    from thesisagents.core import export_validation

    asked: list[list[tuple[str, str]]] = []

    async def _recording(targets):
        asked.append(sorted(targets))
        return {target: Verdict(VerificationStatus.OK) for target in targets}

    monkeypatch.setattr(export_validation, "_resolve_targets", _recording)
    collection = _collection(FOLDING)

    with Library(path) as library:
        assert verify_collection_blocking(collection, cache=library.verification_cache()).ok
    with Library(path) as library:                     # the next run
        assert verify_collection_blocking(collection, cache=library.verification_cache()).ok
        assert verify_collection_blocking(
            _collection(FOLDING, GNN_OPENALEX), cache=library.verification_cache()
        ).ok

    assert asked[0] == [(KIND_DOI, "10.1000/fold"), (KIND_URL, FOLDING.url)]
    # Run two asked nothing about FOLDING, and only about the new paper.
    assert asked[1:] == [[(KIND_DOI, "10.1000/gnn"), (KIND_URL, GNN_OPENALEX.url)]]


# ------------------------------------------------------------ concurrency


def test_concurrent_readers_do_not_corrupt_the_database(path):
    papers = [
        _paper(f"p{index}", f"Paper number {index} on graphs", doi=f"10.1000/p{index}")
        for index in range(40)
    ]
    with Library(path) as library:
        library.add_papers(papers[:5])
    failures: list[BaseException] = []
    done = threading.Event()

    def read() -> None:
        try:
            with Library(path, create=False) as reader:    # its own connection
                while not done.is_set():
                    count = len(reader.search("graphs", limit=None))
                    if not 5 <= count <= 40:
                        raise RuntimeError(f"Concurrent reader saw an invalid paper count: {count}")
                    reader.stats()
        except BaseException as err:  # noqa: BLE001 - reported by the main thread
            failures.append(err)

    readers = [threading.Thread(target=read) for _ in range(4)]
    for thread in readers:
        thread.start()
    try:
        with Library(path) as writer:
            for paper in papers[5:]:
                writer.add_papers([paper])
    finally:
        done.set()
        for thread in readers:
            thread.join(timeout=30)

    assert failures == []
    with Library(path) as library:
        assert len(library) == 40
        assert library._conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert library._conn.execute("PRAGMA journal_mode").fetchone()[0] == "wal"


def test_two_writers_both_land(path):
    with Library(path) as first, Library(path) as second:
        first.add_papers([GNN_ARXIV])
        second.add_papers([FOLDING])
        second.add_papers([GNN_OPENALEX])
        assert len(first) == 2


def test_one_library_object_can_be_used_from_another_thread(path):
    with Library(path) as library:
        worker = threading.Thread(target=lambda: library.add_papers([GNN_ARXIV]))
        worker.start()
        worker.join(timeout=30)
        assert len(library) == 1


def test_a_failed_import_leaves_nothing_behind(path):
    class _Exploding:
        source = "arxiv"
        source_id = "boom"

        def identity_keys(self):
            raise RuntimeError("boom")

    with Library(path) as library:
        with pytest.raises(RuntimeError, match="boom"):
            library.add_papers([GNN_ARXIV, _Exploding()])
        assert len(library) == 0
        assert library.runs() == []


# ------------------------------------------------------- schema / version


def test_a_new_library_is_at_the_current_schema_version(path):
    with Library(path) as library:
        assert library.schema_version == SCHEMA_VERSION
    with sqlite3.connect(path) as conn:
        assert conn.execute("PRAGMA user_version").fetchone()[0] == SCHEMA_VERSION
        assert conn.execute("PRAGMA application_id").fetchone()[0] == schema.APPLICATION_ID
    conn.close()


def test_reopening_does_not_migrate_again(path):
    with Library(path) as library:
        library.add_papers([GNN_ARXIV])
    with Library(path) as library:
        assert library.schema_version == SCHEMA_VERSION
        assert len(library) == 1


def test_a_library_from_a_newer_version_is_refused(path):
    with Library(path):
        pass
    conn = sqlite3.connect(path)
    conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION + 2}")
    conn.close()

    with pytest.raises(LibraryError) as raised:
        Library(path)
    message = str(raised.value)
    assert f"schema version {SCHEMA_VERSION + 2}" in message
    assert f"up to version {SCHEMA_VERSION}" in message
    assert "upgrade ThesisAgents" in message


def test_an_older_library_is_migrated_step_by_step(path, monkeypatch):
    with Library(path) as library:
        library.add_papers([GNN_ARXIV])

    def _add_notes(conn):
        conn.execute("ALTER TABLE papers ADD COLUMN note TEXT")

    monkeypatch.setattr(schema, "MIGRATIONS", (*schema.MIGRATIONS, _add_notes))
    monkeypatch.setattr(schema, "SCHEMA_VERSION", SCHEMA_VERSION + 1)

    with Library(path) as library:
        assert library.schema_version == SCHEMA_VERSION + 1
        assert len(library) == 1                       # the data came along
        columns = [row[1] for row in library._conn.execute("PRAGMA table_info(papers)")]
    assert "note" in columns


def test_a_migration_that_fails_leaves_the_previous_version(path, monkeypatch):
    with Library(path) as library:
        library.add_papers([GNN_ARXIV])

    def _half_done(conn):
        conn.execute("ALTER TABLE papers ADD COLUMN note TEXT")
        raise sqlite3.OperationalError("disk full")

    monkeypatch.setattr(schema, "MIGRATIONS", (*schema.MIGRATIONS, _half_done))
    monkeypatch.setattr(schema, "SCHEMA_VERSION", SCHEMA_VERSION + 1)
    with pytest.raises(LibraryError, match="disk full"):
        Library(path)
    monkeypatch.undo()

    with Library(path) as library:                     # still a working version-1 library
        assert library.schema_version == SCHEMA_VERSION
        assert len(library) == 1
        columns = [row[1] for row in library._conn.execute("PRAGMA table_info(papers)")]
    assert "note" not in columns


def test_another_applications_database_is_refused_untouched(path):
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE invoices (id INTEGER PRIMARY KEY)")
    conn.commit()
    conn.close()

    with pytest.raises(LibraryError, match="not a ThesisAgents library"):
        Library(path)
    conn = sqlite3.connect(path)
    tables = [row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")]
    conn.close()
    assert tables == ["invoices"]


def test_a_versioned_database_of_another_application_is_refused(path):
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE papers (id INTEGER PRIMARY KEY)")
    conn.execute("PRAGMA user_version = 1")
    conn.commit()
    conn.close()
    with pytest.raises(LibraryError, match="another application"):
        Library(path)


def test_a_file_that_is_not_a_database_is_refused(path):
    path.write_text("these are my reading notes, not a database\n" * 40, encoding="utf-8")
    with pytest.raises(LibraryError, match="not an SQLite database"):
        Library(path)
    assert path.read_text(encoding="utf-8").startswith("these are my reading notes")


def test_reading_a_library_that_does_not_exist_is_an_error_not_an_empty_library(path):
    with pytest.raises(LibraryError, match="no library at"):
        Library(path, create=False)
    assert not path.exists()


def test_a_directory_is_not_a_library(tmp_path):
    with pytest.raises(LibraryError, match="is a directory"):
        Library(tmp_path)


def test_the_parent_directory_is_created(tmp_path):
    nested = tmp_path / "research" / "2026" / "thesis.db"
    with Library(nested) as library:
        library.add_papers([GNN_ARXIV])
    assert nested.is_file()
