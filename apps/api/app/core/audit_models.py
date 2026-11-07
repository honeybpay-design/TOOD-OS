"""Versioned audit disclosure; cryptographic scope is not a compliance certification."""

from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

DecimalSequence = Annotated[str, Field(pattern=r"^(0|[1-9][0-9]*)$", max_length=19)]
LegacyIdentifier = Annotated[str, Field(pattern=r"^-?(0|[1-9][0-9]*)$", max_length=20)]
HexDigest = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]


class AuditModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class LegacyAuditEvent(AuditModel):
    id: int
    action: str
    target: str | None
    at: str


class V2AuditEvent(AuditModel):
    event_id: str
    sequence: DecimalSequence
    action: str
    target: str | None
    recorded_at: datetime
    event_hash: HexDigest
    payload_schema: str


class LegacyAuditState(AuditModel):
    event_count: DecimalSequence
    min_id: LegacyIdentifier | None
    max_id: LegacyIdentifier | None
    current_internal_valid: bool
    first_bad_id: LegacyIdentifier | None
    history_state: Literal["internally_valid", "broken", "unverified"]
    declared_status: Literal["verified", "broken", "unverified"] | None
    declared_first_bad_id: LegacyIdentifier | None
    incident_ref: str | None
    manifest_version: Literal[1] = 1
    observed_manifest_sha256: HexDigest
    committed_manifest_sha256: HexDigest | None
    manifest_matches: bool | None
    declaration_consistent: bool | None
    hash_envelope_scope: Literal["v1-org-actor-action-target-prev"] = "v1-org-actor-action-target-prev"
    historically_unbound_fields: tuple[Literal["id"], Literal["at"], Literal["ip"]] = ("id", "at", "ip")


class V2AuditState(AuditModel):
    status: Literal["not_active", "prepared_not_active", "valid", "invalid", "unavailable"]
    ledger_id: str | None = None
    epoch_id: str | None = None
    format_version: int | None = None
    sequence: DecimalSequence | None = None
    event_count: DecimalSequence = "0"
    head_hash: HexDigest | None = None
    genesis_hash: HexDigest | None = None
    first_bad_sequence: DecimalSequence | None = None
    reason: str


class AuditCheckpointState(AuditModel):
    status: Literal["unconfigured", "verified", "invalid"]
    verified_through_sequence: DecimalSequence | None = None
    uncheckpointed_events: DecimalSequence | None = None
    receipt_digest: HexDigest | None = None
    issued_at: datetime | None = None
    reason: str


class AuditAssurance(AuditModel):
    schema_version: Literal[2] = 2
    org_id: str
    active_version: Literal[1, 2]
    snapshot_at: datetime
    status: Literal[
        "legacy_only", "v2_unavailable", "v2_integrity_failed", "legacy_manifest_changed",
        "legacy_broken", "legacy_unverified", "checkpoint_invalid",
        "v2_internal_only_uncheckpointed", "checkpointed_prefix_only", "checkpointed_internal_integrity",
    ]
    legacy: LegacyAuditState
    v2: V2AuditState
    checkpoint: AuditCheckpointState
    limitations: list[str]


class AuditLogResponse(AuditModel):
    schema_version: Literal[2] = 2
    chain_ok: bool = Field(description="Deprecated compatibility field: legacy v1 internal hashes only.", deprecated=True)
    chain_ok_scope: Literal["legacy_v1_internal_only"] = "legacy_v1_internal_only"
    first_bad_event: int | None
    events_total: int
    recent: list[LegacyAuditEvent]
    assurance: AuditAssurance
    recent_v2: list[V2AuditEvent]
