"""Generation provenance payload contract, using public synthetic metadata only."""

import hashlib
import json
import unittest
from dataclasses import replace
from uuid import UUID

from app.core.audit_v2 import GenerationAudit


class GenerationAuditTests(unittest.TestCase):
    def setUp(self):
        self.value = GenerationAudit(
            UUID(int=1),
            UUID(int=2),
            UUID(int=3),
            b"r" * 32,
            "synthetic-requested-alias",
            "synthetic-returned-version",
            "synthetic-prompt-v1",
            b"a" * 32,
        )

    def test_all_existing_receipt_fields_explicit(self):
        payload = json.loads(self.value.payload())
        self.assertEqual(
            set(payload),
            {
                "draft_id",
                "question_id",
                "revision_id",
                "revision_hash",
                "requested_model_id",
                "actual_model_id",
                "prompt_version",
                "signed_admission_digest",
                "source",
            },
        )
        self.assertEqual(payload["revision_hash"], (b"r" * 32).hex())
        self.assertEqual(payload["signed_admission_digest"], (b"a" * 32).hex())
        self.assertEqual(payload["requested_model_id"], "synthetic-requested-alias")
        self.assertEqual(payload["actual_model_id"], "synthetic-returned-version")
        self.assertEqual(payload["source"], "admitted_model")

    def test_every_generation_binding_changes_committed_payload(self):
        original = hashlib.sha256(self.value.payload()).digest()
        changes = {
            "draft_id": UUID(int=4),
            "question_id": UUID(int=4),
            "revision_id": UUID(int=4),
            "revision_hash": b"x" * 32,
            "requested_model_id": "synthetic-other-request",
            "actual_model_id": "synthetic-other-return",
            "prompt_version": "synthetic-prompt-v2",
            "signed_admission_digest": b"x" * 32,
        }
        for field, value in changes.items():
            with self.subTest(field=field):
                self.assertNotEqual(original, hashlib.sha256(replace(self.value, **{field: value}).payload()).digest())

    def test_current_template_is_explicit_without_admission_receipt(self):
        value = replace(
            self.value,
            requested_model_id="template-v0",
            actual_model_id="template-v0",
            prompt_version="template-draft-1",
            signed_admission_digest=None,
        )
        payload = json.loads(value.payload())
        self.assertEqual(payload["source"], "template")
        self.assertIsNone(payload["signed_admission_digest"])
        with self.assertRaises(ValueError):
            replace(value, signed_admission_digest=b"a" * 32).payload()

    def test_missing_malformed_admission_or_revision_digest_rejected(self):
        for changes in (
            {"signed_admission_digest": None},
            {"signed_admission_digest": b"a"},
            {"revision_hash": b"r"},
            {"requested_model_id": ""},
            {"revision_id": "invalid"},
        ):
            with self.subTest(changes=tuple(changes)), self.assertRaises(ValueError):
                replace(self.value, **changes).payload()


if __name__ == "__main__":
    unittest.main(verbosity=2)
