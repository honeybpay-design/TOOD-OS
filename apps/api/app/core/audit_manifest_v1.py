"""Canonical observed legacy inventory; never reinterpret old audit/revision hashes."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any

from app.core.audit import _hash
from app.core.audit_codec_v2 import signed_integer, uuid_text

FIELDS = {"id", "org_id", "actor_id", "action", "target", "at_epoch", "ip_binary", "prev_hash", "hash"}
EPOCH = re.compile(r"-?(?:0|[1-9][0-9]*)\.[0-9]{6}\Z")


@dataclass(frozen=True)
class LegacyInventory:
    count: int
    min_id: int | None
    max_id: int | None
    first_bad_id: int | None
    internal_valid: bool
    digest: bytes


def text(value: Any, *, nullable: bool = False) -> str | None:
    if nullable and value is None:
        return None
    if not isinstance(value, str) or "\x00" in value:
        raise ValueError("invalid legacy inventory text")
    value.encode("utf-8", errors="strict")
    return value


def inet_binary(value: Any) -> str | None:
    if value is None:
        return None
    value = text(value)
    if value != value.lower() or not re.fullmatch(r"[0-9a-f]+", value):
        raise ValueError("invalid legacy inet encoding")
    raw = bytes.fromhex(value)
    if not (
        (len(raw) == 8 and raw[0] == 2 and raw[1] <= 32 and raw[2:4] == b"\x00\x04")
        or (len(raw) == 20 and raw[0] == 3 and raw[1] <= 128 and raw[2:4] == b"\x00\x10")
    ):
        raise ValueError("invalid legacy inet family/prefix")
    return value


def legacy_inventory(org_id, rows: Iterable[Mapping]) -> LegacyInventory:
    """Hash every observed field, retaining broken legacy hashes and signed IDs.

    Callers supply rows from one tenant-scoped consistent snapshot. No total
    inventory size is confused with the separate64KiB v2event-payload bound.
    """
    org = uuid_text(org_id)
    digest = hashlib.sha256()
    digest.update(b"[")
    count = 0
    minimum = maximum = first_bad = None
    previous = None
    for row in rows:
        if set(row) != FIELDS:
            raise ValueError("legacy inventory field set differs from version1")
        event_id = row["id"]
        identifier = signed_integer(event_id)
        if maximum is not None and event_id <= maximum:
            raise ValueError("legacy inventory must be strictly ordered by ID")
        if uuid_text(row["org_id"]) != org:
            raise ValueError("legacy inventory tenant mismatch")
        actor = uuid_text(row["actor_id"]) if row["actor_id"] is not None else None
        action = text(row["action"])
        target = text(row["target"], nullable=True)
        at = text(row["at_epoch"])
        if at not in {"Infinity", "-Infinity"} and not EPOCH.fullmatch(at):
            raise ValueError("invalid canonical PostgreSQL epoch text")
        ip = inet_binary(row["ip_binary"])
        prev = text(row["prev_hash"], nullable=True)
        stored = text(row["hash"])
        if first_bad is None and (prev != previous or stored != _hash(org, actor, action, target, previous)):
            first_bad = event_id
        encoded = json.dumps(
            [identifier, org, actor, action, target, at, ip, prev, stored],
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
        ).encode("utf-8")
        if count:
            digest.update(b",")
        digest.update(encoded)
        minimum = event_id if minimum is None else minimum
        maximum, previous = event_id, stored
        count += 1
    digest.update(b"]")
    return LegacyInventory(count, minimum, maximum, first_bad, first_bad is None, digest.digest())
