"""Tenant-scoped database access. Every customer query runs inside tenant_connection()."""

import uuid
from collections.abc import Iterator
from contextlib import contextmanager

import psycopg
from psycopg.rows import dict_row

from app.core.config import settings


@contextmanager
def tenant_connection(
    org_id: uuid.UUID | str, url: str | None = None, dict_rows: bool = False
) -> Iterator[psycopg.Connection]:
    """Open a transaction with app.org_id set locally (SET LOCAL semantics).

    set_config(..., true) is transaction-local, so the value never leaks to another
    request that reuses a pooled connection. Never use a plain SET with a pool.
    """
    org = str(uuid.UUID(str(org_id)))  # validates the value
    kwargs = {"row_factory": dict_row} if dict_rows else {}
    with psycopg.connect(url or settings.database_url, **kwargs) as conn:
        with conn.transaction():
            conn.execute("SELECT set_config('app.org_id', %s, true)", (org,))
            yield conn


@contextmanager
def tenant_snapshot_connection(
    org_id: uuid.UUID | str, url: str | None = None
) -> Iterator[psycopg.Connection]:
    """One read-only repeatable snapshot; set isolation before the first SQL.

    Writers retain tenant_connection() and READ COMMITTED. No head locks or
    security-definer privileges are introduced by this read boundary.
    """
    org = str(uuid.UUID(str(org_id)))
    with psycopg.connect(url or settings.database_url, row_factory=dict_row) as conn:
        conn.isolation_level = psycopg.IsolationLevel.REPEATABLE_READ
        conn.read_only = True
        with conn.transaction():
            conn.execute("SELECT set_config('app.org_id', %s, true)", (org,))
            conn.execute("SELECT set_config('TimeZone', 'UTC', true)")
            yield conn
