"""Synthetic public protocol vectors; no fixture DB/config/provider access."""

import unittest
import uuid
from dataclasses import replace
from datetime import UTC, datetime, timedelta, timezone

from app.core import audit_codec_v2 as codec

U = uuid.UUID("11111111-1111-4111-8111-111111111111")


class AuditV2CodecTests(unittest.TestCase):
    def event(self):
        return codec.Event(
            U,
            U,
            U,
            1,
            U,
            U,
            U,
            None,
            "synthetic.created",
            "",
            datetime(2026, 1, 1, tzinfo=UTC),
            "192.0.2.1",
            "synthetic-v1",
            b"{}",
            b"0" * 32,
        )

    def test_literal_length_vectors(self):
        for value, expected in [
            (None, "00"),
            ("", "010000000000000000"),
            ("A", "01000000000000000141"),
            ("é", "010000000000000002c3a9"),
        ]:
            self.assertEqual(codec.field(value).hex(), expected)

    def test_null_empty_delimiters_are_distinct(self):
        self.assertNotEqual(codec.frame(codec.REQUEST, [None, ""]), codec.frame(codec.REQUEST, ["", None]))
        self.assertNotEqual(codec.frame(codec.REQUEST, ["a|b", "c"]), codec.frame(codec.REQUEST, ["a", "b|c"]))

    def test_domain_separation(self):
        self.assertNotEqual(codec.frame(codec.EVENT, ["x"]), codec.frame(codec.GENESIS, ["x"]))
        with self.assertRaises(ValueError):
            codec.frame(b"unknown", [])

    def test_unicode_is_not_normalized(self):
        self.assertNotEqual(codec.field("é"), codec.field("e\u0301"))
        self.assertEqual(codec.field("😀")[1:9].hex(), "0000000000000004")

    def test_forbidden_text_and_nonfinite_payload(self):
        for value in ["x\x00y", "\ud800", "x" * 65537]:
            with self.assertRaises((ValueError, UnicodeError)):
                codec.field(value)
        for value in [
            {"value": float("nan")},
            {"value": float("inf")},
            {1: "ambiguous"},
            {"nested": {1: 2}},
            {"nested": ({1: 2},)},
        ]:
            with self.assertRaises(ValueError):
                codec.canonical_payload(value)

    def test_sequence_checked(self):
        for value in [0, -1, True, 1.0, 1 << 63]:
            with self.assertRaises(ValueError):
                codec.integer(value)
        self.assertEqual(codec.integer((1 << 63) - 1), "9223372036854775807")

    def test_time_is_utc_microseconds(self):
        local = datetime(2026, 1, 1, 1, 30, 0, 7, timezone(timedelta(hours=1)))
        self.assertEqual(codec.timestamp(local), "2026-01-01T00:30:00.000007Z")
        self.assertEqual(codec.timestamp(datetime(1, 1, 1, tzinfo=UTC)), "0001-01-01T00:00:00.000000Z")
        with self.assertRaises(ValueError):
            codec.timestamp(datetime(2026, 1, 1))

    def test_ip_hosts_only(self):
        self.assertEqual(codec.ip_text("2001:0db8::1/128"), "2001:db8::1")
        self.assertEqual(codec.ip_text("::ffff:192.0.2.1"), "::ffff:192.0.2.1")
        for address in ["192.0.2.1/24", "2001:db8::1/64", "fe80::1%eth0"]:
            with self.assertRaises(ValueError):
                codec.ip_text(address)

    def test_every_event_field_is_bound(self):
        event = self.event()
        other = uuid.UUID("22222222-2222-4222-8222-222222222222")
        variants = {
            "ledger_id": other,
            "org_id": other,
            "epoch_id": other,
            "sequence": 2,
            "event_id": other,
            "source_event_id": other,
            "operation_id": other,
            "actor_id": other,
            "action": "synthetic.changed",
            "target": None,
            "recorded_at": event.recorded_at + timedelta(microseconds=1),
            "source_ip": "203.0.113.7",
            "payload_schema": "synthetic-v2",
            "payload": b"{ }",
            "previous_hash": b"1" * 32,
        }
        for key, value in variants.items():
            with self.subTest(field=key):
                self.assertNotEqual(event.event_hash(), replace(event, **{key: value}).event_hash())

    def test_retry_identity_excludes_server_observations(self):
        event = self.event()
        retried = replace(event, source_ip="203.0.113.7", recorded_at=event.recorded_at + timedelta(days=1), sequence=2)
        self.assertEqual(event.request_hash(), retried.request_hash())
        self.assertNotEqual(event.event_hash(), retried.event_hash())

    def test_uuid_case_is_canonical(self):
        text = "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee"
        self.assertEqual(codec.uuid_text(text.upper()), text)

    def test_payload_has_stable_json_bytes(self):
        self.assertEqual(codec.canonical_payload({"z": "é", "a": 1}), b'{"a":1,"z":"\xc3\xa9"}')

    def test_broken_legacy_must_be_disclosed(self):
        genesis = codec.Genesis(
            U, U, U, b"m" * 32, "broken", 2, 42, 42, "SYNTHETIC-FORK", b"c" * 32, datetime(2026, 1, 1, tzinfo=UTC)
        )
        self.assertEqual(len(genesis.genesis_hash()), 32)
        for changed in [
            replace(genesis, incident_ref=""),
            replace(genesis, legacy_first_bad_id=None),
            replace(genesis, legacy_status="verified"),
        ]:
            with self.assertRaises(ValueError):
                changed.genesis_hash()

    def test_legacy_inventory_retains_signed_ids(self):
        genesis = codec.Genesis(
            U, U, U, b"m" * 32, "broken", 2, 0, -1, "SYNTHETIC-LEGACY", b"c" * 32, datetime(2026, 1, 1, tzinfo=UTC)
        )
        self.assertEqual(len(genesis.genesis_hash()), 32)
        self.assertEqual(codec.signed_integer(-(1 << 63)), "-9223372036854775808")
        for invalid in [-(1 << 63) - 1, True, 1 << 63]:
            with self.assertRaises(ValueError):
                codec.signed_integer(invalid)

    def test_impossible_inventory_is_rejected(self):
        genesis = codec.Genesis(
            U, U, U, b"m" * 32, "broken", 2, 42, 42, "SYNTHETIC-LEGACY", b"c" * 32, datetime(2026, 1, 1, tzinfo=UTC)
        )
        for invalid in [
            replace(genesis, legacy_count=-1),
            replace(genesis, legacy_count=0, legacy_max_id=None),
            replace(genesis, legacy_first_bad_id=43),
        ]:
            with self.assertRaises(ValueError):
                invalid.genesis_hash()


if __name__ == "__main__":
    unittest.main(verbosity=2)
