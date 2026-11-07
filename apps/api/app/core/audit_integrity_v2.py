"""Independent v2 verification over supplied immutable snapshots, without DB/config access.

This does not authenticate the caller's actor assertions or establish live checkpoint
storage governance. A trusted receipt must be retained outside application DB authority.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Mapping, Sequence

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from app.core.audit_codec_v2 import (
    CHECKPOINT,
    Event,
    Genesis,
    bounded,
    digest_text,
    frame,
    integer,
    timestamp,
    uuid_text,
)


@dataclass(frozen=True)
class StoredEvent:
    event: Event
    event_hash: bytes
    request_hash: bytes


@dataclass(frozen=True)
class Head:
    epoch_id: str
    sequence: int
    event_hash: bytes


@dataclass(frozen=True)
class Integrity:
    valid: bool
    event_count: int
    first_bad_sequence: int | None
    reason: str


def verify_snapshot(genesis: Genesis, stored_genesis: bytes, head: Head, rows: Sequence[StoredEvent]) -> Integrity:
    """Validate exact protocol bytes, inventory, sequence and head in one snapshot.

    Callers must obtain all inputs in one consistent DB snapshot. This cannot detect
    removal of an uncheckpointed suffix together with a matching head rollback.
    """
    seq = None
    try:
        previous = genesis.genesis_hash()
        if previous != stored_genesis:
            return Integrity(False, len(rows), None, "genesis_digest")
        if uuid_text(head.epoch_id) != uuid_text(genesis.epoch_id):
            return Integrity(False, len(rows), None, "head_epoch")
        event_ids, source_ids = set(), set()
        for seq, stored in enumerate(rows, 1):
            event = stored.event
            if (uuid_text(event.ledger_id), uuid_text(event.org_id), uuid_text(event.epoch_id)) != (
                uuid_text(genesis.ledger_id),
                uuid_text(genesis.org_id),
                uuid_text(genesis.epoch_id),
            ):
                return Integrity(False, len(rows), seq, "event_scope")
            event_id, source_id = uuid_text(event.event_id), uuid_text(event.source_event_id)
            if event_id in event_ids or source_id in source_ids:
                return Integrity(False, len(rows), seq, "duplicate_identity")
            event_ids.add(event_id)
            source_ids.add(source_id)
            if event.sequence != seq or type(event.sequence) is not int or event.previous_hash != previous:
                return Integrity(False, len(rows), seq, "ordering")
            if event.request_hash() != stored.request_hash or event.event_hash() != stored.event_hash:
                return Integrity(False, len(rows), seq, "event_digest")
            previous = event.event_hash()
        integer(head.sequence, minimum=0)
        if head.sequence != len(rows) or head.event_hash != previous:
            return Integrity(False, len(rows), None, "head_inventory")
        return Integrity(True, len(rows), None, "internal_integrity_only")
    except (ValueError, TypeError, UnicodeError, OverflowError):
        return Integrity(False, len(rows), seq, "invalid_encoding")


@dataclass(frozen=True)
class Checkpoint:
    ledger_id: str
    org_id: str
    epoch_id: str
    sequence: int
    event_hash: bytes
    genesis_hash: bytes
    previous_receipt_digest: bytes | None
    key_id: str
    issued_at: datetime

    def signed_bytes(self) -> bytes:
        return frame(
            CHECKPOINT,
            (
                uuid_text(self.ledger_id),
                uuid_text(self.org_id),
                uuid_text(self.epoch_id),
                integer(self.sequence, minimum=0),
                digest_text(self.event_hash),
                digest_text(self.genesis_hash),
                digest_text(self.previous_receipt_digest) if self.previous_receipt_digest is not None else None,
                bounded(self.key_id, 128),
                timestamp(self.issued_at),
            ),
        )


@dataclass(frozen=True)
class Receipt:
    checkpoint: Checkpoint
    signature: bytes

    def digest(self) -> bytes:
        if not isinstance(self.signature, bytes) or len(self.signature) != 64:
            raise ValueError("invalid checkpoint signature length")
        # Signed fields are prefix/framed and Ed25519 signatures have fixed length.
        return hashlib.sha256(self.checkpoint.signed_bytes() + self.signature).digest()


def verify_receipt(
    receipt: Receipt,
    trusted_keys: Mapping[str, Ed25519PublicKey],
    *,
    previous: Receipt | None,
    now: datetime,
    max_age: timedelta,
    future_skew: timedelta,
) -> None:
    """Verify externally retained continuity and freshness; raise on any failure.

    The previous receipt must already be trusted and retained outside the app DB.
    Passing None after discarding that trusted state does not prove continuity.
    Private signing keys and storage are deliberately outside this module.
    """
    cp = receipt.checkpoint
    receipt.digest()
    key = trusted_keys.get(cp.key_id)
    if not isinstance(key, Ed25519PublicKey):
        raise ValueError("untrusted checkpoint key")
    try:
        key.verify(receipt.signature, cp.signed_bytes())
    except InvalidSignature as exc:
        raise ValueError("invalid checkpoint signature") from exc
    timestamp(now)
    if max_age <= timedelta(0) or future_skew < timedelta(0):
        raise ValueError("invalid checkpoint freshness policy")
    if cp.issued_at > now + future_skew or cp.issued_at < now - max_age:
        raise ValueError("checkpoint outside freshness window")
    if previous is None:
        if cp.previous_receipt_digest is not None:
            raise ValueError("checkpoint continuity anchor required")
    else:
        old = previous.checkpoint
        if cp.previous_receipt_digest != previous.digest():
            raise ValueError("checkpoint continuity mismatch")
        if (uuid_text(cp.ledger_id), uuid_text(cp.org_id), uuid_text(cp.epoch_id), cp.genesis_hash) != (
            uuid_text(old.ledger_id),
            uuid_text(old.org_id),
            uuid_text(old.epoch_id),
            old.genesis_hash,
        ):
            raise ValueError("checkpoint scope mismatch")
        if cp.sequence < old.sequence or cp.issued_at <= old.issued_at:
            raise ValueError("checkpoint replay or rollback")
        if cp.sequence == old.sequence and cp.event_hash != old.event_hash:
            raise ValueError("checkpoint changed same-sequence hash")


def match_checkpoint(receipt: Receipt, genesis: Genesis, head: Head, rows: Sequence[StoredEvent]) -> None:
    """Compare an already verified external receipt to a verified full DB snapshot."""
    cp = receipt.checkpoint
    if (uuid_text(cp.ledger_id), uuid_text(cp.org_id), uuid_text(cp.epoch_id), cp.genesis_hash) != (
        uuid_text(genesis.ledger_id),
        uuid_text(genesis.org_id),
        uuid_text(genesis.epoch_id),
        genesis.genesis_hash(),
    ):
        raise ValueError("checkpoint ledger mismatch")
    if cp.sequence > head.sequence or cp.sequence > len(rows):
        raise ValueError("checkpointed suffix missing from database")
    expected = genesis.genesis_hash() if cp.sequence == 0 else rows[cp.sequence - 1].event_hash
    if cp.event_hash != expected:
        raise ValueError("checkpoint hash mismatch")
