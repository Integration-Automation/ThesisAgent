"""Schema of the literature library and how it changes between versions.

The version lives in SQLite's own ``PRAGMA user_version``, and
``PRAGMA application_id`` marks the file as a ThesisAgents library. Opening a
library goes through :func:`prepare`, which leaves the database in exactly one
of three states: brought up to :data:`SCHEMA_VERSION`, already there, or
rejected with a ``LibraryError`` that says why.

Changing the schema means appending one function to :data:`MIGRATIONS`. The
function at index ``n`` upgrades a database from version ``n`` to ``n + 1``,
so the list is also the history. Never edit a migration that has shipped:
libraries in the field have already run it.

Tables (version 1)
------------------
``papers``         one row per distinct paper: its ``Paper.to_dict()`` record
                   (bibliographic fields, field provenance, summary), and when
                   it was first and last seen.
``identity_keys``  every key a paper is known by (DOI, arXiv ID, title hash),
                   pointing at its row. This is what makes a repeated import a
                   merge instead of a duplicate.
``runs``           one row per import: when, what kind, the query, and what
                   each source returned.
``observations``   which run saw which paper, through which source, at what
                   rank, with what score and pruning recommendation.
``relations``      citation links between two stored papers, with the
                   provider and depth that found them.
``verifications``  the export preflight's verdict per DOI / URL, so an
                   identifier checked last week is not looked up again.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Callable, Iterator
from contextlib import contextmanager

from thesisagents.core.exceptions import LibraryError

#: "THAG" in ASCII. Lets a library be told from any other SQLite file.
APPLICATION_ID: int = 0x54484147
SCHEMA_VERSION: int = 1


@contextmanager
def transaction(conn: sqlite3.Connection) -> Iterator[sqlite3.Connection]:
    """One all-or-nothing write to the library.

    The boundary this guards: every write that touches more than one row (an
    import, a merge of two stored papers, a schema migration). The failure it
    prevents is a half-applied change, for example a paper row without its
    identity keys, which a later import could no longer recognise.

    ``BEGIN IMMEDIATE`` takes the write lock up front, so a second writer
    waits (up to the connection's busy timeout) instead of failing halfway
    through with "database is locked". Connections are opened in autocommit
    mode, which is why the transaction is spelled out here.

    Example::

        with transaction(conn):
            conn.execute("INSERT INTO runs ...")
            conn.execute("INSERT INTO observations ...")
    """
    conn.execute("BEGIN IMMEDIATE")
    try:
        yield conn
    except BaseException:
        conn.execute("ROLLBACK")
        raise
    conn.execute("COMMIT")


_VERSION_1: tuple[str, ...] = (
    """
    CREATE TABLE papers (
        id INTEGER PRIMARY KEY,
        record TEXT NOT NULL,
        title TEXT NOT NULL,
        year INTEGER,
        first_seen TEXT NOT NULL,
        last_seen TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE identity_keys (
        key TEXT PRIMARY KEY,
        paper_id INTEGER NOT NULL REFERENCES papers(id) ON DELETE CASCADE
    )
    """,
    "CREATE INDEX identity_keys_paper ON identity_keys(paper_id)",
    """
    CREATE TABLE runs (
        id INTEGER PRIMARY KEY,
        started_at TEXT NOT NULL,
        kind TEXT NOT NULL,
        keywords TEXT NOT NULL,
        query TEXT NOT NULL,
        source_stats TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE observations (
        run_id INTEGER NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
        paper_id INTEGER NOT NULL REFERENCES papers(id) ON DELETE CASCADE,
        source TEXT NOT NULL,
        source_id TEXT NOT NULL,
        rank INTEGER,
        score TEXT,
        recommendation TEXT,
        PRIMARY KEY (run_id, paper_id)
    )
    """,
    "CREATE INDEX observations_paper ON observations(paper_id)",
    """
    CREATE TABLE relations (
        source_id INTEGER NOT NULL REFERENCES papers(id) ON DELETE CASCADE,
        target_id INTEGER NOT NULL REFERENCES papers(id) ON DELETE CASCADE,
        relation TEXT NOT NULL,
        provider TEXT NOT NULL,
        depth INTEGER NOT NULL,
        run_id INTEGER REFERENCES runs(id) ON DELETE SET NULL,
        PRIMARY KEY (source_id, target_id, relation)
    )
    """,
    "CREATE INDEX relations_target ON relations(target_id)",
    """
    CREATE TABLE verifications (
        kind TEXT NOT NULL,
        value TEXT NOT NULL,
        status TEXT NOT NULL,
        resolved_url TEXT,
        detail TEXT NOT NULL,
        checked_at TEXT NOT NULL,
        PRIMARY KEY (kind, value)
    )
    """,
)


def _create_version_1(conn: sqlite3.Connection) -> None:
    # One statement per execute(): ``executescript`` commits any open
    # transaction first, which would take the migration out of the
    # transaction that makes it all-or-nothing.
    for statement in _VERSION_1:
        conn.execute(statement)


#: ``MIGRATIONS[n]`` upgrades a database from version ``n`` to ``n + 1``.
MIGRATIONS: tuple[Callable[[sqlite3.Connection], None], ...] = (_create_version_1,)


def prepare(conn: sqlite3.Connection, path: str) -> int:
    """Bring ``conn`` to the current schema, or refuse it. Returns the version.

    The boundary this guards: the first read of a file the user pointed at.
    The failure it prevents is reading or writing a database whose tables do
    not mean what this code assumes, either because the file is something
    else entirely or because a newer ThesisAgents changed the layout.

    Each migration runs in one transaction together with the version bump
    (SQLite's schema changes and both PRAGMAs are transactional), so an
    upgrade that fails halfway leaves the previous version intact. ``conn``
    must be in autocommit mode (``isolation_level=None``).

    Example: a fresh file ends at version 1. A file that says version 3 raises
    ``LibraryError`` naming both numbers.
    """
    try:
        version = conn.execute("PRAGMA user_version").fetchone()[0]
        application = conn.execute("PRAGMA application_id").fetchone()[0]
        tables = conn.execute(
            "SELECT count(*) FROM sqlite_master WHERE type = 'table'"
        ).fetchone()[0]
    except sqlite3.DatabaseError as err:
        raise LibraryError(
            f"{path} is not an SQLite database ({err}). Point --library at "
            "another file. A new file is created when the path does not exist."
        ) from err
    if version == 0 and tables:
        raise LibraryError(
            f"{path} is an SQLite database, but not a ThesisAgents library "
            "(it has tables and no library schema version). Point --library "
            "at another file."
        )
    if version and application != APPLICATION_ID:
        raise LibraryError(
            f"{path} is an SQLite database of another application "
            f"(application_id {application}). Point --library at another file."
        )
    if version > SCHEMA_VERSION:
        raise LibraryError(
            f"{path} has library schema version {version}, and this "
            f"ThesisAgents understands up to version {SCHEMA_VERSION}. It was "
            "written by a newer release: upgrade ThesisAgents, or point "
            "--library at another file."
        )
    while version < SCHEMA_VERSION:
        migrate = MIGRATIONS[version]
        with transaction(conn):
            migrate(conn)
            version += 1
            # PRAGMA values cannot be bound as parameters. Both are integers
            # defined in this module, never user input.
            conn.execute(f"PRAGMA application_id = {APPLICATION_ID:d}")
            conn.execute(f"PRAGMA user_version = {version:d}")
    return version
