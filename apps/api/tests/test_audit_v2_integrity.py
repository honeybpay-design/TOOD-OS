"""Standalone local synthetic tests; no app settings, database, provider or real key use."""



import unittest
import uuid
from dataclasses import replace
from datetime import UTC, datetime, timedelta

from app.core.audit_codec_v2 import Event, Genesis
from app.core.audit_integrity_v2 import (
    Checkpoint,
    Head,
    Receipt,
    StoredEvent,
    match_checkpoint,
    verify_receipt,
    verify_snapshot,
)
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey


class AuditIntegrityV2Tests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 10, 28, 12, 0, tzinfo=UTC)
        self.ids = [str(uuid.UUID(int=i)) for i in range(1, 9)]
        self.genesis = Genesis(*self.ids[:3], b"m" * 32, "verified", 0, None, None, "", b"c" * 32, self.now)
        ev = Event(
            *self.ids[:3],
            1,
            *self.ids[3:7],
            "synthetic.test",
            None,
            self.now,
            "192.0.2.1",
            "test.v1",
            b"{}",
            self.genesis.genesis_hash(),
        )
        self.rows = [StoredEvent(ev, ev.event_hash(), ev.request_hash())]
        self.head = Head(self.ids[2], 1, ev.event_hash())
        self.private = Ed25519PrivateKey.generate()  # Per-test throwaway; never serialized or retained.
        self.keys = {"synthetic-key-1": self.private.public_key()}
        self.cp = Checkpoint(
            *self.ids[:3], 1, ev.event_hash(), self.genesis.genesis_hash(), None, "synthetic-key-1", self.now
        )
        self.receipt = self.sign(self.cp)

    def sign(self, cp):
        return Receipt(cp, self.private.sign(cp.signed_bytes()))

    def verify(self, receipt, previous=None, **kwargs):
        return verify_receipt(
            receipt,
            self.keys,
            previous=previous,
            now=kwargs.get("now", self.now),
            max_age=timedelta(minutes=5),
            future_skew=timedelta(seconds=30),
        )

    def snapshot(self, rows=None, head=None, genesis=None):
        return verify_snapshot(
            genesis or self.genesis, self.genesis.genesis_hash(), head or self.head, self.rows if rows is None else rows
        )

    def test_valid_snapshot_and_receipt(self):
        self.assertTrue(self.snapshot().valid)
        self.verify(self.receipt)
        match_checkpoint(self.receipt, self.genesis, self.head, self.rows)

    def test_every_event_field_tamper_is_detected(self):
        event = self.rows[0].event
        changes = {
            "ledger_id": self.ids[7],
            "org_id": self.ids[7],
            "epoch_id": self.ids[7],
            "sequence": 2,
            "event_id": self.ids[7],
            "source_event_id": self.ids[7],
            "operation_id": self.ids[7],
            "actor_id": self.ids[7],
            "action": "forged",
            "target": "",
            "recorded_at": self.now + timedelta(microseconds=1),
            "source_ip": "192.0.2.2",
            "payload_schema": "test.v2",
            "payload": b'{"not":true}',
            "previous_hash": b"f" * 32,
        }
        self.assertEqual(len(changes), 15)
        for field, value in changes.items():
            with self.subTest(field=field):
                row = replace(self.rows[0], event=replace(event, **{field: value}))
                self.assertFalse(self.snapshot(rows=[row]).valid)

    def test_request_digest_tamper(self):
        self.assertFalse(self.snapshot(rows=[replace(self.rows[0], request_hash=b"f" * 32)]).valid)

    def test_genesis_tamper(self):
        self.assertFalse(self.snapshot(genesis=replace(self.genesis, cutover_digest=b"f" * 32)).valid)

    def test_missing_row_and_wrong_head(self):
        self.assertFalse(self.snapshot(rows=[]).valid)
        self.assertFalse(self.snapshot(head=replace(self.head, event_hash=b"f" * 32)).valid)

    def test_duplicate_event_identity(self):
        ev = replace(self.rows[0].event, sequence=2, previous_hash=self.rows[0].event_hash)
        rows = self.rows + [StoredEvent(ev, ev.event_hash(), ev.request_hash())]
        self.assertFalse(
            self.snapshot(rows=rows, head=replace(self.head, sequence=2, event_hash=ev.event_hash())).valid
        )

    def test_checkpoint_detects_matching_head_and_tail_restore(self):
        old = Head(self.ids[2], 0, self.genesis.genesis_hash())
        # Internal verification alone honestly accepts a consistent older snapshot.
        self.assertTrue(self.snapshot(rows=[], head=old).valid)
        with self.assertRaisesRegex(ValueError, "suffix missing"):
            match_checkpoint(self.receipt, self.genesis, old, [])

    def test_uncheckpointed_suffix_limit_is_explicit(self):
        cp = self.sign(replace(self.cp, sequence=0, event_hash=self.genesis.genesis_hash()))
        old = Head(self.ids[2], 0, self.genesis.genesis_hash())
        self.verify(cp)
        match_checkpoint(cp, self.genesis, old, [])  # Cannot claim detection of later uncheckpointed data.

    def test_signature_wrong_key_and_unknown_key(self):
        for candidate in (replace(self.receipt, signature=b"x" * 64), replace(self.receipt, signature=b"x")):
            with self.subTest(length=len(candidate.signature)), self.assertRaises(ValueError):
                self.verify(candidate)
        with self.assertRaises(ValueError):
            verify_receipt(
                self.receipt,
                {"synthetic-key-1": Ed25519PrivateKey.generate().public_key()},
                previous=None,
                now=self.now,
                max_age=timedelta(minutes=5),
                future_skew=timedelta(0),
            )
        with self.assertRaises(ValueError):
            self.verify(self.sign(replace(self.cp, key_id="untrusted-key")))

    def test_receipt_continuity_and_same_head_heartbeat(self):
        newer = self.sign(
            replace(self.cp, previous_receipt_digest=self.receipt.digest(), issued_at=self.now + timedelta(seconds=1))
        )
        self.verify(newer, previous=self.receipt)
        with self.assertRaises(ValueError):
            self.verify(newer)
        with self.assertRaises(ValueError):
            self.verify(self.receipt, previous=self.receipt)
        with self.assertRaises(ValueError):
            self.verify(self.sign(replace(newer.checkpoint, previous_receipt_digest=b"x" * 32)), previous=self.receipt)

    def test_checkpoint_sequence_rollback_and_same_position_fork(self):
        for changes in ({"sequence": 0}, {"event_hash": b"x" * 32}, {"org_id": self.ids[7]}):
            with self.subTest(changes=tuple(changes)), self.assertRaises(ValueError):
                newer = replace(
                    self.cp,
                    previous_receipt_digest=self.receipt.digest(),
                    issued_at=self.now + timedelta(seconds=1),
                    **changes,
                )
                self.verify(self.sign(newer), previous=self.receipt)

    def test_stale_and_future_receipt(self):
        for at in (self.now - timedelta(minutes=6), self.now + timedelta(seconds=31)):
            with self.subTest(at=at), self.assertRaises(ValueError):
                self.verify(self.sign(replace(self.cp, issued_at=at)))

    def test_checkpoint_snapshot_wrong_ledger_and_hash(self):
        for changes in ({"ledger_id": self.ids[7]}, {"event_hash": b"x" * 32}):
            with self.subTest(changes=tuple(changes)), self.assertRaises(ValueError):
                match_checkpoint(self.sign(replace(self.cp, **changes)), self.genesis, self.head, self.rows)


if __name__ == "__main__":
    unittest.main(verbosity=2)
