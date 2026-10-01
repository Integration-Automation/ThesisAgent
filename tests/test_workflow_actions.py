"""Every GitHub Actions step pins its action to a commit SHA.

A tag such as ``@v4`` can be moved to new code at any time (the 2025
tj-actions/changed-files compromise rewrote tags), so each ``uses:`` names a
full 40-hex commit and carries the release it corresponds to as a comment,
which is what Dependabot reads and updates. Pinning also keeps Node 20 actions
from lingering unnoticed: GitHub removed Node 20 from its runners on 2026-09-23.

The rest of the workflow supply chain is guarded here too: Dependabot's
settings, checkout credentials, job timeouts, the Nuitka cache, and the
hash-locked tooling of the job that holds the PyPI token.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

_ROOT = next(p for p in Path(__file__).resolve().parents if (p / ".github" / "workflows").is_dir())
_WORKFLOWS = sorted((_ROOT / ".github" / "workflows").glob("*.yml"))
_USES = re.compile(r"^\s*(?:-\s*)?uses:\s*(\S+)(.*)$")
_PINNED = re.compile(r"^[\w.-]+/[\w./-]+@[0-9a-f]{40}$")
_LOCAL = re.compile(r"^\./")
_VERSION_COMMENT = re.compile(r"^\s+#\s*v\d+(\.\d+)*\s*$")


def _uses(path: Path) -> list[tuple[int, str, str]]:
    """Return ``(line number, action reference, rest of line)`` for each remote ``uses:``."""
    found = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        match = _USES.match(line)
        if match and not _LOCAL.match(match.group(1)):
            found.append((number, match.group(1), match.group(2)))
    return found


def test_workflows_exist():
    assert _WORKFLOWS


@pytest.mark.parametrize("workflow", _WORKFLOWS, ids=lambda p: p.name)
def test_every_action_is_pinned_to_a_commit_with_its_version(workflow):
    bad = [f"{workflow.name}:{number} {ref}{rest}"
           for number, ref, rest in _uses(workflow)
           if not (_PINNED.match(ref) and _VERSION_COMMENT.match(rest))]
    assert bad == []


def test_one_version_per_action():
    # The same action at two different commits means a partial upgrade.
    seen: dict[str, set[str]] = {}
    for workflow in _WORKFLOWS:
        for _number, ref, _rest in _uses(workflow):
            action, _, sha = ref.partition("@")
            seen.setdefault(action, set()).add(sha)
    assert {action: shas for action, shas in seen.items() if len(shas) > 1} == {}


def test_dependabot_keeps_pins_current_on_dev():
    # Pinned SHAs only stay current if something bumps them; every update
    # goes to dev because main is the release branch. Parsed as text: PyYAML
    # is not a test dependency.
    text = (_ROOT / ".github" / "dependabot.yml").read_text(encoding="utf-8")
    blocks = re.split(r"^\s*-\s*package-ecosystem:", text, flags=re.MULTILINE)[1:]
    ecosystems = {block.split()[0].strip("\"'") for block in blocks}
    assert {"pip", "github-actions"} <= ecosystems
    assert all(re.search(r"^\s*target-branch:\s*\"dev\"", block, re.MULTILINE)
               for block in blocks)


def test_dependabot_waits_a_week_before_proposing_a_release():
    # A compromised release is usually found and yanked within days. Dependabot's
    # own default wait is 3 days, and zizmor's dependabot-cooldown audit asks
    # for 7. The wait never delays security updates.
    text = (_ROOT / ".github" / "dependabot.yml").read_text(encoding="utf-8")
    blocks = re.split(r"^\s*-\s*package-ecosystem:", text, flags=re.MULTILINE)[1:]
    days = [re.search(r"^\s*default-days:\s*(\d+)", block, re.MULTILINE) for block in blocks]
    assert blocks and all(match and int(match.group(1)) >= 7 for match in days)


def test_dependabot_watches_the_hash_locked_requirements():
    # From "/" Dependabot does not reach .github/requirements, so the directory
    # has to be named or publish.txt is never updated. Comment lines are dropped
    # first: a path quoted in a comment configures nothing.
    text = (_ROOT / ".github" / "dependabot.yml").read_text(encoding="utf-8")
    blocks = re.split(r"^\s*-\s*package-ecosystem:", text, flags=re.MULTILINE)[1:]
    pip = next(block for block in blocks if block.split()[0].strip("\"'") == "pip")
    settings = "\n".join(line for line in pip.splitlines() if not line.lstrip().startswith("#"))
    assert re.search(r"^\s*directories:", settings, re.MULTILINE)
    assert set(re.findall(r"\"(/[^\"]*)\"", settings)) == {"/", "/.github/requirements"}


def test_release_runs_only_for_pushes_to_this_repository():
    # workflow_run's `branches:` filter compares the head branch *name*, so
    # a pull request from a fork's `main` also completes CI "on main". The
    # release job must additionally require a push to this repository.
    text = (_ROOT / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")
    assert "github.event.workflow_run.event == 'push'" in text
    assert "github.event.workflow_run.head_repository.full_name == github.repository" in text


def _steps_using(text: str, action: str) -> list[tuple[int, str]]:
    """Return ``(line number, step text)`` for each step that uses ``action``.

    A step runs from its ``uses:`` line to the next line indented less than
    ``uses:`` or starting another list item, e.g.
    ``_steps_using(text, "actions/checkout")``.
    """
    lines = text.splitlines()
    steps = []
    for index, line in enumerate(lines):
        if not re.search(rf"uses:\s*{re.escape(action)}@", line):
            continue
        column = line.index("uses:")
        body = [line]
        for following in lines[index + 1:]:
            indent = len(following) - len(following.lstrip())
            if following.strip() and (indent < column or following.lstrip().startswith("- ")):
                break
            body.append(following)
        steps.append((index + 1, "\n".join(body)))
    return steps


def _checkout_steps(path: Path) -> list[tuple[int, str]]:
    """Return ``(line number, step text)`` for each ``actions/checkout`` step."""
    return _steps_using(path.read_text(encoding="utf-8"), "actions/checkout")


@pytest.mark.parametrize("workflow", _WORKFLOWS, ids=lambda p: p.name)
def test_every_checkout_decides_on_persisted_credentials(workflow):
    # actions/checkout leaves the job token in .git/config unless told not
    # to, where every later step (and any uploaded workspace) can read it.
    # Only jobs that push keep it, and they say so.
    bad = [f"{workflow.name}:{number}" for number, step in _checkout_steps(workflow)
           if not re.search(r"^\s*persist-credentials:\s*(true|false)\b", step, re.MULTILINE)]
    assert bad == []


def test_nuitka_cache_step_saves_the_directory_nuitka_uses():
    # Nuitka's compiler cache lives under NUITKA_CACHE_DIR. The release
    # cached ~/.nuitka and ~/.cache/Nuitka instead, which Nuitka does not
    # use on Windows, so every release compiled all ~2700 C files cold
    # ("0 cache hits") and ran within minutes of its 90 min cap.
    text = (_ROOT / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")
    env = re.search(r"^\s*NUITKA_CACHE_DIR:\s*(\S+)\s*$", text, re.MULTILINE)
    assert env, "release.yml must set NUITKA_CACHE_DIR for the Nuitka build"
    cache_step = next(step for _number, step in _steps_using(text, "actions/cache")
                      if "nuitka-" in step)
    assert re.search(rf"^\s*path:\s*{re.escape(env.group(1))}\s*$", cache_step, re.MULTILINE)


_JOB_HEAD = re.compile(r"^  [A-Za-z0-9_-]+:\s*(#.*)?$")


def _jobs(path: Path) -> list[tuple[str, str]]:
    """Return ``(job id, job text)`` for each job under ``jobs:`` in a workflow."""
    lines = path.read_text(encoding="utf-8").splitlines()
    start = next(i for i, line in enumerate(lines) if re.match(r"^jobs:\s*(#.*)?$", line))
    heads = [i for i in range(start + 1, len(lines)) if _JOB_HEAD.match(lines[i])]
    ends = [*heads[1:], len(lines)]
    pairs = zip(heads, ends, strict=True)
    return [(lines[i].strip().rstrip(":"), "\n".join(lines[i:end])) for i, end in pairs]


@pytest.mark.parametrize("workflow", _WORKFLOWS, ids=lambda p: p.name)
def test_every_job_has_a_timeout(workflow):
    # Without timeout-minutes a hung job runs for GitHub's default six hours.
    # Each job sets about three times its slowest recent run, at least 15 minutes.
    bad = [name for name, body in _jobs(workflow)
           if "runs-on:" in body and not re.search(r"^\s*timeout-minutes:", body, re.MULTILINE)]
    assert bad == []


_REQUIREMENTS = _ROOT / ".github" / "requirements"
_LOCKED_INSTALL = ("python -m pip install --require-hashes --only-binary :all: "
                   "-r .github/requirements/publish.txt")
_PIP_INSTALL = re.compile(r"(?:python3? -m )?\bpip3? install\b.*")
_RUN_OR_IMPORT = re.compile(r"python3? -m ([A-Za-z_]\w*)|^\s*import ([A-Za-z_]\w*)", re.MULTILINE)


def _publish_jobs() -> list[tuple[str, str]]:
    """Return ``(workflow:job, job text less comments)`` for each job that reads the PyPI token.

    These are the jobs whose installs run next to ``secrets.PYPI_API_TOKEN``, e.g.
    ``[("release.yml:publish-pypi", "publish-pypi:\\n    name: ...")]``. Comment lines are
    dropped so a command quoted in a comment is neither counted as an install nor as a tool.
    """
    found = []
    for workflow in _WORKFLOWS:
        for name, body in _jobs(workflow):
            if "secrets.PYPI_API_TOKEN" in body:
                code = [line for line in body.splitlines() if not line.lstrip().startswith("#")]
                found.append((f"{workflow.name}:{name}", "\n".join(code)))
    return found


_PUBLISH_JOBS = _publish_jobs()
_PUBLISH_IDS = [name for name, _body in _PUBLISH_JOBS]
_PUBLISH_BODIES = [body for _name, body in _PUBLISH_JOBS]


def _distribution(name: str) -> str:
    """Return a module or requirement name the way PyPI spells a distribution.

    Lets a module a job runs be compared with a requirement line, e.g.
    ``_distribution("Pyproject_Hooks") == "pyproject-hooks"``.
    """
    return name.lower().replace("_", "-")


def _tools(body: str) -> set[str]:
    """Return what a job runs with ``python -m`` or imports inline, less pip and the stdlib.

    This is the set that has to be locked before the job can use it, e.g. a job that runs
    ``python -m build`` and ``python -m twine upload`` gives ``{"build", "twine"}``.
    """
    named = {module or imported for module, imported in _RUN_OR_IMPORT.findall(body)}
    return {_distribution(name) for name in named - {"pip"} - set(sys.stdlib_module_names)}


def _requirements(name: str) -> set[str]:
    """Return the distributions a file in ``.github/requirements`` names at the start of a line.

    Reads ``publish.in`` (the tools asked for) or ``publish.txt`` (every pin), e.g.
    ``_requirements("publish.in") == {"build", "twine"}``. Comments, hashes and ``# via``
    lines start with ``#`` or a space and are not matched.
    """
    text = (_REQUIREMENTS / name).read_text(encoding="utf-8")
    found = re.findall(r"^([A-Za-z0-9][\w.-]*)", text, re.MULTILINE)
    return {_distribution(requirement) for requirement in found}


def test_the_job_that_holds_the_pypi_token_is_publish_pypi():
    # A second job that reads the token must be listed here on purpose, which
    # puts its installs under the tests below.
    assert _PUBLISH_IDS == ["release.yml:publish-pypi"]


@pytest.mark.parametrize("body", _PUBLISH_BODIES, ids=_PUBLISH_IDS)
def test_publish_job_installs_only_the_hash_locked_tooling(body):
    # Whatever this job installs runs next to the PyPI token. An unpinned
    # "pip install build twine", or upgrading pip first, takes the newest upload
    # of that day. The lock allows only wheels whose hashes were recorded.
    assert [command.strip() for command in _PIP_INSTALL.findall(body)] == [_LOCKED_INSTALL]


def test_publish_in_lists_exactly_the_tools_the_job_runs():
    # A tool the job starts using has to be locked first, or the release fails at that step.
    used = set().union(*(_tools(body) for body in _PUBLISH_BODIES))
    assert used == _requirements("publish.in")


def test_publish_lock_pins_every_tool_of_publish_in():
    # publish.txt is generated. Editing publish.in alone changes nothing the job installs.
    assert _requirements("publish.in") <= _requirements("publish.txt")


def test_publish_lock_is_resolved_for_the_python_and_runner_of_the_job():
    # The lock holds the wheels of one Python version on one platform. A job on
    # another version or operating system may find no wheel whose hash is listed.
    header = (_REQUIREMENTS / "publish.txt").read_text(encoding="utf-8").splitlines()[1]
    locked_python = re.search(r"--python-version (\S+)", header).group(1)
    locked_platform = re.search(r"--python-platform (\S+)", header).group(1)
    set_up = {version for body in _PUBLISH_BODIES
              for version in re.findall(r"python-version:\s*\"([^\"]+)\"", body)}
    runners = {runner for body in _PUBLISH_BODIES
               for runner in re.findall(r"^\s*runs-on:\s*(\S+)", body, re.MULTILINE)}
    assert set_up == {locked_python}
    assert locked_platform.startswith("x86_64-manylinux")
    assert runners == {"ubuntu-latest"}
