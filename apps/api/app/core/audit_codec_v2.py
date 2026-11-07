"""Version-fixed audit wire format; no environment, database or provider access.

V1 hashes and revisions are separate protocols and must never be reinterpreted.
"""

from __future__ import annotations

import hashlib
import ipaddress
import json
import struct
import uuid
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime

EVENT = b"TOOD-AUDIT-EVENT\x002\x00"
REQUEST = b"TOOD-AUDIT-REQUEST\x00v2"
GENESIS = b"TOOD-AUDIT-GENESIS\x00v2"
CHECKPOINT = b"TOOD-AUDIT-CHECKPOINT\x00v2"
MAX_PAYLOAD = 65536
MAX_SEQUENCE = (1 << 63) - 1


def field(value: str | None) -> bytes:
    """Null or presence + unsigned big-endian octet length + strict UTF-8."""
    if value is None:
        return b"\x00"
    if not isinstance(value, str) or "\x00" in value:
        raise ValueError("invalid framed text")
    encoded = value.encode("utf-8", errors="strict")
    if len(encoded) > MAX_PAYLOAD:
        raise ValueError("framed text exceeds limit")
    return b"\x01" + struct.pack(">Q", len(encoded)) + encoded


def frame(domain: bytes, values: Iterable[str | None]) -> bytes:
    if domain not in {EVENT, REQUEST, GENESIS, CHECKPOINT}:
        raise ValueError("unsupported audit domain")
    return domain + b"".join(field(value) for value in values)


def uuid_text(value: uuid.UUID | str) -> str:
    return str(value if isinstance(value, uuid.UUID) else uuid.UUID(value))


def integer(value: int, *, minimum: int = 1) -> str:
    if type(value) is not int or not minimum <= value <= MAX_SEQUENCE:
        raise ValueError("integer outside audit range")
    return str(value)


def signed_integer(value: int) -> str:
    if type(value) is not int or not -(1 << 63) <= value <= MAX_SEQUENCE:
        raise ValueError("legacy ID outside BIGINT range")
    return str(value)


def timestamp(value: datetime) -> str:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("audit time must be timezone-aware")
    value = value.astimezone(UTC)
    return (
        f"{value.year:04d}-{value.month:02d}-{value.day:02d}T"
        f"{value.hour:02d}:{value.minute:02d}:{value.second:02d}.{value.microsecond:06d}Z"
    )


def ip_text(value: str | None) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or "%" in value:
        raise ValueError("invalid audit IP")
    address = ipaddress.ip_interface(value)
    if address.network.prefixlen != address.max_prefixlen:
        raise ValueError("audit IP must be a single host")
    if isinstance(address.ip, ipaddress.IPv6Address) and address.ip.ipv4_mapped:
        return "::ffff:" + str(address.ip.ipv4_mapped)
    return address.ip.compressed


def digest_text(value: bytes) -> str:
    if not isinstance(value, bytes) or len(value) != 32:
        raise ValueError("audit digest must be 32 bytes")
    return value.hex()


def bounded(value: str, limit: int, *, empty: bool = False) -> str:
    if not isinstance(value, str) or (not value and not empty):
        raise ValueError("invalid audit text")
    if "\x00" in value or len(value.encode("utf-8")) > limit:
        raise ValueError("audit text exceeds limit")
    return value


def canonical_payload(value: dict) -> bytes:
    """Producer JSON contract, distinct from the database's exact raw-byte hash."""

    def validate(item):
        if isinstance(item, dict):
            if not all(isinstance(key, str) for key in item):
                raise ValueError("payload keys must be strings")
            for child in item.values():
                validate(child)
        elif isinstance(item, (list, tuple)):
            for child in item:
                validate(child)

    if not isinstance(value, dict):
        raise ValueError("payload must be an object")
    validate(value)
    result = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode(
        "utf-8"
    )
    if len(result) > MAX_PAYLOAD:
        raise ValueError("audit payload exceeds limit")
    return result


@dataclass(frozen=True)
class Event:
    ledger_id: uuid.UUID | str
    org_id: uuid.UUID | str
    epoch_id: uuid.UUID | str
    sequence: int
    event_id: uuid.UUID | str
    source_event_id: uuid.UUID | str
    operation_id: uuid.UUID | str
    actor_id: uuid.UUID | str | None
    action: str
    target: str | None
    recorded_at: datetime
    source_ip: str | None
    payload_schema: str
    payload: bytes
    previous_hash: bytes

    def request_fields(self) -> tuple[str | None, ...]:
        if not isinstance(self.payload, bytes) or len(self.payload) > MAX_PAYLOAD:
            raise ValueError("invalid audit payload")
        return (
            uuid_text(self.org_id),
            uuid_text(self.source_event_id),
            uuid_text(self.operation_id),
            uuid_text(self.actor_id) if self.actor_id is not None else None,
            bounded(self.action, 128),
            bounded(self.target, 4096, empty=True) if self.target is not None else None,
            bounded(self.payload_schema, 128),
            hashlib.sha256(self.payload).hexdigest(),
        )

    def request_bytes(self) -> bytes:
        return frame(REQUEST, self.request_fields())

    def request_hash(self) -> bytes:
        return hashlib.sha256(self.request_bytes()).digest()

    def event_bytes(self) -> bytes:
        request = self.request_fields()
        return frame(
            EVENT,
            (
                uuid_text(self.ledger_id),
                request[0],
                uuid_text(self.epoch_id),
                integer(self.sequence),
                uuid_text(self.event_id),
                request[1],
                request[2],
                request[3],
                request[4],
                request[5],
                timestamp(self.recorded_at),
                ip_text(self.source_ip),
                request[6],
                request[7],
                digest_text(self.previous_hash),
            ),
        )

    def event_hash(self) -> bytes:
        return hashlib.sha256(self.event_bytes()).digest()


@dataclass(frozen=True)
class Genesis:
    ledger_id: uuid.UUID | str
    org_id: uuid.UUID | str
    epoch_id: uuid.UUID | str
    manifest_digest: bytes
    legacy_status: str
    legacy_count: int
    legacy_max_id: int | None
    legacy_first_bad_id: int | None
    incident_ref: str
    cutover_digest: bytes
    initialized_at: datetime

    def genesis_bytes(self) -> bytes:
        integer(self.legacy_count, minimum=0)
        if self.legacy_status not in {"verified", "broken", "unverified"}:
            raise ValueError("invalid legacy status")
        if (self.legacy_count == 0) != (self.legacy_max_id is None):
            raise ValueError("legacy inventory does not match maximum ID")
        if self.legacy_count == 0 and self.legacy_first_bad_id is not None:
            raise ValueError("empty history cannot have a failure position")
        if (
            self.legacy_first_bad_id is not None
            and self.legacy_max_id is not None
            and self.legacy_first_bad_id > self.legacy_max_id
        ):
            raise ValueError("failure position exceeds inventory maximum")
        if self.legacy_status == "broken" and self.legacy_first_bad_id is None:
            raise ValueError("broken history requires a failure position")
        if self.legacy_status == "verified" and self.legacy_first_bad_id is not None:
            raise ValueError("verified history cannot have a failure position")
        if self.legacy_status != "verified" and not self.incident_ref:
            raise ValueError("unverified or broken history requires a reference")
        return frame(
            GENESIS,
            (
                uuid_text(self.ledger_id),
                uuid_text(self.org_id),
                uuid_text(self.epoch_id),
                "1",
                "v1-org-actor-action-target-prev",
                self.legacy_status,
                digest_text(self.manifest_digest),
                integer(self.legacy_count, minimum=0),
                signed_integer(self.legacy_max_id) if self.legacy_max_id is not None else None,
                signed_integer(self.legacy_first_bad_id) if self.legacy_first_bad_id is not None else None,
                bounded(self.incident_ref, 512, empty=True),
                digest_text(self.cutover_digest),
                timestamp(self.initialized_at),
            ),
        )

    def genesis_hash(self) -> bytes:
        return hashlib.sha256(self.genesis_bytes()).digest()
