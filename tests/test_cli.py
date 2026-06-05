"""CLI smoke test: monkeypatch the pipeline to return canned papers and run main."""

from __future__ import annotations

from pathlib import Path

import pytest

from thesisagents import cli as cli_module
from thesisagents.core.identifiers import PaperIdentifier
from thesisagents.core.models import PaperCollection, Query


@pytest.fixture(autouse=True)
def _stub_download_pdfs(monkeypatch, tmp_path):
    """Default fake downloader: pretends every paper's PDF was retrieved so
    the new per-paper PPT gate passes. Tests exercising the gate's
    paywall / failure branches override this fixture by re-patching
    ``cli_module.download_pdfs``."""
    from thesisagents.core.pdf_download import PdfDownloadResult

    async def _fake_success(collection, out_dir):
        pdf_dir = Path(out_dir) / "pdfs"
        pdf_dir.mkdir(parents=True, exist_ok=True)
        results = []
        for paper in collection.papers:
            path = pdf_dir / f"{paper.bibtex_key()}.pdf"
            path.write_bytes(b"%PDF-1.4 stub")
            results.append(
                PdfDownloadResult(
                    paper_key=paper.bibtex_key(),
                    path=path,
                    skipped_reason=None,
                )
            )
        return results

    monkeypatch.setattr(cli_module, "download_pdfs", _fake_success)
    # Sample fixtures have some papers without pdf_url, which would trip the
    # interactive paywall prompt. Auto-accept so the prompt never blocks.
    monkeypatch.setattr("builtins.input", lambda _prompt="": "y")


@pytest.fixture()
def patched_pipeline(monkeypatch, sample_papers):
    async def fake_run_search(query: Query, **_kwargs) -> PaperCollection:
        return PaperCollection(query=query, papers=tuple(sample_papers))

    async def fake_shutdown() -> None:
        return None

    monkeypatch.setattr(cli_module, "run_search", fake_run_search)
    monkeypatch.setattr(cli_module, "shutdown_clients", fake_shutdown)
    # Leave the autouse ``_stub_download_pdfs`` in place so the new per-paper
    # PPT gate sees every paper as downloadable.


def test_cli_runs_end_to_end(tmp_path: Path, patched_pipeline, capsys):
    code = cli_module.main(
        [
            "--query", "attention",
            "--source", "arxiv",
            "--max", "5",
            "--export", "md,bib,json",
            "--out", str(tmp_path),
            "--filename-stem", "cli-test",
        ]
    )
    assert code == 0
    assert (tmp_path / "cli-test.md").exists()
    assert (tmp_path / "cli-test.bib").exists()
    assert (tmp_path / "cli-test.json").exists()
    captured = capsys.readouterr().out
    assert "Wrote:" in captured


def test_cli_rejects_unknown_source(tmp_path, capsys):
    with pytest.raises(SystemExit):
        cli_module.main(
            ["--query", "x", "--source", "nope", "--out", str(tmp_path)]
        )


def test_cli_rejects_unknown_export(tmp_path, patched_pipeline):
    with pytest.raises(SystemExit):
        cli_module.main(
            [
                "--query", "x", "--source", "arxiv",
                "--export", "weird", "--out", str(tmp_path),
            ]
        )


def test_cli_no_results_returns_one(tmp_path, monkeypatch):
    async def empty_pipeline(query: Query, **_kwargs) -> PaperCollection:
        return PaperCollection(query=query, papers=())

    async def fake_shutdown() -> None:
        return None

    monkeypatch.setattr(cli_module, "run_search", empty_pipeline)
    monkeypatch.setattr(cli_module, "shutdown_clients", fake_shutdown)
    code = cli_module.main(
        ["--query", "x", "--source", "arxiv", "--out", str(tmp_path)]
    )
    assert code == 1


def test_cli_search_default_exports(tmp_path, patched_pipeline):
    """When --query is given without --export, default to pptx,xlsx,bib."""
    code = cli_module.main(
        ["--query", "x", "--source", "arxiv", "--out", str(tmp_path)]
    )
    assert code == 0
    files = {p.suffix for p in tmp_path.iterdir() if p.is_file()}
    assert files == {".pptx", ".xlsx", ".bib"}


def test_cli_single_paper_default_exports(tmp_path, monkeypatch, sample_papers):
    """When --paper is given without --export, default to pptx,bib (no xlsx)."""
    from thesisagents.core.models import PaperCollection, Query

    async def fake_single(identifier: PaperIdentifier) -> PaperCollection:
        query = Query(keywords=identifier.value, sources=("arxiv",), max_results=1)
        return PaperCollection(query=query, papers=(sample_papers[0],))

    async def fake_shutdown() -> None:
        return None

    monkeypatch.setattr(cli_module, "run_single_paper", fake_single)
    monkeypatch.setattr(cli_module, "shutdown_clients", fake_shutdown)
    code = cli_module.main(
        ["--paper", "2401.08741", "--out", str(tmp_path)]
    )
    assert code == 0
    files = {p.suffix for p in tmp_path.iterdir() if p.is_file()}
    assert files == {".pptx", ".bib"}
    assert ".xlsx" not in files


def test_cli_single_paper_explicit_export_wins(tmp_path, monkeypatch, sample_papers):
    """Explicit --export overrides the single-paper default."""
    from thesisagents.core.models import PaperCollection, Query

    async def fake_single(identifier: PaperIdentifier) -> PaperCollection:
        query = Query(keywords=identifier.value, sources=("arxiv",), max_results=1)
        return PaperCollection(query=query, papers=(sample_papers[0],))

    async def fake_shutdown() -> None:
        return None

    monkeypatch.setattr(cli_module, "run_single_paper", fake_single)
    monkeypatch.setattr(cli_module, "shutdown_clients", fake_shutdown)
    code = cli_module.main(
        [
            "--paper", "2401.08741",
            "--export", "pptx,xlsx,bib",
            "--out", str(tmp_path),
        ]
    )
    assert code == 0
    files = {p.suffix for p in tmp_path.iterdir() if p.is_file()}
    assert files == {".pptx", ".xlsx", ".bib"}


def test_cli_single_paper_mode(tmp_path, monkeypatch, capsys, sample_papers):
    captured_identifiers: list[PaperIdentifier] = []

    async def fake_single(identifier: PaperIdentifier) -> PaperCollection:
        captured_identifiers.append(identifier)
        query = Query(keywords=identifier.value, sources=("arxiv",), max_results=1)
        return PaperCollection(query=query, papers=(sample_papers[0],))

    async def fake_shutdown() -> None:
        return None

    monkeypatch.setattr(cli_module, "run_single_paper", fake_single)
    monkeypatch.setattr(cli_module, "shutdown_clients", fake_shutdown)
    code = cli_module.main(
        [
            "--paper", "https://arxiv.org/abs/2401.08741v1",
            "--export", "md,bib",
            "--out", str(tmp_path),
            "--filename-stem", "single",
        ]
    )
    assert code == 0
    assert (tmp_path / "single.md").exists()
    assert (tmp_path / "single.bib").exists()
    assert captured_identifiers and captured_identifiers[0].value == "2401.08741"
    captured = capsys.readouterr().out
    assert "Sample Paper on Attention" in captured


def test_cli_requires_query_or_paper(tmp_path):
    with pytest.raises(SystemExit):
        cli_module.main(["--source", "arxiv", "--out", str(tmp_path)])


def test_cli_rejects_both_query_and_paper(tmp_path):
    with pytest.raises(SystemExit):
        cli_module.main(
            [
                "--query", "x", "--paper", "2401.08741",
                "--source", "arxiv", "--out", str(tmp_path),
            ]
        )


def test_cli_bare_invocation_dispatches_gui(monkeypatch):
    """`thesisagents` with no args MUST route to the GUI dispatcher.

    Regression: the bare command used to crash with `one of the arguments
    --query/-q --paper/-p --pdf is required` because the mutex group is
    `required=True`. Users expected a "just open the app" gesture, and
    the GUI extras' own entry point already does that — so the bare
    CLI now mirrors `thesisagents gui`.
    """
    called: dict[str, list[str]] = {}

    def fake_dispatch_gui(argv: list[str]) -> int:
        called["argv"] = argv
        return 0

    monkeypatch.setattr(cli_module, "_dispatch_gui", fake_dispatch_gui)
    assert cli_module.main([]) == 0
    assert called == {"argv": []}


def test_cli_gui_subcommand_dispatches_gui(monkeypatch):
    """`thesisagents gui` still routes to the GUI dispatcher, with any
    trailing tokens forwarded to the GUI's own argv parser."""
    called: dict[str, list[str]] = {}

    def fake_dispatch_gui(argv: list[str]) -> int:
        called["argv"] = argv
        return 0

    monkeypatch.setattr(cli_module, "_dispatch_gui", fake_dispatch_gui)
    assert cli_module.main(["gui", "--debug"]) == 0
    assert called == {"argv": ["--debug"]}


def test_cli_rejects_doi_identifier_until_resolver_lands(tmp_path):
    code = cli_module.main(
        ["--paper", "10.1234/example", "--out", str(tmp_path)]
    )
    assert code == 2


def test_cli_source_default_is_multi_source(tmp_path, monkeypatch, sample_papers):
    """When --source is omitted, run_search must be invoked across the
    DEFAULT_SOURCES mix, not just arxiv."""
    from thesisagents.core.constants import DEFAULT_SOURCES

    captured: dict[str, Query] = {}

    async def fake_run_search(query: Query, **_kwargs) -> PaperCollection:
        captured["query"] = query
        return PaperCollection(query=query, papers=tuple(sample_papers))

    async def fake_shutdown() -> None:
        return None

    monkeypatch.setattr(cli_module, "run_search", fake_run_search)
    monkeypatch.setattr(cli_module, "shutdown_clients", fake_shutdown)

    code = cli_module.main(
        ["--query", "x", "--out", str(tmp_path), "--export", "bib"]
    )
    assert code == 0
    assert captured["query"].sources == DEFAULT_SOURCES


def test_cli_list_sources(capsys):
    """--list-sources prints the catalog (incl. the newest plugins) and exits 0
    without needing a query/paper/pdf mode."""
    code = cli_module.main(["--list-sources"])
    assert code == 0
    out = capsys.readouterr().out
    assert "europepmc" in out
    assert "doaj" in out
    assert "[default]" in out


def test_cli_list_exports(capsys):
    """--list-exports prints every format, including the new ris / csv."""
    code = cli_module.main(["--list-exports"])
    assert code == 0
    out = capsys.readouterr().out
    assert "ris" in out
    assert "csv" in out
    assert "pptx" in out


def test_cli_exclude_source_prunes_default_mix(tmp_path, monkeypatch, sample_papers):
    """--exclude-source subtracts from the resolved mix; the no-VPN path drops
    only ieee and keeps every other default source."""
    from thesisagents.core.constants import DEFAULT_SOURCES

    captured: dict[str, Query] = {}

    async def fake_run_search(query: Query, **_kwargs) -> PaperCollection:  # NOSONAR async stub
        captured["query"] = query
        return PaperCollection(query=query, papers=tuple(sample_papers))

    async def fake_shutdown() -> None:  # NOSONAR async stub
        return None

    monkeypatch.setattr(cli_module, "run_search", fake_run_search)
    monkeypatch.setattr(cli_module, "shutdown_clients", fake_shutdown)

    code = cli_module.main(
        ["--query", "x", "--out", str(tmp_path), "--export", "bib",
         "--exclude-source", "ieee"]
    )
    assert code == 0
    assert "ieee" not in captured["query"].sources
    expected = tuple(s for s in DEFAULT_SOURCES if s != "ieee")
    assert captured["query"].sources == expected


def test_cli_min_citations_flows_into_query(tmp_path, monkeypatch, sample_papers):
    """--min-citations is parsed and passed through to the Query (it was
    previously unreachable from the CLI)."""
    captured: dict[str, Query] = {}

    async def fake_run_search(query: Query, **_kwargs) -> PaperCollection:  # NOSONAR async stub
        captured["query"] = query
        return PaperCollection(query=query, papers=tuple(sample_papers))

    async def fake_shutdown() -> None:  # NOSONAR async stub
        return None

    monkeypatch.setattr(cli_module, "run_search", fake_run_search)
    monkeypatch.setattr(cli_module, "shutdown_clients", fake_shutdown)
    code = cli_module.main(
        ["--query", "x", "--out", str(tmp_path), "--export", "bib",
         "--min-citations", "50"]
    )
    assert code == 0
    assert captured["query"].min_citations == 50


def test_cli_exclude_unknown_source_errors(tmp_path):
    """A typo in --exclude-source must fail loudly, not silently no-op."""
    with pytest.raises(SystemExit):
        cli_module.main(
            ["--query", "x", "--out", str(tmp_path), "--exclude-source", "nope"]
        )


def test_cli_exclude_all_sources_errors(tmp_path):
    """Excluding the only requested source leaves an empty mix -> error."""
    with pytest.raises(SystemExit):
        cli_module.main(
            ["--query", "x", "--out", str(tmp_path),
             "--source", "arxiv", "--exclude-source", "arxiv"]
        )


def test_cli_top_tier_filter_off_by_default(tmp_path, monkeypatch, sample_papers):
    """top_tier_only is OFF by default (broader coverage including IEEE / ACM
    workshops); --top-tier-only flips it on."""
    captured: dict[str, Query] = {}

    async def fake_run_search(query: Query, **_kwargs) -> PaperCollection:
        captured["query"] = query
        return PaperCollection(query=query, papers=tuple(sample_papers))

    async def fake_shutdown() -> None:
        return None

    monkeypatch.setattr(cli_module, "run_search", fake_run_search)
    monkeypatch.setattr(cli_module, "shutdown_clients", fake_shutdown)

    code = cli_module.main(
        ["--query", "x", "--out", str(tmp_path), "--export", "bib"]
    )
    assert code == 0
    assert captured["query"].top_tier_only is False

    captured.clear()
    code = cli_module.main(
        ["--query", "x", "--top-tier-only", "--out", str(tmp_path), "--export", "bib"]
    )
    assert code == 0
    assert captured["query"].top_tier_only is True


def test_cli_default_triggers_pdf_download(tmp_path, monkeypatch, sample_papers):
    """Default flag set should invoke download_pdfs; --no-pdf disables it."""
    calls: list[str] = []

    async def fake_run_search(query: Query, **_kwargs) -> PaperCollection:
        return PaperCollection(query=query, papers=tuple(sample_papers))

    async def fake_shutdown() -> None:
        return None

    async def fake_download(_collection, _out_dir):
        calls.append("called")
        return []

    monkeypatch.setattr(cli_module, "run_search", fake_run_search)
    monkeypatch.setattr(cli_module, "shutdown_clients", fake_shutdown)
    monkeypatch.setattr(cli_module, "download_pdfs", fake_download)

    code = cli_module.main(
        [
            "--query", "x",
            "--source", "arxiv",
            "--out", str(tmp_path),
            "--export", "bib",
        ]
    )
    assert code == 0
    assert calls == ["called"]


def test_cli_no_pdf_flag_skips_download(tmp_path, monkeypatch, sample_papers):
    calls: list[str] = []

    async def fake_run_search(query: Query, **_kwargs) -> PaperCollection:
        return PaperCollection(query=query, papers=tuple(sample_papers))

    async def fake_shutdown() -> None:
        return None

    async def fake_download(_collection, _out_dir):
        calls.append("called")
        return []

    monkeypatch.setattr(cli_module, "run_search", fake_run_search)
    monkeypatch.setattr(cli_module, "shutdown_clients", fake_shutdown)
    monkeypatch.setattr(cli_module, "download_pdfs", fake_download)

    code = cli_module.main(
        [
            "--query", "x",
            "--source", "arxiv",
            "--no-pdf",
            "--out", str(tmp_path),
            "--export", "bib",
        ]
    )
    assert code == 0
    assert calls == []


# ---------------------------------------------------------------------------
# Accessibility gate (per-paper PPT, paywall prompt) — added with the rewrite
# that stopped producing aggregate decks when most papers are paywalled.
# ---------------------------------------------------------------------------


def _build_paper(source_id: str, *, pdf_url: str | None):
    from thesisagents.core.models import Paper

    return Paper(
        source="arxiv",
        source_id=source_id,
        title=f"Paper {source_id}",
        authors=(f"Author {source_id}",),
        year=2025,
        venue=None,
        abstract="abstract body",
        url=f"https://example.com/{source_id}",
        pdf_url=pdf_url,
    )


def _patch_search(monkeypatch, papers):
    from thesisagents.core.models import PaperCollection

    async def fake_run_search(query, **_kwargs):
        return PaperCollection(query=query, papers=tuple(papers))

    async def fake_shutdown():
        return None

    monkeypatch.setattr(cli_module, "run_search", fake_run_search)
    monkeypatch.setattr(cli_module, "shutdown_clients", fake_shutdown)


def test_cli_per_paper_pptx_one_per_accessible_paper(
    tmp_path, monkeypatch
):
    """N papers with successful PDFs should produce N pptx files, one each."""
    papers = [
        _build_paper("a", pdf_url="https://example.com/a.pdf"),
        _build_paper("b", pdf_url="https://example.com/b.pdf"),
        _build_paper("c", pdf_url="https://example.com/c.pdf"),
    ]
    _patch_search(monkeypatch, papers)
    code = cli_module.main(
        [
            "--query", "x",
            "--source", "arxiv",
            "--out", str(tmp_path),
            "--yes",
        ]
    )
    assert code == 0
    pptx_files = sorted(p.name for p in tmp_path.iterdir() if p.suffix == ".pptx")
    assert len(pptx_files) == 3
    keys = {p.bibtex_key() for p in papers}
    assert {Path(f).stem for f in pptx_files} == keys


def test_cli_aggregate_xlsx_bib_only_over_accessible(tmp_path, monkeypatch):
    """xlsx + bib aggregate over the accessible subset, not the full result set."""
    from thesisagents.core.pdf_download import PdfDownloadResult

    accessible = _build_paper("good", pdf_url="https://example.com/good.pdf")
    paywalled = _build_paper("bad", pdf_url=None)
    _patch_search(monkeypatch, [accessible, paywalled])

    async def selective_download(collection, out_dir):
        # Only the accessible paper "downloads".
        pdf_dir = Path(out_dir) / "pdfs"
        pdf_dir.mkdir(parents=True, exist_ok=True)
        results = []
        for paper in collection.papers:
            if paper.pdf_url:
                path = pdf_dir / f"{paper.bibtex_key()}.pdf"
                path.write_bytes(b"%PDF-1.4 stub")
                results.append(
                    PdfDownloadResult(
                        paper_key=paper.bibtex_key(),
                        path=path,
                        skipped_reason=None,
                    )
                )
            else:
                results.append(
                    PdfDownloadResult(
                        paper_key=paper.bibtex_key(),
                        path=None,
                        skipped_reason="no_pdf_url",
                    )
                )
        return results

    monkeypatch.setattr(cli_module, "download_pdfs", selective_download)
    code = cli_module.main(
        [
            "--query", "x",
            "--source", "arxiv",
            "--out", str(tmp_path),
            "--yes",
        ]
    )
    assert code == 0
    # Exactly one per-paper PPT, named after the accessible paper.
    pptx_files = [p for p in tmp_path.iterdir() if p.suffix == ".pptx"]
    assert len(pptx_files) == 1
    assert pptx_files[0].stem == accessible.bibtex_key()
    # bib should reference only the accessible paper.
    bib_files = [p for p in tmp_path.iterdir() if p.suffix == ".bib"]
    assert len(bib_files) == 1
    bib_text = bib_files[0].read_text(encoding="utf-8")
    assert accessible.bibtex_key() in bib_text
    assert paywalled.bibtex_key() not in bib_text


def test_cli_aborts_when_no_pdf_accessible(tmp_path, monkeypatch, capsys):
    """If every paper is paywalled, abort with a clear error and exit code 1."""
    papers = [_build_paper(str(i), pdf_url=None) for i in range(3)]
    _patch_search(monkeypatch, papers)
    code = cli_module.main(
        [
            "--query", "x",
            "--source", "arxiv",
            "--out", str(tmp_path),
            "--yes",
        ]
    )
    # Either gate aborts (accessible == 0) or downstream catches it.
    assert code == 1
    err = capsys.readouterr().err
    assert "no paper" in err.lower() or "no pdf" in err.lower()


def test_cli_paywall_prompt_blocks_without_yes(tmp_path, monkeypatch):
    """When >30% are paywalled and the user answers 'n', abort with code 1."""
    papers = [
        _build_paper("a", pdf_url=None),
        _build_paper("b", pdf_url=None),
        _build_paper("c", pdf_url="https://example.com/c.pdf"),
    ]
    _patch_search(monkeypatch, papers)
    # Override the autouse 'always-yes' to simulate the user declining.
    monkeypatch.setattr("builtins.input", lambda _prompt="": "n")
    code = cli_module.main(
        [
            "--query", "x",
            "--source", "arxiv",
            "--out", str(tmp_path),
        ]
    )
    assert code == 1


def test_cli_paywall_below_threshold_does_not_prompt(tmp_path, monkeypatch):
    """If only 1 of 10 is paywalled (10% < 30%), proceed silently."""
    from thesisagents.core.pdf_download import PdfDownloadResult

    papers = [
        _build_paper(str(i), pdf_url=f"https://example.com/{i}.pdf")
        for i in range(9)
    ] + [_build_paper("bad", pdf_url=None)]
    _patch_search(monkeypatch, papers)

    async def selective(collection, out_dir):
        pdf_dir = Path(out_dir) / "pdfs"
        pdf_dir.mkdir(parents=True, exist_ok=True)
        results = []
        for paper in collection.papers:
            if paper.pdf_url:
                path = pdf_dir / f"{paper.bibtex_key()}.pdf"
                path.write_bytes(b"%PDF-1.4 stub")
                results.append(
                    PdfDownloadResult(
                        paper_key=paper.bibtex_key(),
                        path=path,
                        skipped_reason=None,
                    )
                )
            else:
                results.append(
                    PdfDownloadResult(
                        paper_key=paper.bibtex_key(),
                        path=None,
                        skipped_reason="no_pdf_url",
                    )
                )
        return results

    monkeypatch.setattr(cli_module, "download_pdfs", selective)

    def boom(_prompt=""):
        raise AssertionError("prompt should not have fired below threshold")

    monkeypatch.setattr("builtins.input", boom)
    code = cli_module.main(
        [
            "--query", "x",
            "--source", "arxiv",
            "--out", str(tmp_path),
        ]
    )
    assert code == 0
    pptx_files = [p for p in tmp_path.iterdir() if p.suffix == ".pptx"]
    assert len(pptx_files) == 9


# ---------------------------------------------------------------------------
# --pdf path: user supplies a local PDF
# ---------------------------------------------------------------------------


def _stub_pdf_extract(monkeypatch, text: str = "Extracted paper body."):
    """Replace the pypdf-backed text extractor so tests don't need a real PDF."""
    monkeypatch.setattr(
        "thesisagents.intelligence.pdf._extract_text",
        lambda body, source="local": (text, 1),  # noqa: ARG005  # signature mirror
    )


def _write_fake_pdf(path: Path) -> None:
    """Write the minimum byte sequence that passes the %PDF magic check."""
    path.write_bytes(b"%PDF-1.4\n% stub for tests\n")


def test_cli_pdf_mode_produces_pptx_and_copies_pdf(tmp_path, monkeypatch):
    _stub_pdf_extract(monkeypatch)
    src = tmp_path / "input.pdf"
    _write_fake_pdf(src)
    out = tmp_path / "out"

    async def fake_shutdown() -> None:
        return None

    monkeypatch.setattr(cli_module, "shutdown_clients", fake_shutdown)
    code = cli_module.main(
        [
            "--pdf", str(src),
            "--title", "Title From Flag",
            "--authors", "Alice Anderson, Bob Brown",
            "--year", "2026",
            "--venue", "Test Venue",
            "--out", str(out),
        ]
    )
    assert code == 0
    pptx_files = [p for p in out.iterdir() if p.suffix == ".pptx"]
    bib_files = [p for p in out.iterdir() if p.suffix == ".bib"]
    assert len(pptx_files) == 1
    assert len(bib_files) == 1
    # PDF copied to the pdfs/ subdir
    pdf_copies = list((out / "pdfs").iterdir())
    assert len(pdf_copies) == 1
    assert pdf_copies[0].read_bytes().startswith(b"%PDF")


def test_cli_pdf_mode_uses_filename_title_when_flag_absent(tmp_path, monkeypatch):
    _stub_pdf_extract(monkeypatch)
    src = tmp_path / "my-cool_paper.pdf"
    _write_fake_pdf(src)
    out = tmp_path / "out"

    async def fake_shutdown() -> None:
        return None

    monkeypatch.setattr(cli_module, "shutdown_clients", fake_shutdown)
    code = cli_module.main(
        ["--pdf", str(src), "--out", str(out)]
    )
    assert code == 0
    bib_text = next(p for p in out.iterdir() if p.suffix == ".bib").read_text(
        encoding="utf-8"
    )
    # Filename stem becomes the title — underscores / dashes turn into spaces.
    assert "my cool paper" in bib_text.lower()


def test_cli_pdf_mode_rejects_missing_file(tmp_path, monkeypatch, capsys):
    async def fake_shutdown() -> None:
        return None

    monkeypatch.setattr(cli_module, "shutdown_clients", fake_shutdown)
    exit_code = cli_module.main(
        ["--pdf", str(tmp_path / "nope.pdf"), "--out", str(tmp_path / "out")]
    )
    assert exit_code == 2
    assert "does not exist" in capsys.readouterr().err.lower()


def test_cli_pdf_mode_rejects_non_pdf(tmp_path, monkeypatch, capsys):
    src = tmp_path / "not.pdf"
    src.write_bytes(b"<html>not a pdf</html>")

    async def fake_shutdown() -> None:
        return None

    monkeypatch.setattr(cli_module, "shutdown_clients", fake_shutdown)
    exit_code = cli_module.main(
        ["--pdf", str(src), "--out", str(tmp_path / "out")]
    )
    assert exit_code == 2
    assert "%pdf magic" in capsys.readouterr().err.lower()


# ---------------------------------------------------------------------------
# Auto-enrich default (rich PPT when ANTHROPIC_API_KEY is set)
# ---------------------------------------------------------------------------


def _stub_enrich_collection(monkeypatch) -> list[str]:
    """Replace enrich_collection with a no-op that records its calls."""
    calls: list[str] = []

    async def fake_enrich(collection, language=None, model=None):  # noqa: ARG001
        calls.append("called")
        return collection

    monkeypatch.setattr(cli_module, "enrich_collection", fake_enrich)
    return calls


def _fake_search_with_papers(monkeypatch, sample_papers):
    async def fake_run_search(query, **_kwargs):
        return PaperCollection(query=query, papers=tuple(sample_papers))

    async def fake_shutdown():
        return None

    monkeypatch.setattr(cli_module, "run_search", fake_run_search)
    monkeypatch.setattr(cli_module, "shutdown_clients", fake_shutdown)


def test_cli_auto_enriches_when_api_key_set(tmp_path, monkeypatch, sample_papers):
    """ANTHROPIC_API_KEY in env + no --lightweight = auto-enrich fires."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    _fake_search_with_papers(monkeypatch, sample_papers)
    calls = _stub_enrich_collection(monkeypatch)
    code = cli_module.main(
        ["--query", "x", "--source", "arxiv", "--out", str(tmp_path), "--export", "bib"]
    )
    assert code == 0
    assert calls == ["called"]


def test_cli_lightweight_skips_auto_enrich(tmp_path, monkeypatch, sample_papers):
    """--lightweight wins over the auto-enrich default."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    _fake_search_with_papers(monkeypatch, sample_papers)
    calls = _stub_enrich_collection(monkeypatch)
    code = cli_module.main(
        [
            "--query", "x", "--source", "arxiv",
            "--lightweight",
            "--out", str(tmp_path), "--export", "bib",
        ]
    )
    assert code == 0
    assert calls == []


def test_cli_no_key_does_not_auto_enrich(tmp_path, monkeypatch, sample_papers):
    """No ANTHROPIC_API_KEY → no Anthropic call, lightweight deck."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    _fake_search_with_papers(monkeypatch, sample_papers)
    calls = _stub_enrich_collection(monkeypatch)
    code = cli_module.main(
        ["--query", "x", "--source", "arxiv", "--out", str(tmp_path), "--export", "bib"]
    )
    assert code == 0
    assert calls == []


def test_cli_explicit_enrich_still_works(tmp_path, monkeypatch, sample_papers):
    """--enrich runs even without a key in env (the explicit path used to
    error inside the API client; here we only check the CLI dispatch)."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    _fake_search_with_papers(monkeypatch, sample_papers)
    calls = _stub_enrich_collection(monkeypatch)
    code = cli_module.main(
        [
            "--query", "x", "--source", "arxiv", "--enrich",
            "--out", str(tmp_path), "--export", "bib",
        ]
    )
    assert code == 0
    assert calls == ["called"]


def test_cli_resolve_enrich_mode_branches(monkeypatch):
    """Pure-helper sanity check on the mode resolver."""
    from argparse import Namespace

    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    assert cli_module._resolve_enrich_mode(  # noqa: SLF001
        Namespace(enrich=False, lightweight=False)
    ) == "skip-no-key"
    monkeypatch.setenv("ANTHROPIC_API_KEY", "k")
    assert cli_module._resolve_enrich_mode(  # noqa: SLF001
        Namespace(enrich=False, lightweight=False)
    ) == "auto"
    assert cli_module._resolve_enrich_mode(  # noqa: SLF001
        Namespace(enrich=False, lightweight=True)
    ) == "skip-lightweight"
    assert cli_module._resolve_enrich_mode(  # noqa: SLF001
        Namespace(enrich=True, lightweight=False)
    ) == "explicit"


def test_cli_pdf_mode_skips_paywall_gate_and_download(tmp_path, monkeypatch):
    """--pdf must not run the paywall gate or the network PDF downloader.

    Both would be wrong: the user already supplied the PDF, and the
    downloader would try to fetch a file:// URL through the HTTPS-only
    transport and fail."""
    _stub_pdf_extract(monkeypatch)
    src = tmp_path / "input.pdf"
    _write_fake_pdf(src)
    out = tmp_path / "out"

    download_calls: list[str] = []

    async def fake_download(_collection, _out_dir):
        download_calls.append("called")
        return []

    def boom_prompt(_prompt=""):
        raise AssertionError("paywall prompt fired for --pdf mode")

    async def fake_shutdown() -> None:
        return None

    monkeypatch.setattr(cli_module, "download_pdfs", fake_download)
    monkeypatch.setattr("builtins.input", boom_prompt)
    monkeypatch.setattr(cli_module, "shutdown_clients", fake_shutdown)
    code = cli_module.main(["--pdf", str(src), "--out", str(out)])
    assert code == 0
    assert download_calls == []


def test_cli_single_paper_mode_aborts_without_pdf(
    tmp_path, monkeypatch, sample_papers
):
    """--paper mode must error when the single paper's PDF is not retrievable."""
    from thesisagents.core.models import PaperCollection, Query
    from thesisagents.core.pdf_download import PdfDownloadResult

    paper_no_pdf = _build_paper("nope", pdf_url=None)

    async def fake_single(identifier):
        query = Query(
            keywords=identifier.value, sources=("arxiv",), max_results=1
        )
        return PaperCollection(query=query, papers=(paper_no_pdf,))

    async def fake_shutdown():
        return None

    async def selective_download(collection, out_dir):  # noqa: ARG001
        return [
            PdfDownloadResult(
                paper_key=p.bibtex_key(),
                path=None,
                skipped_reason="no_pdf_url",
            )
            for p in collection.papers
        ]

    monkeypatch.setattr(cli_module, "run_single_paper", fake_single)
    monkeypatch.setattr(cli_module, "shutdown_clients", fake_shutdown)
    monkeypatch.setattr(cli_module, "download_pdfs", selective_download)
    code = cli_module.main(
        ["--paper", "2401.08741", "--out", str(tmp_path), "--yes"]
    )
    assert code == 1


