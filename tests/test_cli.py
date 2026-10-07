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
    """Stub cli's run_search + shutdown_clients and return a dict that captures
    the Query passed to run_search (``patched_pipeline["query"]``).

    Tests that only need the pipeline stubbed ignore the return value; tests
    that assert on the constructed Query read ``patched_pipeline["query"]``
    instead of each re-rolling their own ``fake_run_search`` / ``fake_shutdown``
    boilerplate.
    """
    captured: dict[str, Query] = {}

    async def fake_run_search(query, **_kwargs):  # NOSONAR async stub
        captured["query"] = query
        return PaperCollection(query=query, papers=tuple(sample_papers))

    async def fake_shutdown():  # NOSONAR async stub
        return None

    monkeypatch.setattr(cli_module, "run_search", fake_run_search)
    monkeypatch.setattr(cli_module, "shutdown_clients", fake_shutdown)
    # Leave the autouse ``_stub_download_pdfs`` in place so the new per-paper
    # PPT gate sees every paper as downloadable.
    return captured


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


def test_cli_source_default_is_multi_source(tmp_path, patched_pipeline):
    """When --source is omitted, run_search must be invoked across the
    DEFAULT_SOURCES mix, not just arxiv."""
    from thesisagents.core.constants import DEFAULT_SOURCES

    code = cli_module.main(
        ["--query", "x", "--out", str(tmp_path), "--export", "bib"]
    )
    assert code == 0
    assert patched_pipeline["query"].sources == DEFAULT_SOURCES


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


def test_cli_exclude_source_prunes_default_mix(tmp_path, patched_pipeline):
    """--exclude-source subtracts from the resolved mix; the no-VPN path drops
    only ieee and keeps every other default source."""
    from thesisagents.core.constants import DEFAULT_SOURCES

    code = cli_module.main(
        ["--query", "x", "--out", str(tmp_path), "--export", "bib",
         "--exclude-source", "ieee"]
    )
    assert code == 0
    assert "ieee" not in patched_pipeline["query"].sources
    expected = tuple(s for s in DEFAULT_SOURCES if s != "ieee")
    assert patched_pipeline["query"].sources == expected


def test_cli_min_citations_flows_into_query(tmp_path, patched_pipeline):
    """--min-citations is parsed and passed through to the Query (it was
    previously unreachable from the CLI)."""
    code = cli_module.main(
        ["--query", "x", "--out", str(tmp_path), "--export", "bib",
         "--min-citations", "50"]
    )
    assert code == 0
    assert patched_pipeline["query"].min_citations == 50


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


def test_cli_top_tier_filter_off_by_default(tmp_path, patched_pipeline):
    """top_tier_only is OFF by default (broader coverage including IEEE / ACM
    workshops); --top-tier-only flips it on."""
    code = cli_module.main(
        ["--query", "x", "--out", str(tmp_path), "--export", "bib"]
    )
    assert code == 0
    assert patched_pipeline["query"].top_tier_only is False

    patched_pipeline.clear()
    code = cli_module.main(
        ["--query", "x", "--top-tier-only", "--out", str(tmp_path), "--export", "bib"]
    )
    assert code == 0
    assert patched_pipeline["query"].top_tier_only is True


def test_cli_default_triggers_pdf_download(tmp_path, monkeypatch, patched_pipeline):
    """Default flag set should invoke download_pdfs; --no-pdf disables it."""
    calls: list[str] = []

    async def fake_download(_collection, _out_dir):  # NOSONAR async stub
        calls.append("called")
        return []

    monkeypatch.setattr(cli_module, "download_pdfs", fake_download)
    code = cli_module.main(
        ["--query", "x", "--source", "arxiv", "--out", str(tmp_path), "--export", "bib"]
    )
    assert code == 0
    assert calls == ["called"]


def test_cli_no_pdf_flag_skips_download(tmp_path, monkeypatch, patched_pipeline):
    calls: list[str] = []

    async def fake_download(_collection, _out_dir):  # NOSONAR async stub
        calls.append("called")
        return []

    monkeypatch.setattr(cli_module, "download_pdfs", fake_download)
    code = cli_module.main(
        ["--query", "x", "--source", "arxiv", "--no-pdf",
         "--out", str(tmp_path), "--export", "bib"]
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


def test_cli_auto_enriches_when_api_key_set(tmp_path, monkeypatch, patched_pipeline):
    """ANTHROPIC_API_KEY in env + no --lightweight = auto-enrich fires."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    calls = _stub_enrich_collection(monkeypatch)
    code = cli_module.main(
        ["--query", "x", "--source", "arxiv", "--out", str(tmp_path), "--export", "bib"]
    )
    assert code == 0
    assert calls == ["called"]


def test_cli_lightweight_skips_auto_enrich(tmp_path, monkeypatch, patched_pipeline):
    """--lightweight wins over the auto-enrich default."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
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


def test_cli_no_key_does_not_auto_enrich(tmp_path, monkeypatch, patched_pipeline):
    """No ANTHROPIC_API_KEY → no Anthropic call, lightweight deck."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    calls = _stub_enrich_collection(monkeypatch)
    code = cli_module.main(
        ["--query", "x", "--source", "arxiv", "--out", str(tmp_path), "--export", "bib"]
    )
    assert code == 0
    assert calls == []


def test_cli_explicit_enrich_still_works(tmp_path, monkeypatch, patched_pipeline):
    """--enrich runs even without a key in env (the explicit path used to
    error inside the API client; here we only check the CLI dispatch)."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
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




def test_cli_export_pdf_downloads_instead_of_failing(tmp_path, patched_pipeline):
    """``--export pdf`` is advertised by --list-exports and must actually run.

    ``pdf`` names the PDF *download* stage, not a rendered artefact — there is
    no pdf exporter class. Left in the format list it reached
    ``export_collection`` and raised "no exporter registered for this format",
    but only AFTER the whole search and download had already run.
    """
    code = cli_module.main(
        [
            "--query", "attention",
            "--source", "arxiv",
            "--export", "pdf,bib",
            "--out", str(tmp_path),
            "--filename-stem", "pdfmode",
        ]
    )
    assert code == 0
    assert (tmp_path / "pdfmode.bib").exists()
    assert not (tmp_path / "pdfmode.pdf").exists()  # never a rendered artefact
    assert list((tmp_path / "pdfs").glob("*.pdf"))  # the download stage ran


def test_cli_export_pdf_alone_is_a_download_only_run(tmp_path, patched_pipeline):
    """``--export pdf`` on its own means "just fetch the PDFs"."""
    code = cli_module.main(
        [
            "--query", "attention",
            "--source", "arxiv",
            "--export", "pdf",
            "--out", str(tmp_path),
        ]
    )
    assert code == 0
    assert list((tmp_path / "pdfs").glob("*.pdf"))


# ---------------------------------------------------------------------------
# Identifier preflight (--no-verify-identifiers)
# ---------------------------------------------------------------------------


def _collection_with_doi(doi: str) -> PaperCollection:
    from thesisagents.core.models import Paper

    paper = Paper(
        source="arxiv", source_id="p1", title="Preflight Probe Paper",
        authors=("Ada Author",), year=2024, venue=None, abstract="An abstract.",
        url="https://example.org/p1", doi=doi,
        pdf_url="https://example.org/p1.pdf",
    )
    query = Query(keywords="preflight", sources=("arxiv",), max_results=5)
    return PaperCollection(query=query, papers=(paper,))


@pytest.fixture()
def pipeline_returning(monkeypatch):
    """Make the CLI's search return a given collection, with no client shutdown."""

    def _install(collection: PaperCollection) -> None:
        async def fake_run_search(query, **_kwargs):  # NOSONAR async stub
            return collection

        async def fake_shutdown():  # NOSONAR async stub
            return None

        monkeypatch.setattr(cli_module, "run_search", fake_run_search)
        monkeypatch.setattr(cli_module, "shutdown_clients", fake_shutdown)

    return _install


def test_cli_reports_verified_identifiers(tmp_path, patched_pipeline, capsys):
    code = cli_module.main(
        ["--query", "x", "--source", "arxiv", "--export", "bib", "--out", str(tmp_path)]
    )
    assert code == 0
    # sample_papers: two URLs and one DOI, all answered "ok" by the offline stub.
    assert "Identifiers: 3 verified, 0 not checkable, 0 failed." in capsys.readouterr().out


def test_cli_stops_on_a_bad_identifier_before_downloading(
    tmp_path, pipeline_returning, monkeypatch, capsys
):
    """A wrong DOI fails the run right after the search: exit 2, no PDF
    download, no export file."""
    pipeline_returning(_collection_with_doi("10.x/typed-from-memory"))
    downloads: list[object] = []

    async def recording_download(collection, out_dir):
        downloads.append(collection)
        return []

    monkeypatch.setattr(cli_module, "download_pdfs", recording_download)
    code = cli_module.main(
        ["--query", "x", "--source", "arxiv", "--out", str(tmp_path), "--yes"]
    )
    assert code == 2
    err = capsys.readouterr().err
    assert "identifier verification failed" in err
    assert "10.x/typed-from-memory is invalid" in err
    assert "--no-verify-identifiers" in err
    assert downloads == []
    assert [p for p in tmp_path.rglob("*") if p.is_file()] == []


def test_cli_no_verify_identifiers_exports_and_says_so(
    tmp_path, pipeline_returning, capsys
):
    pipeline_returning(_collection_with_doi("10.x/typed-from-memory"))
    code = cli_module.main(
        [
            "--query", "x", "--source", "arxiv", "--export", "bib",
            "--out", str(tmp_path), "--no-verify-identifiers", "--quiet",
        ]
    )
    assert code == 0
    captured = capsys.readouterr()
    # Printed even under --quiet: skipping the check must be visible.
    assert "Identifier verification is OFF (--no-verify-identifiers)" in captured.err
    assert "Identifiers:" not in captured.out
    assert len(list(tmp_path.glob("*.bib"))) == 1


def test_cli_checks_each_identifier_once_across_per_paper_decks(
    tmp_path, patched_pipeline, monkeypatch
):
    """The run-wide cache: the early check asks, the aggregate export and the
    two per-paper deck exports reuse the answers."""
    from thesisagents.core import export_validation

    asked: list[list[tuple[str, str]]] = []

    async def counting_resolver(targets):
        asked.append(list(targets))
        return {
            target: export_validation.Verdict(export_validation.VerificationStatus.OK)
            for target in targets
        }

    monkeypatch.setattr(export_validation, "_resolve_targets", counting_resolver)
    code = cli_module.main(
        ["--query", "x", "--source", "arxiv", "--out", str(tmp_path), "--yes"]
    )
    assert code == 0
    assert len(list(tmp_path.glob("*.pptx"))) == 2  # one deck per paper
    assert len(asked) == 1
    assert len(asked[0]) == 3


def test_cli_verify_identifiers_defaults_on():
    parser = cli_module.build_parser()
    assert parser.parse_args(["--query", "x"]).verify_identifiers is True
    assert (
        parser.parse_args(["--query", "x", "--no-verify-identifiers"]).verify_identifiers
        is False
    )


# ---------------------------------------------------------------------------
# --diagnostics
# ---------------------------------------------------------------------------


def _diagnosed(papers, keywords: str = "attention") -> PaperCollection:
    """A collection the way ``run_search`` returns it: ranked, with diagnostics."""
    from thesisagents.core import pipeline
    from thesisagents.core.ranking import rank_with_scores

    ranked = rank_with_scores(papers, keywords, current_year=2026)
    query = Query(keywords=keywords, sources=("arxiv",), max_results=5)
    return PaperCollection(
        query=query,
        papers=tuple(entry.paper for entry in ranked),
        diagnostics=pipeline._diagnose(ranked),  # noqa: SLF001
    )


def test_cli_diagnostics_prints_and_writes_the_breakdown(
    tmp_path, pipeline_returning, sample_papers, capsys
):
    import json

    pipeline_returning(_diagnosed(sample_papers))
    code = cli_module.main(
        [
            "--query", "attention", "--source", "arxiv", "--export", "bib",
            "--out", str(tmp_path), "--diagnostics",
        ]
    )
    assert code == 0
    out = capsys.readouterr().out
    assert "Ranking diagnostics for: attention" in out
    assert "[  1] keep " in out
    assert "[  2] prune " in out
    assert "total " in out and "= relevance " in out
    # Reasons are spelled out only for papers that are not "keep".
    assert "        - no query term appears in the title or abstract" in out
    assert "        rule: prune_below_relevance=0.10" in out
    assert "title matches 1 of 1 query terms" not in out
    assert "Recommendations: 1 keep, 0 review, 1 prune. Advice only, nothing was removed." in out

    report = json.loads((tmp_path / "diagnostics.json").read_text(encoding="utf-8"))
    assert report["summary"] == {"keep": 1, "review": 0, "prune": 1}
    assert [p["bibtex_key"] for p in report["papers"]] == [
        sample_papers[0].bibtex_key(), sample_papers[1].bibtex_key()
    ]
    # The file holds the full reasons for every paper, including "keep".
    assert report["papers"][0]["score"]["reasons"][0].startswith(
        "title matches 1 of 1 query terms (attention)"
    )
    # Advice only: the pruned paper is still exported.
    bib = next(tmp_path.glob("*.bib")).read_text(encoding="utf-8")
    assert bib.count("@") == 2


def test_cli_without_diagnostics_writes_no_report(
    tmp_path, pipeline_returning, sample_papers, capsys
):
    pipeline_returning(_diagnosed(sample_papers))
    code = cli_module.main(
        ["--query", "attention", "--source", "arxiv", "--export", "bib", "--out", str(tmp_path)]
    )
    assert code == 0
    assert "Ranking diagnostics" not in capsys.readouterr().out
    assert not (tmp_path / "diagnostics.json").exists()


def test_cli_diagnostics_quiet_still_writes_the_file(
    tmp_path, pipeline_returning, sample_papers, capsys
):
    pipeline_returning(_diagnosed(sample_papers))
    code = cli_module.main(
        [
            "--query", "attention", "--source", "arxiv", "--export", "bib",
            "--out", str(tmp_path), "--diagnostics", "--quiet",
        ]
    )
    assert code == 0
    assert "Ranking diagnostics" not in capsys.readouterr().out
    assert (tmp_path / "diagnostics.json").exists()


def test_cli_diagnostics_says_when_a_run_has_none(tmp_path, monkeypatch, sample_papers, capsys):
    """--paper fetches one paper by ID: there is no query to be relevant to."""

    async def fake_single(identifier: PaperIdentifier) -> PaperCollection:
        query = Query(keywords=identifier.value, sources=("arxiv",), max_results=1)
        return PaperCollection(query=query, papers=(sample_papers[0],))

    async def fake_shutdown() -> None:
        return None

    monkeypatch.setattr(cli_module, "run_single_paper", fake_single)
    monkeypatch.setattr(cli_module, "shutdown_clients", fake_shutdown)
    code = cli_module.main(
        ["--paper", "2401.08741", "--export", "bib", "--out", str(tmp_path), "--diagnostics"]
    )
    assert code == 0
    assert "No ranking diagnostics for this run" in capsys.readouterr().err
    assert not (tmp_path / "diagnostics.json").exists()


def test_cli_diagnostics_survive_the_per_paper_deck_path(
    tmp_path, pipeline_returning, sample_papers
):
    """The per-paper path rebuilds the collection from the downloadable papers.
    The report is written before that, from the full ranked result."""
    import json

    pipeline_returning(_diagnosed(sample_papers))
    code = cli_module.main(
        ["--query", "attention", "--source", "arxiv", "--out", str(tmp_path),
         "--diagnostics", "--yes"]
    )
    assert code == 0
    report = json.loads((tmp_path / "diagnostics.json").read_text(encoding="utf-8"))
    assert len(report["papers"]) == 2
    assert len(list(tmp_path.glob("*.pptx"))) == 2


# ---------------------------------------------------------------------------
# Per-source statistics printout
# ---------------------------------------------------------------------------


def _collection_with_stats(papers) -> PaperCollection:
    from thesisagents.core.diagnostics import (
        SearchDiagnostics,
        SourceStat,
        SourceStatus,
    )

    stats = (
        SourceStat("arxiv", requested=25, returned=23, after_dedup=19),
        SourceStat(
            "semantic_scholar", requested=25, returned=0, after_dedup=0,
            status=SourceStatus.RATE_LIMITED,
            detail="gave up after 3 rate-limit retries: [semantic_scholar] slow down",
        ),
        SourceStat(
            "springer", requested=25, returned=0, after_dedup=0,
            status=SourceStatus.DISABLED, detail="x" * 300,
        ),
        SourceStat("dblp", requested=25, returned=0, after_dedup=0),
    )
    query = Query(keywords="attention", sources=("arxiv",), max_results=25)
    return PaperCollection(
        query=query, papers=tuple(papers),
        diagnostics=SearchDiagnostics(source_stats=stats),
    )


def test_cli_prints_what_each_source_returned(
    tmp_path, pipeline_returning, sample_papers, capsys
):
    pipeline_returning(_collection_with_stats(sample_papers))
    code = cli_module.main(
        ["--query", "attention", "--source", "arxiv", "--export", "bib", "--out", str(tmp_path)]
    )
    assert code == 0
    lines = capsys.readouterr().out.splitlines()
    start = lines.index("Sources (up to 25 requested from each):")
    block = lines[start + 1 : start + 5]
    assert block[0] == "  arxiv              23 returned, 19 after dedup"
    assert block[1] == (
        "  semantic_scholar    0 returned  rate_limited: gave up after 3 "
        "rate-limit retries: [semantic_scholar] slow down"
    )
    assert block[2].startswith("  springer            0 returned  disabled: xxx")
    assert block[2].endswith("…")
    assert len(block[2]) == len("  springer            0 returned  disabled: ") + 100
    assert block[3] == "  dblp                0 returned, 0 after dedup"


def test_cli_quiet_hides_the_source_block(
    tmp_path, pipeline_returning, sample_papers, capsys
):
    pipeline_returning(_collection_with_stats(sample_papers))
    code = cli_module.main(
        ["--query", "attention", "--source", "arxiv", "--export", "bib",
         "--out", str(tmp_path), "--quiet"]
    )
    assert code == 0
    assert "Sources (up to" not in capsys.readouterr().out


def test_cli_prints_no_source_block_without_counts(tmp_path, patched_pipeline, capsys):
    """``patched_pipeline`` returns a bare collection, as --paper and --pdf do."""
    code = cli_module.main(
        ["--query", "x", "--source", "arxiv", "--export", "bib", "--out", str(tmp_path)]
    )
    assert code == 0
    assert "Sources (up to" not in capsys.readouterr().out


def test_cli_diagnostics_file_includes_the_source_stats(
    tmp_path, pipeline_returning, sample_papers
):
    import json

    pipeline_returning(_collection_with_stats(sample_papers))
    code = cli_module.main(
        ["--query", "attention", "--source", "arxiv", "--export", "bib",
         "--out", str(tmp_path), "--diagnostics", "--quiet"]
    )
    assert code == 0
    report = json.loads((tmp_path / "diagnostics.json").read_text(encoding="utf-8"))
    assert [stat["source"] for stat in report["source_stats"]] == [
        "arxiv", "semantic_scholar", "springer", "dblp"
    ]
    assert report["source_stats"][0]["after_dedup"] == 19


# ---------------------------------------------------------------------------
# --snowball
# ---------------------------------------------------------------------------


class _GraphProvider:
    """Citation provider answering from a dict keyed by ``(source_id, direction)``."""

    def __init__(self, graph, name="openalex", fail_with=None):
        self.name = name
        self._graph = graph
        self._fail_with = fail_with
        self.calls: list[tuple[str, str, int]] = []

    async def _answer(self, paper, direction, limit):
        self.calls.append((paper.source_id, direction, limit))
        if self._fail_with is not None:
            raise self._fail_with
        return list(self._graph.get((paper.source_id, direction), []))

    async def references(self, paper, limit):
        return await self._answer(paper, "references", limit)

    async def cited_by(self, paper, limit):
        return await self._answer(paper, "cited_by", limit)


def _found(sid: str, title: str):
    from thesisagents.core.models import Paper

    return Paper(
        source="openalex", source_id=sid, title=title, authors=("Ada Author",),
        year=2024, venue=None, abstract="An abstract.",
        url=f"https://example.org/{sid}", doi=f"10.1000/{sid}",
        pdf_url=f"https://example.org/{sid}.pdf",
    )


@pytest.fixture()
def citation_graph(monkeypatch, sample_papers):
    seed_id = sample_papers[0].source_id
    provider = _GraphProvider(
        {
            (seed_id, "references"): [_found("r1", "Attention Mechanisms Reviewed")],
            (seed_id, "cited_by"): [
                _found("c1", "Sparse Attention at Scale"),
                _found("c2", "Cooking With Gas"),
            ],
        }
    )
    monkeypatch.setattr("thesisagents.core.snowball._default_providers", lambda: [provider])
    return provider


def test_cli_snowball_appends_the_discovered_papers_to_the_export(
    tmp_path, patched_pipeline, citation_graph, sample_papers, capsys
):
    code = cli_module.main(
        ["--query", "attention", "--source", "arxiv", "--export", "bib",
         "--out", str(tmp_path), "--snowball", "both", "--snowball-seeds", "1"]
    )
    assert code == 0
    out = capsys.readouterr().out
    assert "Snowball (both, depth 1) from 1 seed(s): 3 new paper(s), 3 citation link(s)." in out
    assert "  + Attention Mechanisms Reviewed" in out
    seed_key = sample_papers[0].bibtex_key()
    assert f"      references of {seed_key} (openalex, depth 1)" in out
    assert f"      cited_by of {seed_key} (openalex, depth 1)" in out
    bib = next(tmp_path.glob("*.bib")).read_text(encoding="utf-8")
    assert bib.count("@") == 5          # 2 search results + 3 discovered
    assert "Sparse Attention at Scale" in bib
    # The discovered papers are verified like any other: 2 URLs + 1 DOI from
    # the search, 3 URLs + 3 DOIs from the snowball.
    assert "Identifiers: 9 verified" in out


def test_cli_snowball_is_off_by_default(tmp_path, patched_pipeline, citation_graph, capsys):
    code = cli_module.main(
        ["--query", "attention", "--source", "arxiv", "--export", "bib", "--out", str(tmp_path)]
    )
    assert code == 0
    assert citation_graph.calls == []
    assert "Snowball" not in capsys.readouterr().out


def test_cli_snowball_passes_the_flags_through(
    tmp_path, patched_pipeline, citation_graph, sample_papers
):
    code = cli_module.main(
        ["--query", "attention", "--source", "arxiv", "--export", "bib",
         "--out", str(tmp_path), "--snowball", "cited_by", "--snowball-seeds", "1",
         "--snowball-max-per-seed", "7", "--snowball-max-total", "1", "--quiet"]
    )
    assert code == 0
    assert citation_graph.calls == [(sample_papers[0].source_id, "cited_by", 7)]
    assert next(tmp_path.glob("*.bib")).read_text(encoding="utf-8").count("@") == 3


def test_cli_snowball_min_relevance_drops_off_topic_papers(
    tmp_path, patched_pipeline, citation_graph
):
    code = cli_module.main(
        ["--query", "attention", "--source", "arxiv", "--export", "bib",
         "--out", str(tmp_path), "--snowball", "both", "--snowball-seeds", "1",
         "--snowball-min-relevance", "0.3", "--quiet"]
    )
    assert code == 0
    bib = next(tmp_path.glob("*.bib")).read_text(encoding="utf-8")
    assert "Sparse Attention at Scale" in bib
    assert "Cooking With Gas" not in bib


def test_cli_snowball_says_when_the_cap_stopped_it(
    tmp_path, patched_pipeline, citation_graph, capsys
):
    code = cli_module.main(
        ["--query", "attention", "--source", "arxiv", "--export", "bib",
         "--out", str(tmp_path), "--snowball", "both", "--snowball-seeds", "1",
         "--snowball-max-total", "2"]
    )
    assert code == 0
    assert "Stopped at --snowball-max-total 2" in capsys.readouterr().out


def test_cli_snowball_reports_a_failing_provider_and_still_exports(
    tmp_path, patched_pipeline, monkeypatch, capsys
):
    from thesisagents.core.exceptions import SourceUnavailableError

    broken = _GraphProvider({}, fail_with=SourceUnavailableError("openalex", "HTTP 503"))
    monkeypatch.setattr("thesisagents.core.snowball._default_providers", lambda: [broken])
    code = cli_module.main(
        ["--query", "attention", "--source", "arxiv", "--export", "bib",
         "--out", str(tmp_path), "--snowball", "references", "--quiet"]
    )
    assert code == 0
    err = capsys.readouterr().err
    assert "snowball: openalex references lookup failed" in err   # shown despite --quiet
    assert next(tmp_path.glob("*.bib")).read_text(encoding="utf-8").count("@") == 2


def test_cli_snowball_records_the_links_in_the_diagnostics_file(
    tmp_path, pipeline_returning, citation_graph, sample_papers
):
    import json

    pipeline_returning(_diagnosed(sample_papers))
    code = cli_module.main(
        ["--query", "attention", "--source", "arxiv", "--export", "bib",
         "--out", str(tmp_path), "--snowball", "references", "--snowball-seeds", "1",
         "--diagnostics", "--quiet"]
    )
    assert code == 0
    report = json.loads((tmp_path / "diagnostics.json").read_text(encoding="utf-8"))
    assert report["relations"] == [
        {"source_key": sample_papers[0].dedup_key(), "target_key": "doi:10.1000/r1",
         "relation": "references", "provider": "openalex", "depth": 1}
    ]
    assert [entry["rank"] for entry in report["papers"]] == [1, 2, 3]
    discovered = report["papers"][2]
    assert discovered["title"] == "Attention Mechanisms Reviewed"
    assert discovered["score"]["matched_terms"] == ["attention"]
    assert discovered["recommendation"]["action"] == "keep"


@pytest.mark.parametrize(
    ("flags", "message"),
    [
        (["--snowball-depth", "9"], "--snowball-depth must be in 1..3"),
        (["--snowball-depth", "0"], "--snowball-depth must be in 1..3"),
        (["--snowball-seeds", "0"], "--snowball-seeds must be in 1..200"),
        (["--snowball-max-per-seed", "101"], "--snowball-max-per-seed must be in 1..100"),
        (["--snowball-max-total", "1001"], "--snowball-max-total must be in 1..1000"),
        (["--snowball-min-relevance", "1.5"], "--snowball-min-relevance must be in 0..1"),
    ],
)
def test_cli_snowball_rejects_a_bad_bound_before_searching(
    tmp_path, patched_pipeline, flags, message
):
    with pytest.raises(SystemExit) as raised:
        cli_module.main(
            ["--query", "x", "--source", "arxiv", "--out", str(tmp_path),
             "--snowball", "both", *flags]
        )
    assert str(raised.value) == message
    assert "query" not in patched_pipeline   # the search never ran


def test_cli_snowball_bounds_are_ignored_when_snowball_is_off(tmp_path, patched_pipeline):
    code = cli_module.main(
        ["--query", "x", "--source", "arxiv", "--export", "bib", "--out", str(tmp_path),
         "--snowball-depth", "9"]
    )
    assert code == 0


def test_cli_snowball_min_relevance_needs_a_query(tmp_path, monkeypatch, sample_papers):
    with pytest.raises(SystemExit, match="cannot be used with --paper or --pdf"):
        cli_module.main(
            ["--paper", "2401.08741", "--out", str(tmp_path), "--snowball", "both",
             "--snowball-min-relevance", "0.3"]
        )


def test_cli_snowball_rejects_an_unknown_direction(tmp_path):
    with pytest.raises(SystemExit):
        cli_module.main(
            ["--query", "x", "--out", str(tmp_path), "--snowball", "sideways"]
        )


def test_cli_snowball_from_a_single_paper_keeps_discovery_order(
    tmp_path, monkeypatch, sample_papers, citation_graph, capsys
):
    """--paper has no keywords, so nothing is scored and nothing reordered."""

    async def fake_single(identifier: PaperIdentifier) -> PaperCollection:
        query = Query(keywords=identifier.value, sources=("arxiv",), max_results=1)
        return PaperCollection(query=query, papers=(sample_papers[0],))

    async def fake_shutdown() -> None:
        return None

    monkeypatch.setattr(cli_module, "run_single_paper", fake_single)
    monkeypatch.setattr(cli_module, "shutdown_clients", fake_shutdown)
    code = cli_module.main(
        ["--paper", "2401.08741", "--export", "bib", "--out", str(tmp_path),
         "--snowball", "both"]
    )
    assert code == 0
    out = capsys.readouterr().out
    order = [out.index(title) for title in (
        "Attention Mechanisms Reviewed", "Sparse Attention at Scale", "Cooking With Gas",
    )]
    assert order == sorted(order)
