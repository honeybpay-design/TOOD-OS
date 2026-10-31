"""Tenant-consistent legacy/v2/checkpoint assessment; no config or provider access."""

from __future__ import annotations

import hashlib
import uuid
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from psycopg.rows import dict_row

from app.core.audit_codec_v2 import Event, Genesis, integer, signed_integer
from app.core.audit_integrity_v2 import Head, Receipt, StoredEvent, match_checkpoint, verify_receipt, verify_snapshot
from app.core.audit_manifest_v1 import legacy_inventory
from app.core.audit_models import (
    AuditAssurance,
    AuditCheckpointState,
    AuditLogResponse,
    LegacyAuditState,
    V2AuditEvent,
    V2AuditState,
)

LEGACY_SELECT = (
    "SELECT id,org_id,actor_id,action,target,extract(epoch FROM at)::text AS at_epoch,"
    "encode(inet_send(ip),'hex') AS ip_binary,prev_hash::text AS prev_hash,hash::text AS hash "
    "FROM public.audit_events WHERE org_id=%s ORDER BY id"
)


@dataclass(frozen=True)
class TrustedCheckpoint:
    """Trusted caller input, never a receipt-supplied key or HTTP parameter.

    Live independent storage/key governance is outside this local adapter.
    """
    receipt: Receipt
    previous: Receipt | None
    trusted_keys: Mapping[str, Ed25519PublicKey]
    now: datetime
    max_age: timedelta
    future_skew: timedelta


def decode_event(row) -> StoredEvent:
    if row["format_version"] != 2 or bytes(row["payload_digest"]) != hashlib.sha256(bytes(row["payload_bytes"])).digest():
        raise ValueError("stored event format or payload digest differs from protocol")
    event = Event(
        row["ledger_id"], row["org_id"], row["epoch_id"], row["tenant_sequence"], row["event_id"],
        row["source_event_id"], row["operation_id"], row["actor_id"], row["action"], row["target"],
        row["recorded_at"], str(row["source_ip"]) if row["source_ip"] is not None else None,
        row["payload_schema"], bytes(row["payload_bytes"]), bytes(row["prev_hash"]),
    )
    return StoredEvent(event, bytes(row["hash"]), bytes(row["request_digest"]))


class SnapshotEvents(Sequence[StoredEvent]):
    """Payloads stream through a server cursor in the caller's fixed snapshot.

    The pure verifier still retains identity sets. This is linear verification,
    not a constant-time or independently checkpointed large-history assertion.
    """
    def __init__(self, conn, org_id, epoch_id):
        self.conn, self.org, self.epoch = conn, org_id, epoch_id
        self.count = conn.execute(
            "SELECT count(*) AS n FROM audit_v2.events WHERE org_id=%s AND epoch_id=%s", (org_id, epoch_id)
        ).fetchone()["n"]

    def __len__(self):
        return self.count

    def __iter__(self) -> Iterator[StoredEvent]:
        with self.conn.cursor(name="audit_events_" + uuid.uuid4().hex, row_factory=dict_row) as cursor:
            cursor.execute(
                "SELECT * FROM audit_v2.events WHERE org_id=%s AND epoch_id=%s ORDER BY tenant_sequence",
                (self.org, self.epoch),
            )
            for row in cursor:
                yield decode_event(row)

    def __getitem__(self, index):
        if type(index) is not int or not 0 <= index < self.count:
            raise IndexError("audit snapshot index outside verified inventory")
        row = self.conn.execute(
            "SELECT * FROM audit_v2.events WHERE org_id=%s AND epoch_id=%s AND tenant_sequence=%s",
            (self.org, self.epoch, index + 1),
        ).fetchone()
        if row is None:
            raise ValueError("audit snapshot sequence missing")
        return decode_event(row)


def checkpoint_state(trust, genesis, head, rows, valid):
    if trust is None:
        return AuditCheckpointState(status="unconfigured", reason="No external checkpoint trust is configured")
    if not valid or genesis is None or head is None:
        return AuditCheckpointState(status="invalid", reason="Snapshot integrity is not verified")
    try:
        verify_receipt(
            trust.receipt, trust.trusted_keys, previous=trust.previous, now=trust.now,
            max_age=trust.max_age, future_skew=trust.future_skew,
        )
        match_checkpoint(trust.receipt, genesis, head, rows)
    except (ValueError, TypeError, OverflowError):
        return AuditCheckpointState(status="invalid", reason="External checkpoint verification failed")
    cp = trust.receipt.checkpoint
    return AuditCheckpointState(
        status="verified", verified_through_sequence=integer(cp.sequence, minimum=0),
        uncheckpointed_events=integer(head.sequence - cp.sequence, minimum=0),
        receipt_digest=trust.receipt.digest().hex(), issued_at=cp.issued_at,
        reason="Verified against caller-supplied external trust; governance is not certified",
    )


def read_audit_snapshot(conn, org_id, *, trust: TrustedCheckpoint | None = None, recent_limit: int = 30):
    """No permission fallback: all inputs must share one read-only tenant snapshot."""
    org = uuid.UUID(str(org_id))
    context = conn.execute(
        "SELECT current_setting('transaction_isolation') AS isolation,"
        "current_setting('transaction_read_only') AS readonly,public.app_org_id() AS org_id,"
        "transaction_timestamp() AS snapshot_at,audit_v2.current_version() AS version"
    ).fetchone()
    if (context["isolation"], context["readonly"], context["org_id"]) != ("repeatable read", "on", org):
        raise ValueError("audit reader requires one read-only tenant snapshot")
    mode = context["version"]
    if mode not in (1, 2) or type(recent_limit) is not int or not 1 <= recent_limit <= 100:
        raise ValueError("unsupported audit read mode or recent bound")
    with conn.cursor(name="audit_legacy_" + uuid.uuid4().hex, row_factory=dict_row) as cursor:
        cursor.execute(LEGACY_SELECT, (org,))
        inventory = legacy_inventory(org, cursor)
    epoch = conn.execute("SELECT * FROM audit_v2.epochs WHERE org_id=%s", (org,)).fetchone()
    head_row = conn.execute("SELECT * FROM audit_v2.heads WHERE org_id=%s", (org,)).fetchone()
    declared = epoch["legacy_status"] if epoch else None
    manifest_matches = None
    declaration_consistent = None
    if epoch:
        manifest_matches = (
            epoch["manifest_version"] == 1 and bytes(epoch["manifest_digest"]) == inventory.digest
            and epoch["legacy_count"] == inventory.count and epoch["legacy_max_id"] == inventory.max_id
        )
        declaration_consistent = (
            declared == "unverified"
            or (declared == "verified" and inventory.internal_valid and epoch["legacy_first_bad_id"] is None)
            or (declared == "broken" and not inventory.internal_valid
                and epoch["legacy_first_bad_id"] == inventory.first_bad_id)
        )
    history = "broken" if not inventory.internal_valid or declared == "broken" else (
        "unverified" if declared == "unverified" else "internally_valid"
    )
    legacy = LegacyAuditState(
        event_count=integer(inventory.count, minimum=0),
        min_id=signed_integer(inventory.min_id) if inventory.min_id is not None else None,
        max_id=signed_integer(inventory.max_id) if inventory.max_id is not None else None,
        current_internal_valid=inventory.internal_valid,
        first_bad_id=signed_integer(inventory.first_bad_id) if inventory.first_bad_id is not None else None,
        history_state=history, declared_status=declared,
        declared_first_bad_id=signed_integer(epoch["legacy_first_bad_id"])
        if epoch and epoch["legacy_first_bad_id"] is not None else None,
        incident_ref=epoch["incident_ref"] if epoch else None,
        observed_manifest_sha256=inventory.digest.hex(),
        committed_manifest_sha256=bytes(epoch["manifest_digest"]).hex() if epoch else None,
        manifest_matches=manifest_matches, declaration_consistent=declaration_consistent,
    )
    total = conn.execute("SELECT count(*) AS n FROM audit_v2.events WHERE org_id=%s", (org,)).fetchone()["n"]
    rows = genesis = head = None
    if not epoch or not head_row:
        v2 = V2AuditState(
            status="not_active" if mode == 1 and not epoch and not head_row and total == 0 else "unavailable",
            event_count=integer(total, minimum=0), reason="not_active" if mode == 1 else "missing_epoch_or_head",
        )
    elif epoch["format_version"] != 2 or epoch["manifest_version"] != 1:
        v2 = V2AuditState(status="invalid", event_count=integer(total, minimum=0), reason="unsupported_format")
    else:
        rows = SnapshotEvents(conn, org, epoch["epoch_id"])
        genesis = Genesis(
            epoch["ledger_id"], org, epoch["epoch_id"], bytes(epoch["manifest_digest"]), declared,
            epoch["legacy_count"], epoch["legacy_max_id"], epoch["legacy_first_bad_id"], epoch["incident_ref"],
            bytes(epoch["cutover_digest"]), epoch["initialized_at"],
        )
        head = Head(str(head_row["epoch_id"]), head_row["last_sequence"], bytes(head_row["last_hash"]))
        integrity = verify_snapshot(genesis, bytes(epoch["genesis_hash"]), head, rows)
        valid = integrity.valid and total == len(rows)
        v2 = V2AuditState(
            status=("valid" if mode == 2 else "prepared_not_active") if valid else "invalid",
            ledger_id=str(epoch["ledger_id"]), epoch_id=str(epoch["epoch_id"]), format_version=epoch["format_version"],
            sequence=integer(head.sequence, minimum=0), event_count=integer(total, minimum=0),
            head_hash=head.event_hash.hex(), genesis_hash=bytes(epoch["genesis_hash"]).hex(),
            first_bad_sequence=integer(integrity.first_bad_sequence) if integrity.first_bad_sequence is not None else None,
            reason=integrity.reason if total == len(rows) else "unexpected_epoch_inventory",
        )
    checkpoint = checkpoint_state(trust, genesis, head, rows, v2.status == "valid")
    if mode == 2 and v2.status == "unavailable":
        status = "v2_unavailable"
    elif v2.status == "invalid":
        status = "v2_integrity_failed"
    elif manifest_matches is False:
        status = "legacy_manifest_changed"
    elif history == "broken":
        status = "legacy_broken"
    elif history == "unverified" or declaration_consistent is False:
        status = "legacy_unverified"
    elif mode == 1:
        status = "legacy_only"
    elif checkpoint.status == "invalid":
        status = "checkpoint_invalid"
    elif checkpoint.status == "unconfigured":
        status = "v2_internal_only_uncheckpointed"
    elif checkpoint.uncheckpointed_events != "0":
        status = "checkpointed_prefix_only"
    else:
        status = "checkpointed_internal_integrity"
    limitations = [
        "Legacy v1 hashes do not authenticate stored IDs, timestamps or IP metadata",
        "Actor and IP values are application assertions, not independent identity proof",
        "An observed legacy inventory cannot establish authenticity before its capture",
        "Removal of an uncheckpointed suffix is not independently detectable",
        "Cryptographic verification is not a compliance or enterprise certification",
    ]
    assurance = AuditAssurance(
        org_id=str(org), active_version=mode, snapshot_at=context["snapshot_at"], status=status,
        legacy=legacy, v2=v2, checkpoint=checkpoint, limitations=limitations,
    )
    recent = conn.execute(
        "SELECT id,action,target,to_jsonb(at) AS at FROM public.audit_events WHERE org_id=%s ORDER BY id DESC LIMIT %s",
        (org, recent_limit),
    ).fetchall()
    recent_v2 = []
    if epoch:
        for row in conn.execute(
            "SELECT * FROM audit_v2.events WHERE org_id=%s AND epoch_id=%s ORDER BY tenant_sequence DESC LIMIT %s",
            (org, epoch["epoch_id"], recent_limit),
        ):
            recent_v2.append(V2AuditEvent(
                event_id=str(row["event_id"]), sequence=integer(row["tenant_sequence"]), action=row["action"],
                target=row["target"], recorded_at=row["recorded_at"], event_hash=bytes(row["hash"]).hex(),
                payload_schema=row["payload_schema"],
            ))
    return AuditLogResponse(
        chain_ok=inventory.internal_valid, first_bad_event=inventory.first_bad_id,
        events_total=inventory.count, recent=recent, assurance=assurance, recent_v2=recent_v2,
    )
