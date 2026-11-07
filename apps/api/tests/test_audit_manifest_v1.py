"""Frozen inventory bytes and hostile/legacy metadata cases, no config or DB access."""

import unittest

from app.core.audit import _hash
from app.core.audit_manifest_v1 import legacy_inventory

ORG = "00000000-0000-0000-0000-000000000001"
OLD_HASH = "5408bb58f4d7ae232815627072de663236ec56920e7b0df384e740c5ee70438b"
GOLDEN = "f6caafb184a4000825315bddd82b08e6f486f4b4bccf8ba30a42c08af4f6551a"


def row(**changes):
    value = dict(id=-1, org_id=ORG, actor_id=None, action="created", target=None,
                 at_epoch="0.000000", ip_binary=None, prev_hash=None, hash=OLD_HASH)
    value.update(changes)
    return value


class LegacyManifestTests(unittest.TestCase):
    def test_empty_preserves_atomic_bootstrap_digest(self):
        result = legacy_inventory(ORG, [])
        self.assertEqual(result.digest.hex(), "4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945")
        self.assertEqual((result.count, result.max_id, result.first_bad_id), (0, None, None))
        self.assertTrue(result.internal_valid)

    def test_frozen_literal_protocol_vector(self):
        result = legacy_inventory(ORG, [row()])
        self.assertEqual(result.digest.hex(), GOLDEN)
        self.assertTrue(result.internal_valid)
        self.assertEqual((result.min_id, result.max_id), (-1, -1))

    def test_previously_unhashed_metadata_changes_inventory(self):
        baseline = legacy_inventory(ORG, [row()])
        for change in [dict(id=0), dict(at_epoch="-0.000001"), dict(ip_binary="02180004c0000207")]:
            with self.subTest(change=change):
                changed = legacy_inventory(ORG, [row(**change)])
                self.assertTrue(changed.internal_valid)
                self.assertNotEqual(changed.digest, baseline.digest)

    def test_broken_hash_and_negative_failure_id_are_retained(self):
        result = legacy_inventory(ORG, [row(hash="broken")])
        self.assertFalse(result.internal_valid)
        self.assertEqual(result.first_bad_id, -1)
        self.assertEqual(result.count, 1)

    def test_complete_signed_bigint_domain_and_global_id_gaps(self):
        first = row(id=-(1 << 63))
        last = row(id=(1 << 63)-1, prev_hash=OLD_HASH, hash=_hash(ORG, None, "created", None, OLD_HASH))
        result = legacy_inventory(ORG, [first, last])
        self.assertTrue(result.internal_valid)
        self.assertEqual((result.min_id, result.max_id, result.count), (-(1 << 63), (1 << 63)-1, 2))
        for invalid in [True, 1.5, -(1 << 63)-1, 1 << 63]:
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                legacy_inventory(ORG, [row(id=invalid)])

    def test_null_empty_text_are_distinct_without_repair(self):
        empty = row(target="", hash=_hash(ORG, None, "created", "", None))
        self.assertNotEqual(legacy_inventory(ORG, [row()]).digest, legacy_inventory(ORG, [empty]).digest)

    def test_no_unicode_normalization(self):
        a = row(action="\u00e9", hash=_hash(ORG, None, "\u00e9", None, None))
        b = row(action="e\u0301", hash=_hash(ORG, None, "e\u0301", None, None))
        self.assertNotEqual(legacy_inventory(ORG, [a]).digest, legacy_inventory(ORG, [b]).digest)
        with self.assertRaises(UnicodeError):
            legacy_inventory(ORG, [row(action="\ud800")])

    def test_observed_pg_inet_vectors_retain_subnet_and_address_family(self):
        values = ["02200004c0000201", "02180004c0000207",
                  "0380001000000000000000000000ffffc0000201", "0340001020010db8000000000000000000000001"]
        self.assertEqual(len({legacy_inventory(ORG, [row(ip_binary=v)]).digest for v in values}), 4)
        for invalid in ["", "02210004c0000201", "0381001000000000000000000000ffffc0000201", "BAD", "01000004c0000201"]:
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                legacy_inventory(ORG, [row(ip_binary=invalid)])

    def test_epoch_full_domain_including_infinity_without_python_datetime_loss(self):
        for value in ["0.000000", "-0.000001", "-62135596800.000000", "Infinity", "-Infinity", "9223371331200.000000"]:
            with self.subTest(value=value):
                self.assertTrue(legacy_inventory(ORG, [row(at_epoch=value)]).internal_valid)
        for value in ["NaN", "0", "00.000000", "1.0", "+1.000000"]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                legacy_inventory(ORG, [row(at_epoch=value)])

    def test_missing_added_or_foreign_fields_are_not_silently_omitted(self):
        missing = row()
        missing.pop("ip_binary")
        for changed in [missing, row(unexpected="not part of version1"), row(org_id="00000000-0000-0000-0000-000000000002")]:
            with self.subTest(changed=changed), self.assertRaises(ValueError):
                legacy_inventory(ORG, [changed])

    def test_duplicate_or_unsorted_legacy_ids_fail(self):
        for rows in [[row(), row()], [row(id=0), row(id=-1)]]:
            with self.assertRaises(ValueError):
                legacy_inventory(ORG, rows)

    def test_inventory_larger_than_event_bound_is_streamed(self):
        def records():
            previous = None
            for ident in range(100):
                target = "x"*2000
                stored = _hash(ORG, None, "created", target, previous)
                yield row(id=ident, target=target, prev_hash=previous, hash=stored)
                previous = stored
        result = legacy_inventory(ORG, records())
        self.assertTrue(result.internal_valid)
        self.assertEqual(result.count, 100)
        self.assertEqual(len(result.digest), 32)
