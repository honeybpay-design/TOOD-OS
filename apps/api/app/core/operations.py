"""Business idempotency in the caller's transaction; no external exactly-once claim."""

from __future__ import annotations

import hashlib
import json
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import psycopg
from fastapi import HTTPException
from psycopg.types.json import Jsonb

from app.core import audit, audit_v2
from app.core.audit_codec_v2 import canonical_payload

if TYPE_CHECKING:
    from app.core.auth import Ctx

MAX_REQUEST = 262144


def request_bytes(value: dict) -> bytes:
    """Canonical effective JSON request, not raw HTTP whitespace or only its digest."""

    def validate(item):
        if isinstance(item, dict):
            if not all(isinstance(k, str) for k in item):
                raise ValueError("business request keys must be strings")
            for child in item.values():
                validate(child)
        elif isinstance(item, (list, tuple)):
            for child in item:
                validate(child)

    if not isinstance(value, dict):
        raise ValueError("business request must be an object")
    validate(value)
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode(
        "utf-8"
    )
    if len(encoded) > MAX_REQUEST:
        raise ValueError("business request exceeds bounded size")
    return encoded


def _row(cursor) -> dict:
    row = cursor.fetchone()
    if row is None:
        raise RuntimeError("operation boundary returned no row")
    return row if isinstance(row, dict) else dict(zip((c.name for c in cursor.description), row, strict=True))


@dataclass
class Operation:
    conn: Any
    ctx: Ctx
    action: str
    operation_id: uuid.UUID
    mode: int
    schema: str
    request_digest: bytes
    reference: dict | None = None
    finished: bool = False

    @property
    def replayed(self) -> bool:
        return self.reference is not None

    def new_id(self, purpose: str) -> uuid.UUID:
        # Stable object IDs after an uncommitted retry; GCS generation guards are
        # still enforced. Orphans require reconciliation, never silent overwrite.
        return (
            uuid.uuid5(uuid.UUID(str(self.ctx.org_id)), str(self.operation_id) + ":" + purpose)
            if self.mode == 2
            else uuid.uuid4()
        )

    def finish(
        self,
        reference: dict,
        *,
        target,
        payload: dict | bytes | None = None,
        payload_schema: str = "tood.business-operation.v1",
    ) -> None:
        if self.finished or self.replayed:
            raise RuntimeError("operation already completed")
        if self.mode == 1:
            audit.record(self.conn, self.ctx.org_id, self.ctx.user_id, self.action, str(target))
        else:
            content = json.loads(payload) if isinstance(payload, bytes) else dict(payload or {"resource": reference})
            content.update(operation_request_digest=self.request_digest.hex(), operation_request_schema=self.schema)
            audit_v2.append(
                self.conn,
                org_id=self.ctx.org_id,
                actor_id=self.ctx.user_id,
                action=self.action,
                target=str(target),
                source_event_id=uuid.uuid5(self.operation_id, "audit:" + self.action),
                operation_id=self.operation_id,
                payload_schema=payload_schema,
                payload=canonical_payload(content),
            )
            self.conn.execute(
                "SELECT audit_v2.complete_operation(%s,%s,%s,%s)",
                (self.ctx.org_id, self.operation_id, self.ctx.user_id, Jsonb(reference)),
            ).fetchone()
        self.finished = True


@contextmanager
def business_operation(conn, ctx: Ctx, action: str, effective_request: dict, idempotency_key: uuid.UUID | None = None):
    """Authorize resource/role before entering. Mutating preconditions follow replay.

    Pending state cannot commit: both this context and a deferred DB trigger enforce
    completion. Supplied UUID keys deduplicate committed database effects. Without
    a key each HTTP request is a new intent. No retries/commits happen in this helper.
    """
    if conn.autocommit:
        raise ValueError("business operation requires a transaction")
    row = conn.execute("SELECT audit_v2.locked_version() AS version").fetchone()
    mode = row["version"] if isinstance(row, dict) else row[0]
    if mode not in (1, 2):
        raise HTTPException(503, "audit mode is unavailable")
    if mode == 1 and idempotency_key is not None:
        raise HTTPException(409, "idempotency keys require reviewed audit v2 activation")
    key = uuid.UUID(str(idempotency_key)) if idempotency_key is not None else uuid.uuid4()
    schema = "tood." + action + ".request.v1"
    encoded = request_bytes(effective_request)
    operation = Operation(conn, ctx, action, key, mode, schema, hashlib.sha256(encoded).digest())
    if mode == 2:
        try:
            row = _row(
                conn.execute(
                    "SELECT * FROM audit_v2.begin_operation(%s,%s,%s,%s,%s,%s)",
                    (ctx.org_id, key, ctx.user_id, action, schema, encoded),
                )
            )
        except psycopg.errors.UniqueViolation:
            raise HTTPException(409, "idempotency key conflicts with the original actor or request") from None
        except psycopg.errors.ObjectNotInPrerequisiteState:
            raise HTTPException(503, "audit operation is not ready") from None
        if row["status"] == "complete":
            operation.reference = row["result_reference"]
            if not isinstance(operation.reference, dict):
                raise HTTPException(503, "committed operation result is unavailable")
    yield operation
    if not operation.replayed and not operation.finished:
        raise RuntimeError("business operation returned without audit completion")
