"""Export preflight: check every paper's DOI and URL before an exporter runs.

Why this exists
---------------
The project rule "never invent a URL / DOI, copy it from the search results"
was only a documented authoring rule. Nothing at run time stopped a
hand-written ``Paper`` carrying a DOI that was typed from memory, so a
fabricated identifier could reach a ``.bib`` file or a references slide. This
module turns the rule into a gate that ``export_collection`` runs first.

What is checked
---------------
* **DOI**: syntax first, with no network (``10.<registrant>/<suffix>``), then
  existence through the doi.org handle API (``/api/handles/<doi>``). The handle
  API answers from the DOI registry itself, so the check never touches the
  publisher's site and cannot be blocked by a publisher bot wall.
* **URL**: one streamed ``GET`` (headers only), following redirects by hand.
  A paper's URL on a browser-only publisher host (IEEE Xplore, ACM DL, …) is
  not probed at all: those hosts reject plain HTTP clients and the project
  routes them through a real browser. The DOI check covers such a paper.

Outcomes (``VerificationStatus``)
---------------------------------
``ok``           the identifier exists.
``invalid``      the identifier is definitely wrong: malformed DOI, DOI unknown
                 to doi.org, URL answering 404 / 410.
``unreachable``  no definite answer: DNS / connection failure, HTTP 5xx.
``timeout``      the request timed out.
``skipped``      not checked, with the reason in ``detail``: a ``file://`` URL,
                 a browser-only publisher host, a server that refuses automated
                 access (HTTP 401 / 403 / 429).

``invalid``, ``unreachable`` and ``timeout`` block a strict export. ``skipped``
never does: "could not check" is not evidence the identifier is wrong.

The paper's own ``doi`` and ``url`` are never rewritten. A redirect target or a
DOI's registered landing page is reported separately as ``resolved_url``.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
from collections.abc import AsyncIterator, Iterable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Protocol
from urllib.parse import quote, urljoin, urlsplit, urlunsplit

import httpx

from thesisagents.core.exceptions import ExportError
from thesisagents.core.identifiers import canonical_doi
from thesisagents.core.models import Paper, PaperCollection
from thesisagents.fetchers.http import scoped_client
from thesisagents.fetchers.webrunner_pdf import should_use_webrunner
from thesisagents.utils.async_helpers import run_blocking
from thesisagents.utils.logging import get_logger

_LOG = get_logger(__name__)

KIND_DOI = "doi"
KIND_URL = "url"

_SOURCE_NAME = "identifier_preflight"
_DOI_HANDLE_ENDPOINT = "https://doi.org/api/handles/"
_DOI_HOSTS = frozenset({"doi.org", "dx.doi.org", "www.doi.org"})

#: Short on purpose: the preflight runs in front of every export, so one slow
#: host must cost seconds, not the 30 s the search clients allow.
_TIMEOUT_SECONDS = 8.0
#: One retry for a timeout / connection failure / 5xx. A strict gate that
#: blocks an export on a single dropped packet would teach users to switch it
#: off, so a transient failure gets a second chance before it counts.
_ATTEMPTS = 2
_MAX_REDIRECTS = 5
#: Simultaneous probes overall, and against any one host. A 25-paper export
#: sends most DOI lookups to doi.org and most arXiv URLs to arxiv.org, so the
#: per-host cap is what keeps the burst polite.
_CONCURRENCY = 5
_PER_HOST_CONCURRENCY = 2
_DETAIL_MAX_CHARS = 200

_HTTP_NOT_FOUND = frozenset({404, 410})
_HTTP_REDIRECTS = frozenset({301, 302, 303, 307, 308})
_HTTP_SERVER_ERROR_FLOOR = 500
_HTTP_CLIENT_ERROR_FLOOR = 400
#: doi.org handle API ``responseCode`` values (the HTTP status is not enough:
#: a handle that exists but carries no values also answers 404).
_HANDLE_FOUND = 1
_HANDLE_NOT_FOUND = 100
_HANDLE_VALUES_NOT_FOUND = 200


class VerificationStatus(StrEnum):
    """Outcome of checking one identifier. See the module docstring."""

    OK = "ok"
    INVALID = "invalid"
    UNREACHABLE = "unreachable"
    TIMEOUT = "timeout"
    SKIPPED = "skipped"


_BLOCKING = frozenset(
    {
        VerificationStatus.INVALID,
        VerificationStatus.UNREACHABLE,
        VerificationStatus.TIMEOUT,
    }
)
_RETRYABLE = frozenset({VerificationStatus.UNREACHABLE, VerificationStatus.TIMEOUT})


@dataclass(frozen=True, slots=True)
class Verdict:
    """What one probe found, independent of which paper asked.

    Kept separate from :class:`IdentifierCheck` so it can be cached: two papers
    citing the same DOI share one ``Verdict``.
    """

    status: VerificationStatus
    resolved_url: str | None = None
    detail: str = ""


@dataclass(frozen=True, slots=True)
class IdentifierCheck:
    """One identifier of one paper, with its verdict.

    ``value`` is the identifier exactly as the paper carries it. It is never
    replaced by ``resolved_url``: a redirect target is where the link leads
    today, not what the bibliography should cite.
    """

    paper_key: str
    title: str
    kind: str
    value: str
    status: VerificationStatus
    resolved_url: str | None = None
    detail: str = ""

    @property
    def blocking(self) -> bool:
        """True when this check stops a strict export."""
        return self.status in _BLOCKING

    def to_dict(self) -> dict[str, Any]:
        return {
            "paper_key": self.paper_key,
            "title": self.title,
            "kind": self.kind,
            "value": self.value,
            "status": self.status.value,
            "resolved_url": self.resolved_url,
            "detail": self.detail,
        }


@dataclass(frozen=True, slots=True)
class VerificationReport:
    """Every check made for one collection, in paper order."""

    checks: tuple[IdentifierCheck, ...] = ()

    @property
    def failures(self) -> tuple[IdentifierCheck, ...]:
        return tuple(check for check in self.checks if check.blocking)

    @property
    def ok(self) -> bool:
        """True when nothing blocks a strict export."""
        return not self.failures

    def counts(self) -> dict[str, int]:
        """Number of checks per status, every status present (0 when unused)."""
        totals = dict.fromkeys((status.value for status in VerificationStatus), 0)
        for check in self.checks:
            totals[check.status.value] += 1
        return totals

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "counts": self.counts(),
            "checks": [check.to_dict() for check in self.checks],
        }

    def failure_message(self) -> str:
        """Multi-line text naming each failed identifier and how to proceed."""
        failures = self.failures
        papers = {check.paper_key for check in failures}
        lines = [
            f"identifier verification failed for {len(failures)} identifier(s) "
            f"in {len(papers)} paper(s):"
        ]
        lines.extend(
            f"  - {check.paper_key}: {check.kind} {check.value} is "
            f"{check.status.value} ({check.detail})"
            for check in failures
        )
        lines.append(
            "Copy each DOI / URL from the search results instead of typing it. "
            "To export without this check (for example offline), pass "
            "--no-verify-identifiers on the CLI, or verify_identifiers=False "
            "to the MCP export tool / ExportOptions."
        )
        return "\n".join(lines)


class IdentifierVerificationError(ExportError):
    """A strict export was stopped by the identifier preflight.

    ``report`` carries every check, so a caller can show the structured result
    instead of parsing the message.
    """

    def __init__(self, report: VerificationReport) -> None:
        super().__init__("preflight", report.failure_message())
        self.report = report


class VerificationCache(Protocol):
    """Where verdicts are remembered between checks.

    ``kind`` is :data:`KIND_DOI` or :data:`KIND_URL`. ``value`` is the probed
    form (a canonical lower-case DOI, or the URL that was requested).
    """

    def get(self, kind: str, value: str) -> Verdict | None:
        """Return the remembered verdict, or ``None`` when there is none."""

    def put(self, kind: str, value: str, verdict: Verdict) -> None:
        """Remember ``verdict`` for later :meth:`get` calls."""


class MemoryVerificationCache:
    """Verdicts kept for the life of one object, usually one CLI run.

    Why: the CLI calls ``export_collection`` once for the aggregate formats and
    then once per paper for the decks. Without a shared cache every paper's DOI
    would be looked up twice in the same run.

    Example::

        cache = MemoryVerificationCache()
        export_collection(collection, options, verification_cache=cache)
        export_collection(one_paper, deck_options, verification_cache=cache)
    """

    def __init__(self) -> None:
        self._verdicts: dict[tuple[str, str], Verdict] = {}

    def get(self, kind: str, value: str) -> Verdict | None:
        return self._verdicts.get((kind, value))

    def put(self, kind: str, value: str, verdict: Verdict) -> None:
        self._verdicts[(kind, value)] = verdict

    def __len__(self) -> int:
        return len(self._verdicts)


# ---------------------------------------------------------------------------
# Planning: decide, per identifier, what needs a network probe
# ---------------------------------------------------------------------------

type _Target = tuple[str, str]


@dataclass(frozen=True, slots=True)
class _Planned:
    """One identifier of one paper before any network call.

    Exactly one of ``verdict`` (decided locally) and ``target`` (needs a
    probe) is set. ``http_upgraded`` marks a plain-``http`` URL whose
    ``https`` form is probed in its place.
    """

    paper_key: str
    title: str
    kind: str
    value: str
    verdict: Verdict | None = None
    target: _Target | None = None
    http_upgraded: bool = False


def _plan_collection(papers: Iterable[Paper]) -> list[_Planned]:
    planned: list[_Planned] = []
    for paper in papers:
        planned.extend(_plan_paper(paper))
    return planned


def _plan_paper(paper: Paper) -> list[_Planned]:
    key = paper.bibtex_key()
    out: list[_Planned] = []
    doi = (paper.doi or "").strip()
    has_valid_doi = False
    if doi:
        canonical = canonical_doi(doi)
        has_valid_doi = canonical is not None
        out.append(_plan_doi(key, paper.title, KIND_DOI, doi, canonical))
    url = (paper.url or "").strip()
    if url:
        out.append(_plan_url(key, paper.title, url, has_valid_doi))
    return out


def _plan_doi(
    key: str, title: str, kind: str, value: str, canonical: str | None
) -> _Planned:
    if canonical is None:
        return _Planned(
            key, title, kind, value,
            verdict=Verdict(
                VerificationStatus.INVALID,
                detail="not a DOI: expected the form 10.<registrant>/<suffix>",
            ),
        )
    return _Planned(key, title, kind, value, target=(KIND_DOI, canonical))


def _plan_url(key: str, title: str, url: str, has_valid_doi: bool) -> _Planned:
    parts = urlsplit(url)
    scheme = parts.scheme.lower()
    host = (parts.hostname or "").lower()
    if scheme not in ("http", "https"):
        return _skipped(key, title, url, "not an http(s) URL, nothing to probe")
    if not host:
        return _Planned(
            key, title, KIND_URL, url,
            verdict=Verdict(VerificationStatus.INVALID, detail="URL has no host"),
        )
    if host in _DOI_HOSTS:
        # A doi.org link is a DOI in URL clothing: check the DOI it names.
        return _plan_doi(key, title, KIND_URL, url, canonical_doi(url))
    if should_use_webrunner(url):
        reason = (
            "publisher page needs a real browser, the DOI check covers this paper"
            if has_valid_doi
            else "publisher page needs a real browser and the paper has no DOI to check"
        )
        return _skipped(key, title, url, reason)
    if scheme == "http":
        upgraded = urlunsplit(("https", *parts[1:]))
        return _Planned(
            key, title, KIND_URL, url, target=(KIND_URL, upgraded), http_upgraded=True
        )
    return _Planned(key, title, KIND_URL, url, target=(KIND_URL, url))


def _skipped(key: str, title: str, url: str, reason: str) -> _Planned:
    return _Planned(
        key, title, KIND_URL, url,
        verdict=Verdict(VerificationStatus.SKIPPED, detail=reason),
    )


def _verdict_for(planned: _Planned, verdicts: Mapping[_Target, Verdict]) -> Verdict:
    if planned.verdict is not None:
        return planned.verdict
    verdict = verdicts[planned.target]  # type: ignore[index]  # target set when verdict is None
    if planned.http_upgraded:
        return _verdict_for_plain_http(verdict)
    return verdict


def _verdict_for_plain_http(https_verdict: Verdict) -> Verdict:
    """Translate the ``https`` probe's verdict back to the ``http`` URL supplied.

    The HTTPS-only transport cannot request ``http://`` at all, so the
    ``https`` form stands in. A definite answer carries over. Anything else
    only shows that the ``https`` form did not answer, which says nothing about
    an ``http``-only site, so it becomes ``skipped`` and does not block.
    """
    if https_verdict.status is VerificationStatus.OK:
        return Verdict(
            VerificationStatus.OK,
            resolved_url=https_verdict.resolved_url,
            detail="plain-http URL, verified through its https form",
        )
    if https_verdict.status is VerificationStatus.INVALID:
        return https_verdict
    return Verdict(
        VerificationStatus.SKIPPED,
        detail=(
            "plain-http URL: the HTTPS-only transport cannot probe it and its "
            f"https form gave no answer ({https_verdict.detail})"
        ),
    )


def _assemble(
    planned: list[_Planned], verdicts: Mapping[_Target, Verdict], *, probed: int
) -> VerificationReport:
    """Build the report. ``probed`` is how many targets needed a network call.

    A run that only read the cache logs at DEBUG: the CLI exports once per
    paper after the first check, and an INFO line per export would bury the
    one line that reports real work.
    """
    checks: list[IdentifierCheck] = []
    for item in planned:
        verdict = _verdict_for(item, verdicts)
        checks.append(
            IdentifierCheck(
                paper_key=item.paper_key,
                title=item.title,
                kind=item.kind,
                value=item.value,
                status=verdict.status,
                resolved_url=verdict.resolved_url,
                detail=verdict.detail,
            )
        )
    report = VerificationReport(checks=tuple(checks))
    counts = report.counts()
    level = logging.INFO if probed or report.failures else logging.DEBUG
    _LOG.log(
        level,
        "identifier preflight: %d ok, %d skipped, %d failed "
        "(%d identifiers, %d probed, the rest cached or decided locally)",
        counts[VerificationStatus.OK.value],
        counts[VerificationStatus.SKIPPED.value],
        len(report.failures),
        len(checks),
        probed,
    )
    return report


def _split_by_cache(
    planned: list[_Planned], cache: VerificationCache
) -> tuple[dict[_Target, Verdict], list[_Target]]:
    """Return ``(verdicts already known, targets still to probe)``, no duplicates."""
    known: dict[_Target, Verdict] = {}
    pending: list[_Target] = []
    seen: set[_Target] = set()
    for item in planned:
        target = item.target
        if target is None or target in seen:
            continue
        seen.add(target)
        cached = cache.get(*target)
        if cached is None:
            pending.append(target)
        else:
            known[target] = cached
    return known, pending


def _remember(
    cache: VerificationCache, fresh: Mapping[_Target, Verdict]
) -> None:
    for (kind, value), verdict in fresh.items():
        cache.put(kind, value, verdict)


# ---------------------------------------------------------------------------
# Public entry points
# ---------------------------------------------------------------------------


async def verify_collection(
    collection: PaperCollection, *, cache: VerificationCache | None = None
) -> VerificationReport:
    """Check every DOI and URL in ``collection`` and return the report.

    Never raises for a bad identifier: the caller decides what a failure means
    (``export_collection`` raises :class:`IdentifierVerificationError`). Pass a
    ``cache`` to share verdicts across calls.

    Example::

        report = await verify_collection(collection)
        for check in report.failures:
            print(check.paper_key, check.kind, check.value, check.detail)
    """
    store = cache if cache is not None else MemoryVerificationCache()
    planned = _plan_collection(collection.papers)
    known, pending = _split_by_cache(planned, store)
    fresh = await _resolve_targets(pending) if pending else {}
    _remember(store, fresh)
    return _assemble(planned, {**known, **fresh}, probed=len(fresh))


def verify_collection_blocking(
    collection: PaperCollection, *, cache: VerificationCache | None = None
) -> VerificationReport:
    """Synchronous :func:`verify_collection`, safe inside a running event loop.

    The cache is read and written on the calling thread. Only the network
    probes run on the private loop, so a cache backed by a thread-bound
    resource (a ``sqlite3`` connection) keeps working when the probes run in a
    worker thread.
    """
    store = cache if cache is not None else MemoryVerificationCache()
    planned = _plan_collection(collection.papers)
    known, pending = _split_by_cache(planned, store)
    fresh = run_blocking(lambda: _resolve_targets(pending)) if pending else {}
    _remember(store, fresh)
    return _assemble(planned, {**known, **fresh}, probed=len(fresh))


# ---------------------------------------------------------------------------
# Network probes
# ---------------------------------------------------------------------------


class _Throttle:
    """Cap probes in flight overall and per host.

    The host slot is taken first: a task queued behind a busy host must not
    hold one of the few overall slots while it waits.
    """

    def __init__(self, total: int, per_host: int) -> None:
        self._total = asyncio.Semaphore(max(1, total))
        self._per_host_limit = max(1, per_host)
        self._hosts: dict[str, asyncio.Semaphore] = {}

    @contextlib.asynccontextmanager
    async def slot(self, host: str) -> AsyncIterator[None]:
        semaphore = self._hosts.setdefault(
            host, asyncio.Semaphore(self._per_host_limit)
        )
        async with semaphore, self._total:
            yield


async def _resolve_targets(targets: list[_Target]) -> dict[_Target, Verdict]:
    """Probe each target once, bounded, and return its verdict.

    Opens its own client for the duration of the call. The shared per-source
    registry (``get_client``) is not used because this coroutine may run on a
    private event loop (see ``run_blocking``), and a registry client belongs to
    the loop that created it.
    """
    throttle = _Throttle(_CONCURRENCY, _PER_HOST_CONCURRENCY)
    async with scoped_client(_SOURCE_NAME) as client:
        verdicts = await asyncio.gather(
            *(_probe_with_retry(client, throttle, target) for target in targets)
        )
    return dict(zip(targets, verdicts, strict=True))


async def _probe_with_retry(
    client: httpx.AsyncClient, throttle: _Throttle, target: _Target
) -> Verdict:
    kind, value = target
    host = "doi.org" if kind == KIND_DOI else (urlsplit(value).hostname or "")
    verdict = Verdict(VerificationStatus.UNREACHABLE, detail="not attempted")
    for _attempt in range(_ATTEMPTS):
        async with throttle.slot(host):
            verdict = await _probe(client, kind, value)
        if verdict.status not in _RETRYABLE:
            break
    return verdict


async def _probe(client: httpx.AsyncClient, kind: str, value: str) -> Verdict:
    """Run one probe and turn transport failures into verdicts."""
    try:
        if kind == KIND_DOI:
            return await _probe_doi(client, value)
        return await _probe_url(client, value)
    except httpx.TimeoutException:
        return Verdict(
            VerificationStatus.TIMEOUT,
            detail=f"no answer within {_TIMEOUT_SECONDS:g} s",
        )
    except httpx.HTTPError as err:
        return Verdict(
            VerificationStatus.UNREACHABLE,
            detail=_clip(f"{type(err).__name__}: {err}"),
        )


async def _probe_doi(client: httpx.AsyncClient, doi: str) -> Verdict:
    """Ask the doi.org handle API whether ``doi`` is registered."""
    response = await client.get(
        _DOI_HANDLE_ENDPOINT + quote(doi, safe="/"),
        timeout=_TIMEOUT_SECONDS,
        follow_redirects=False,
    )
    status = response.status_code
    payload = _json_object(response)
    code = payload.get("responseCode")
    if code == _HANDLE_FOUND:
        return Verdict(VerificationStatus.OK, resolved_url=_handle_url(payload))
    if code == _HANDLE_VALUES_NOT_FOUND:
        return Verdict(
            VerificationStatus.OK, detail="registered, no landing URL recorded"
        )
    if code == _HANDLE_NOT_FOUND or status in _HTTP_NOT_FOUND:
        return Verdict(
            VerificationStatus.INVALID, detail="doi.org has no such DOI registered"
        )
    return _verdict_for_doi_http_error(status)


def _verdict_for_doi_http_error(status: int) -> Verdict:
    """Verdict for a doi.org answer that carried no usable handle record.

    Only a 400 says something about the DOI itself. A 5xx or an unexpected
    2xx / 3xx is the resolver's problem (``unreachable``), and any other 4xx
    means the lookup was refused, typically rate limiting (``skipped``).
    """
    if status >= _HTTP_SERVER_ERROR_FLOOR:
        return Verdict(
            VerificationStatus.UNREACHABLE, detail=f"doi.org answered HTTP {status}"
        )
    if status == httpx.codes.BAD_REQUEST:
        return Verdict(
            VerificationStatus.INVALID, detail="doi.org rejected the DOI as malformed"
        )
    if status >= _HTTP_CLIENT_ERROR_FLOOR:
        return Verdict(
            VerificationStatus.SKIPPED,
            detail=f"doi.org refused the lookup (HTTP {status})",
        )
    return Verdict(
        VerificationStatus.UNREACHABLE,
        detail=f"unexpected answer from doi.org (HTTP {status})",
    )


def _json_object(response: httpx.Response) -> dict[str, Any]:
    try:
        payload = response.json()
    except (json.JSONDecodeError, UnicodeDecodeError, ValueError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _handle_url(payload: Mapping[str, Any]) -> str | None:
    """The landing URL a DOI handle record points at, if it carries one."""
    for entry in payload.get("values") or ():
        if not isinstance(entry, dict) or entry.get("type") != "URL":
            continue
        data = entry.get("data")
        value = data.get("value") if isinstance(data, dict) else None
        if isinstance(value, str) and value:
            return value
    return None


async def _probe_url(client: httpx.AsyncClient, url: str) -> Verdict:
    """Request ``url`` and follow its redirects one hop at a time.

    Redirects are followed by hand so each hop can be vetted before it is
    requested: a hop to plain ``http`` or to a browser-only publisher host is
    never requested. Reaching such a hop already shows the supplied URL is
    real, so the verdict is ``ok`` with the hop as ``resolved_url``.
    """
    current = url
    for _hop in range(_MAX_REDIRECTS + 1):
        status, location = await _status_and_location(client, current)
        if status in _HTTP_REDIRECTS and location:
            target = urljoin(current, location)
            reason = _reason_not_to_follow(target)
            if reason is not None:
                return Verdict(
                    VerificationStatus.OK, resolved_url=target, detail=reason
                )
            current = target
            continue
        return _verdict_for_status(status, url, current)
    return Verdict(
        VerificationStatus.UNREACHABLE,
        detail=f"more than {_MAX_REDIRECTS} redirects",
    )


async def _status_and_location(
    client: httpx.AsyncClient, url: str
) -> tuple[int, str | None]:
    """Status code and ``Location`` header of ``url``. The body is not read."""
    async with client.stream(
        "GET", url, timeout=_TIMEOUT_SECONDS, follow_redirects=False
    ) as response:
        return response.status_code, response.headers.get("location")


def _reason_not_to_follow(target: str) -> str | None:
    if urlsplit(target).scheme.lower() != "https":
        return "redirects to a non-https URL, which was not requested"
    if should_use_webrunner(target):
        return "redirects to a browser-only publisher page, which was not requested"
    return None


def _verdict_for_status(status: int, supplied: str, final: str) -> Verdict:
    resolved = final if final != supplied else None
    if status < _HTTP_CLIENT_ERROR_FLOOR:
        return Verdict(VerificationStatus.OK, resolved_url=resolved)
    if status in _HTTP_NOT_FOUND:
        return Verdict(
            VerificationStatus.INVALID,
            resolved_url=resolved,
            detail=f"HTTP {status}: the page does not exist",
        )
    if status >= _HTTP_SERVER_ERROR_FLOOR:
        return Verdict(
            VerificationStatus.UNREACHABLE,
            resolved_url=resolved,
            detail=f"HTTP {status} from the server",
        )
    return Verdict(
        VerificationStatus.SKIPPED,
        resolved_url=resolved,
        detail=f"HTTP {status}: the server refuses automated access",
    )


def _clip(text: str) -> str:
    """Keep an error message short enough for a one-line report entry."""
    flat = " ".join(text.split())
    if len(flat) <= _DETAIL_MAX_CHARS:
        return flat
    return flat[: _DETAIL_MAX_CHARS - 1] + "…"
