"""Pure operation request/namespace contracts; no app settings, DB, files or provider calls."""

import unittest
import uuid
from types import SimpleNamespace

from app.core.operations import Operation, request_bytes


class BusinessRequestTests(unittest.TestCase):
    def test_existing_40000_unicode_character_edit_fits(self):
        encoded = request_bytes({"draft_id": str(uuid.UUID(int=1)), "text": "🟢" * 40000})
        self.assertGreater(len(encoded), 65536)
        self.assertLessEqual(len(encoded), 262144)

    def test_request_over_256k_is_rejected(self):
        with self.assertRaises(ValueError):
            request_bytes({"text": "x" * 262144})

    def test_nested_non_string_keys_rejected(self):
        with self.assertRaises(ValueError):
            request_bytes({"nested": [{1: "invalid"}]})

    def test_nan_not_a_canonical_request(self):
        with self.assertRaises(ValueError):
            request_bytes({"value": float("nan")})

    def test_unicode_wording_is_not_normalized(self):
        self.assertNotEqual(request_bytes({"text": "é"}), request_bytes({"text": "e\u0301"}))

    def operation(self, tenant, mode=2):
        return Operation(None, SimpleNamespace(org_id=tenant), "test", uuid.UUID(int=1), mode, "test.v1", b"x" * 32)

    def test_stable_ids_are_scoped_by_tenant_operation_and_purpose(self):
        a = self.operation(uuid.UUID(int=2))
        b = self.operation(uuid.UUID(int=3))
        self.assertEqual(a.new_id("document"), a.new_id("document"))
        self.assertNotEqual(a.new_id("document"), a.new_id("export"))
        self.assertNotEqual(a.new_id("document"), b.new_id("document"))

    def test_legacy_requests_keep_independent_random_ids(self):
        a = self.operation(uuid.UUID(int=2), mode=1)
        self.assertNotEqual(a.new_id("document"), a.new_id("document"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
