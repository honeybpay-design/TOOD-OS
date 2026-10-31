"""Database-only v2 append adapter and typed generation provenance.

Not activated by import. The coordinated cutover and atomic onboarding integration
must be verified before the existing v1 business writer is routed here.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.core.audit_codec_v2 import bounded, canonical_payload, digest_text, uuid_text


@dataclass(frozen=True)
class GenerationAudit:
    draft_id: UUID | str
    question_id: UUID | str
    revision_id: UUID | str
    revision_hash: bytes
    requested_model_id: str
    actual_model_id: str
    prompt_version: str
    signed_admission_digest: bytes | None

    def payload(self) -> bytes:
        requested = bounded(self.requested_model_id, 512)
        actual = bounded(self.actual_model_id, 512)
        template = requested == actual == "template-v0"
        if template != (self.signed_admission_digest is None):
            raise ValueError("generation admission reference inconsistent")
        return canonical_payload(
            {
                "draft_id": uuid_text(self.draft_id),
                "question_id": uuid_text(self.question_id),
                "revision_id": uuid_text(self.revision_id),
                "revision_hash": digest_text(self.revision_hash),
                "requested_model_id": requested,
                "actual_model_id": actual,
                "prompt_version": bounded(self.prompt_version, 512),
                "signed_admission_digest": digest_text(self.signed_admission_digest)
                if self.signed_admission_digest is not None
                else None,
                "source": "template" if template else "admitted_model",
            }
        )


def append(
    conn,
    *,
    org_id,
    actor_id,
    action: str,
    target: str | None,
    source_event_id,
    operation_id,
    payload_schema: str,
    payload: bytes,
    source_ip: str | None = None,
) -> dict:
    """Join the existing business transaction; never commit or allocate retry IDs here.

    Source-event dedup is not business dedup. Caller authorization and operation
    reservation must precede mutations and replay. Database also enforces context,
    isolation, activation, role privileges, payload bounds and head serialization.
    """
    if conn.autocommit:
        raise ValueError("audit v2 append requires a business transaction")
    org = uuid_text(org_id)
    source = uuid_text(source_event_id)
    operation = uuid_text(operation_id)
    actor = uuid_text(actor_id) if actor_id is not None else None
    if not isinstance(payload, bytes):
        raise ValueError("audit payload must be exact bytes")
    cursor = conn.execute(
        "SELECT * FROM audit_v2.append_event(%s,%s,%s,%s,%s,%s,%s,%s,%s)",
        (org, source, operation, actor, action, target, source_ip, payload_schema, payload),
    )
    row = cursor.fetchone()
    if row is None:
        raise RuntimeError("database append did not return an event")
    return row if isinstance(row, dict) else dict(zip((column.name for column in cursor.description), row, strict=True))
