"""Export audit scope/reference rules; no provider, environment or key-store access."""

from __future__ import annotations

from app.core.audit_models import AuditAssurance

EXPORT_SCHEMA = "tood.tender-exported.v2"
LEGACY_EXPORT_SCHEMA = "tood.business-operation.v1"


class AuditExportBlocked(ValueError):
    pass


def ensure_export_allowed(assurance: AuditAssurance) -> None:
    """Preserve legacy behavior; active v2 cannot conceal changed/invalid evidence.

    A captured known broken/unverified legacy segment is disclosed. Unconfigured
    checkpoint trust remains explicit; production readiness is a separate gate.
    """
    if assurance.active_version == 1:
        return
    if assurance.v2.status != "valid":
        raise AuditExportBlocked("v2_integrity_unavailable")
    if assurance.legacy.manifest_matches is not True:
        raise AuditExportBlocked("legacy_inventory_changed")
    if assurance.legacy.declared_status == "verified" and assurance.legacy.declaration_consistent is not True:
        raise AuditExportBlocked("legacy_declaration_inconsistent")
    if assurance.checkpoint.status == "invalid":
        raise AuditExportBlocked("checkpoint_invalid")


def artifact_snapshot(payload: dict, payload_schema: str, reference: dict, current: AuditAssurance):
    """Old immutable exports are explicitly unrecorded, never upgraded in place."""
    if not isinstance(payload, dict) or payload.get("resource") != reference:
        raise AuditExportBlocked("export_resource_reference_mismatch")
    if payload_schema == LEGACY_EXPORT_SCHEMA and "audit_snapshot" not in payload:
        return None
    if payload_schema != EXPORT_SCHEMA or "audit_snapshot" not in payload:
        raise AuditExportBlocked("export_snapshot_schema_unavailable")
    recorded = AuditAssurance.model_validate(payload["audit_snapshot"])
    if (
        recorded.org_id != current.org_id or recorded.active_version != current.active_version
        or recorded.v2.ledger_id != current.v2.ledger_id or recorded.v2.epoch_id != current.v2.epoch_id
    ):
        raise AuditExportBlocked("export_snapshot_scope_mismatch")
    ensure_export_allowed(recorded)
    if (
        recorded.v2.sequence is None or current.v2.sequence is None
        or int(recorded.v2.sequence) > int(current.v2.sequence)
        or recorded.legacy.observed_manifest_sha256 != current.legacy.committed_manifest_sha256
    ):
        raise AuditExportBlocked("export_snapshot_position_mismatch")
    return recorded


def assurance_headers(recorded: AuditAssurance | None, assessment: AuditAssurance) -> dict[str, str]:
    return {
        "X-Audit-Assurance-Schema": "2",
        "X-Audit-Artifact-Snapshot": "recorded" if recorded is not None else "not_recorded",
        "X-Audit-Artifact-Sequence": recorded.v2.sequence or "not_active" if recorded else "unrecorded",
        "X-Audit-Assessment-Sequence": assessment.v2.sequence or "not_active",
        "X-Audit-Assessment-Status": assessment.status,
        "X-Audit-Checkpoint-State": assessment.checkpoint.status,
    }
