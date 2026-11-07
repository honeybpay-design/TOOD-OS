"""Approved export disclosure and immutable-replay policy, without config or DB."""

import unittest
from datetime import UTC, datetime

from app.core.audit_export import (
    EXPORT_SCHEMA,
    LEGACY_EXPORT_SCHEMA,
    AuditExportBlocked,
    artifact_snapshot,
    assurance_headers,
    ensure_export_allowed,
)
from app.core.audit_models import AuditAssurance, AuditCheckpointState, LegacyAuditState, V2AuditState

ORG = "00000000-0000-0000-0000-000000000001"


def sample():
    return AuditAssurance(
        org_id=ORG, active_version=2, snapshot_at=datetime(2026, 1, 1, tzinfo=UTC),
        status="v2_internal_only_uncheckpointed",
        legacy=LegacyAuditState(
            event_count="0", min_id=None, max_id=None, current_internal_valid=True, first_bad_id=None,
            history_state="internally_valid", declared_status="verified", declared_first_bad_id=None, incident_ref="",
            observed_manifest_sha256="f"*64, committed_manifest_sha256="f"*64,
            manifest_matches=True, declaration_consistent=True,
        ),
        v2=V2AuditState(status="valid", ledger_id=ORG, epoch_id=ORG, format_version=2,
                        sequence="2", event_count="2", head_hash="1"*64, genesis_hash="0"*64, reason="internal_integrity_only"),
        checkpoint=AuditCheckpointState(status="unconfigured", reason="Test only"), limitations=["Test only"],
    )


class AuditExportPolicyTests(unittest.TestCase):
    def test_unconfigured_checkpoint_remains_explicit_in_local_export(self):
        value = sample()
        ensure_export_allowed(value)
        self.assertEqual(assurance_headers(value, value)["X-Audit-Checkpoint-State"], "unconfigured")

    def test_active_invalid_or_missing_ledger_blocks_export(self):
        for status in ("invalid", "unavailable", "not_active", "prepared_not_active"):
            value = sample()
            value = value.model_copy(update={"v2": value.v2.model_copy(update={"status": status})})
            with self.subTest(status=status), self.assertRaises(AuditExportBlocked):
                ensure_export_allowed(value)

    def test_changed_legacy_or_false_verified_declaration_blocks_export(self):
        for change in ({"manifest_matches": False}, {"manifest_matches": None}, {"declaration_consistent": False}):
            value = sample()
            value = value.model_copy(update={"legacy": value.legacy.model_copy(update=change)})
            with self.subTest(change=change), self.assertRaises(AuditExportBlocked):
                ensure_export_allowed(value)

    def test_captured_broken_or_unverified_history_is_retained_not_reclassified(self):
        for status in ("broken", "unverified"):
            value = sample()
            value = value.model_copy(update={"legacy": value.legacy.model_copy(update={
                "declared_status": status, "history_state": status,
            })})
            ensure_export_allowed(value)
            self.assertEqual(value.legacy.history_state, status)

    def test_invalid_checkpoint_blocks_active_v2_export(self):
        value = sample().model_copy(update={"checkpoint": AuditCheckpointState(status="invalid", reason="wrong key")})
        with self.assertRaises(AuditExportBlocked):
            ensure_export_allowed(value)

    def test_legacy_mode_keeps_original_business_gate_policy(self):
        value = sample().model_copy(update={"active_version": 1})
        ensure_export_allowed(value)

    def test_old_export_without_snapshot_is_honestly_unrecorded(self):
        reference = {"kind": "export", "id": ORG}
        value = artifact_snapshot({"resource": reference}, LEGACY_EXPORT_SCHEMA, reference, sample())
        self.assertIsNone(value)
        self.assertEqual(assurance_headers(value, sample())["X-Audit-Artifact-Snapshot"], "not_recorded")

    def test_new_snapshot_missing_or_resource_mismatched_is_not_downgraded(self):
        for payload in ({"resource": {}}, {"resource": {"kind": "export"}}):
            with self.subTest(payload=payload), self.assertRaises(AuditExportBlocked):
                artifact_snapshot(payload, EXPORT_SCHEMA, {}, sample())

    def test_original_snapshot_sequence_is_distinct_from_later_assessment(self):
        recorded = sample()
        current = recorded.model_copy(update={"v2": recorded.v2.model_copy(update={"sequence": "3"})})
        reference = {"kind": "export", "id": ORG}
        payload = {"resource": reference, "audit_snapshot": recorded.model_dump(mode="json")}
        parsed = artifact_snapshot(payload, EXPORT_SCHEMA, reference, current)
        headers = assurance_headers(parsed, current)
        self.assertEqual(headers["X-Audit-Artifact-Sequence"], "2")
        self.assertEqual(headers["X-Audit-Assessment-Sequence"], "3")

    def test_cross_scope_or_future_position_cannot_be_replayed(self):
        original = sample()
        reference = {}
        for changed in [original.model_copy(update={"org_id": "00000000-0000-0000-0000-000000000002"}),
                        original.model_copy(update={"v2": original.v2.model_copy(update={"sequence": "3"})})]:
            with self.subTest(changed=changed), self.assertRaises(AuditExportBlocked):
                artifact_snapshot({"resource": reference, "audit_snapshot": changed.model_dump(mode="json")},
                                  EXPORT_SCHEMA, reference, original)
