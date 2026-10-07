"""The CLI's literature-library flags, with the search stubbed."""

from __future__ import annotations

from pathlib import Path

import pytest

from thesisagents import cli as cli_module
from thesisagents.core.diagnostics import PaperRelation, RelationKind
from thesisagents.core.export_validation import Verdict, VerificationStatus
from thesisagents.core.models import Paper, PaperCollection
from thesisagents.library import Library


@pytest.fixture(autouse=True)
def _stub_pipeline(monkeypatch, sample_papers):
    """No network: the search returns the sample papers, PDFs "download"."""
    from thesisagents.core.pdf_download import PdfDownloadResult

    async def fake_run_search(query, **_kwargs):  # NOSONAR async stub
        return PaperCollection(query=query, papers=tuple(sample_papers))

    async def fake_shutdown():  # NOSONAR async stub
        return None

    async def fake_download(collection, out_dir):  # NOSONAR async stub
        downloaded.append([paper.title for paper in collection.papers])
        return [
            PdfDownloadResult(paper_key=paper.bibtex_key(), path=None, skipped_reason="stub")
            for paper in collection.papers
        ]

    downloaded: list[list[str]] = []
    monkeypatch.setattr(cli_module, "run_search", fake_run_search)
    monkeypatch.setattr(cli_module, "shutdown_clients", fake_shutdown)
    monkeypatch.setattr(cli_module, "download_pdfs", fake_download)
    return downloaded


@pytest.fixture()
def library_path(tmp_path) -> Path:
    return tmp_path / "lib" / "thesis.db"


def _search(tmp_path, *extra: str) -> int:
    return cli_module.main(
        ["--query", "attention", "--source", "arxiv", "--no-pdf", "--export", "bib",
         "--out", str(tmp_path / "out"), *extra]
    )


# ---------------------------------------------------------- --library-add


def test_library_add_stores_the_run(tmp_path, library_path, sample_papers, capsys):
    assert _search(tmp_path, "--library", str(library_path), "--library-add") == 0

    out = capsys.readouterr().out
    assert f"Library {library_path}: 2 added, 0 already there, 0 citation link(s) stored." in out
    assert "2 paper(s) in all." in out
    with Library(library_path, create=False) as library:
        assert {entry.paper.title for entry in library.search("")} == {
            paper.title for paper in sample_papers
        }
        run = library.runs()[0]
    assert (run.kind, run.keywords, run.papers) == ("search", "attention", 2)


def test_library_add_twice_merges_instead_of_duplicating(tmp_path, library_path, capsys):
    _search(tmp_path, "--library", str(library_path), "--library-add")
    capsys.readouterr()
    assert _search(tmp_path, "--library", str(library_path), "--library-add") == 0

    assert "0 added, 2 already there" in capsys.readouterr().out
    with Library(library_path) as library:
        assert len(library) == 2
        assert len(library.runs()) == 2


def test_library_add_keeps_the_links_found_by_snowball(
    tmp_path, library_path, sample_papers, monkeypatch, capsys
):
    found = Paper(
        source="openalex", source_id="W7", title="Attention Mechanisms Reviewed",
        authors=("Ada Author",), year=2024, venue=None, abstract="",
        url="https://example.org/W7", doi="10.1000/w7",
    )

    class _Provider:
        name = "graph"

        async def references(self, paper, limit):
            return [found] if paper.source_id == sample_papers[0].source_id else []

        async def cited_by(self, paper, limit):
            return []

    monkeypatch.setattr("thesisagents.core.snowball._default_providers", lambda: [_Provider()])
    code = _search(
        tmp_path, "--snowball", "references", "--snowball-seeds", "1",
        "--library", str(library_path), "--library-add",
    )

    assert code == 0
    assert "3 added, 0 already there, 1 citation link(s) stored." in capsys.readouterr().out
    with Library(library_path) as library:
        assert library.relations() == (
            PaperRelation(
                sample_papers[0].dedup_key(), "doi:10.1000/w7",
                RelationKind.REFERENCES, "graph", 1,
            ),
        )


def test_library_add_is_quiet_under_quiet(tmp_path, library_path, capsys):
    assert _search(tmp_path, "--library", str(library_path), "--library-add", "--quiet") == 0
    assert "Library" not in capsys.readouterr().out
    with Library(library_path) as library:
        assert len(library) == 2


def test_a_run_without_library_add_stores_no_papers(tmp_path, library_path):
    assert _search(tmp_path, "--library", str(library_path)) == 0
    with Library(library_path) as library:
        assert len(library) == 0
        # The library was still the identifier cache of the run.
        assert library.stats().verifications == {"ok": 3}


def test_identifiers_verified_by_an_earlier_run_are_not_asked_about_again(
    tmp_path, library_path, monkeypatch
):
    from thesisagents.core import export_validation

    asked: list[int] = []

    async def _recording(targets):
        asked.append(len(targets))
        return {target: Verdict(VerificationStatus.OK) for target in targets}

    monkeypatch.setattr(export_validation, "_resolve_targets", _recording)
    assert _search(tmp_path, "--library", str(library_path)) == 0
    assert _search(tmp_path, "--library", str(library_path)) == 0

    # 2 URLs + 1 DOI in the first run, nothing left to ask in the second.
    assert asked[0] == 3
    assert sum(asked[1:]) == 0


@pytest.mark.parametrize(
    "flags",
    [["--library-add"], ["--library-search", "x"], ["--library-export"]],
)
def test_library_flags_need_a_library_path(tmp_path, flags, capsys):
    argv = ["--out", str(tmp_path), *flags]
    if flags == ["--library-add"]:
        argv = ["--query", "attention", *argv]
    with pytest.raises(SystemExit) as raised:
        cli_module.main(argv)
    assert str(raised.value) == f"{flags[0]} needs --library PATH"


def test_library_add_cannot_be_combined_with_a_library_read(tmp_path, library_path):
    with pytest.raises(SystemExit, match="cannot be combined"):
        cli_module.main(
            ["--library", str(library_path), "--library-export", "--library-add",
             "--out", str(tmp_path)]
        )


def test_a_library_path_that_cannot_be_used_stops_the_run_before_the_search(
    tmp_path, monkeypatch, capsys
):
    async def _must_not_run(query, **_kwargs):
        raise AssertionError("the search ran")

    monkeypatch.setattr(cli_module, "run_search", _must_not_run)
    notes = tmp_path / "notes.txt"
    notes.write_text("not a database " * 100, encoding="utf-8")

    assert _search(tmp_path, "--library", str(notes), "--library-add") == 2
    assert "is not an SQLite database" in capsys.readouterr().err


# ------------------------------------------------------- --library-search


@pytest.fixture()
def filled(tmp_path, library_path, capsys):
    _search(tmp_path, "--library", str(library_path), "--library-add")
    capsys.readouterr()
    return library_path


def test_library_search_lists_matches_without_searching(filled, monkeypatch, capsys):
    async def _must_not_run(query, **_kwargs):
        raise AssertionError("the search ran")

    monkeypatch.setattr(cli_module, "run_search", _must_not_run)
    code = cli_module.main(["--library", str(filled), "--library-search", "attention"])

    assert code == 0
    out = capsys.readouterr().out
    assert f'Library {filled}: 1 of 2 paper(s) match "attention".' in out
    assert "(2024) Alice Anderson: Sample Paper on Attention" in out
    assert "arxiv:2401.00001 | seen 1 time(s), last " in out
    assert "Second Paper" not in out


def test_library_search_with_an_empty_query_lists_the_library(filled, capsys):
    code = cli_module.main(["--library", str(filled), "--library-search", "", "--max", "1"])
    assert code == 0
    out = capsys.readouterr().out
    assert "1 of 2 paper(s), most recently seen first." in out
    assert out.count("seen 1 time(s)") == 1


def test_library_search_narrows_by_year(filled, capsys):
    code = cli_module.main(
        ["--library", str(filled), "--library-search", "", "--year-to", "2023"]
    )
    assert code == 0
    out = capsys.readouterr().out
    assert "Second Paper with Special & Chars" in out
    assert "Sample Paper on Attention" not in out


def test_library_search_with_no_match_exits_one(filled, capsys):
    code = cli_module.main(["--library", str(filled), "--library-search", "chromodynamics"])
    assert code == 1
    assert 'none of 2 paper(s) match "chromodynamics"' in capsys.readouterr().err


def test_library_search_on_a_missing_library_is_an_error(tmp_path, capsys):
    missing = tmp_path / "typo.db"
    code = cli_module.main(["--library", str(missing), "--library-search", "x"])
    assert code == 2
    assert "no library at" in capsys.readouterr().err
    assert not missing.exists()


def test_library_search_excludes_a_query_in_the_same_run(filled, capsys):
    with pytest.raises(SystemExit):
        cli_module.main(
            ["--library", str(filled), "--library-search", "x", "--query", "attention"]
        )
    assert "not allowed with argument" in capsys.readouterr().err


# ------------------------------------------------------- --library-export


def test_library_export_writes_the_stored_papers(
    filled, tmp_path, _stub_pipeline, monkeypatch, capsys
):
    async def _must_not_run(query, **_kwargs):
        raise AssertionError("the search ran")

    monkeypatch.setattr(cli_module, "run_search", _must_not_run)
    out_dir = tmp_path / "from-library"
    code = cli_module.main(
        ["--library", str(filled), "--library-export", "--out", str(out_dir)]
    )

    assert code == 0
    # Default formats for a library: the reading list and the bibliography.
    assert sorted(path.suffix for path in out_dir.iterdir()) == [".bib", ".xlsx"]
    bib = next(out_dir.glob("*.bib")).read_text(encoding="utf-8")
    assert bib.count("@") == 2
    assert _stub_pipeline == []                        # no PDF was fetched
    assert "Found 2 papers for: library" in capsys.readouterr().out


def test_library_export_can_be_narrowed_by_a_query(filled, tmp_path):
    out_dir = tmp_path / "narrow"
    code = cli_module.main(
        ["--library", str(filled), "--library-export", "attention",
         "--export", "bib", "--out", str(out_dir)]
    )
    assert code == 0
    bib = next(out_dir.glob("*.bib")).read_text(encoding="utf-8")
    assert bib.count("@") == 1
    assert "Sample Paper on Attention" in bib
    assert next(out_dir.glob("*.bib")).name.startswith("attention-")


def test_library_export_with_diagnostics_scores_against_the_query(filled, tmp_path, capsys):
    out_dir = tmp_path / "diag"
    code = cli_module.main(
        ["--library", str(filled), "--library-export", "attention", "--diagnostics",
         "--export", "bib", "--out", str(out_dir)]
    )
    assert code == 0
    assert "Ranking diagnostics for: attention" in capsys.readouterr().out
    assert (out_dir / "diagnostics.json").is_file()


def test_library_export_downloads_pdfs_only_when_asked(filled, tmp_path, _stub_pipeline):
    code = cli_module.main(
        ["--library", str(filled), "--library-export", "--export", "bib,pdf",
         "--out", str(tmp_path / "with-pdf")]
    )
    assert code == 0
    assert len(_stub_pipeline) == 1 and len(_stub_pipeline[0]) == 2


def test_library_export_does_not_enrich_because_a_key_is_set(
    filled, tmp_path, monkeypatch
):
    async def _must_not_run(*_args, **_kwargs):
        raise AssertionError("the summariser ran")

    monkeypatch.setenv("ANTHROPIC_API_KEY", "placeholder-not-a-real-key")
    monkeypatch.setattr(cli_module, "enrich_collection", _must_not_run)
    code = cli_module.main(
        ["--library", str(filled), "--library-export", "--export", "bib",
         "--out", str(tmp_path / "plain")]
    )
    assert code == 0


def test_library_export_with_nothing_matching_exits_one(filled, tmp_path, capsys):
    code = cli_module.main(
        ["--library", str(filled), "--library-export", "chromodynamics",
         "--export", "bib", "--out", str(tmp_path / "none")]
    )
    assert code == 1
    assert "No results." in capsys.readouterr().err


def test_library_export_on_a_missing_library_is_an_error(tmp_path, capsys):
    missing = tmp_path / "typo.db"
    code = cli_module.main(
        ["--library", str(missing), "--library-export", "--out", str(tmp_path / "o")]
    )
    assert code == 2
    assert "no library at" in capsys.readouterr().err
    assert not missing.exists()
