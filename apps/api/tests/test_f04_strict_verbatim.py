"""Strict source-unit regressions; standalone, no conftest/env/provider."""

import hashlib
import unittest

from app.services.requirements import extract_candidates, source_units, verify_verbatim


class StrictVerbatimTests(unittest.TestCase):
    SOURCE = "The supplier must retain the complete original inspection record and its supporting photographs throughout the contract and the agreed retention period, preserve the original wording and timestamps of every approved entry, maintain a reliable link between each reported finding and the evidence used to support it, restrict access to authorised staff working on the same contract, and provide the authority with an accurate unaltered copy when requested through the agreed contract management process."

    def test_exact(self):
        self.assertTrue(verify_verbatim(self.SOURCE, self.SOURCE))

    def test_meaning_edits(self):
        for altered in [
            self.SOURCE.replace("must ", "must not ", 1),
            self.SOURCE.replace("must ", "may ", 1),
            self.SOURCE.replace("authorised", "unauthorised"),
            self.SOURCE.replace("original ", "", 1),
            self.SOURCE[13:],
            self.SOURCE[:-30],
        ]:
            with self.subTest(altered=altered):
                self.assertFalse(verify_verbatim(altered, self.SOURCE))

    def test_deleted_not(self):
        self.assertFalse(verify_verbatim(self.SOURCE, self.SOURCE.replace("must ", "must not ", 1)))

    def test_dropped_prohibition_prefix(self):
        self.assertFalse(
            verify_verbatim("disclose customer records.", "The supplier must not disclose customer records.")
        )

    def test_numbers_dates(self):
        for source, candidate in [
            ("Submission must arrive by 30 April 2027 at 12:00.", "Submission must arrive by 31 April 2027 at 12:00."),
            ("The supplier must cover GBP 5000000.", "The supplier must cover GBP 500000."),
            ("The supplier must achieve 99.5% availability.", "The supplier must achieve 99.9% availability."),
        ]:
            self.assertFalse(verify_verbatim(candidate, source))

    def test_case_unicode_invisible(self):
        for candidate in [
            self.SOURCE.lower(),
            self.SOURCE.replace("must", "mu\u200bst"),
            self.SOURCE.replace("must", "m\u0443st"),
            self.SOURCE + "\u200b",
        ]:
            self.assertFalse(verify_verbatim(candidate, self.SOURCE))
        self.assertFalse(
            verify_verbatim(
                "The supplier must retain cafe\u0301 records.", "The supplier must retain caf\u00e9 records."
            )
        )

    def test_threshold_cannot_relax(self):
        self.assertFalse(verify_verbatim(self.SOURCE.replace("must ", "must not ", 1), self.SOURCE, threshold=0))

    def test_empty(self):
        for candidate, source in [("", self.SOURCE), (self.SOURCE, ""), (" ", " "), ("", "")]:
            self.assertFalse(verify_verbatim(candidate, source))

    def test_source_hash(self):
        self.assertTrue(
            verify_verbatim(
                self.SOURCE, self.SOURCE, expected_block_hash=hashlib.sha256(self.SOURCE.encode()).hexdigest()
            )
        )
        self.assertFalse(verify_verbatim(self.SOURCE, self.SOURCE, expected_block_hash="0" * 64))

    def test_boundaries(self):
        source = "  The supplier must retain records.\nThe supplier must not disclose records.  "
        units = source_units(source)
        self.assertEqual(
            [source[a:b] for a, b in units],
            ["The supplier must retain records.", "The supplier must not disclose records."],
        )
        for a, b in units:
            self.assertTrue(verify_verbatim(source[a:b], source))
        self.assertFalse(verify_verbatim("disclose records.", source))

    def test_ambiguous_repeat(self):
        self.assertFalse(
            verify_verbatim(
                "The supplier must retain records.",
                "The supplier must retain records. The supplier must retain records.",
            )
        )

    def test_internal_whitespace_punctuation(self):
        source = "The supplier must retain  original records; no substitutions."
        self.assertTrue(verify_verbatim(source, source))
        self.assertFalse(verify_verbatim(source.replace("  ", " "), source))
        self.assertFalse(verify_verbatim(source.replace(";", ","), source))

    def test_extractor_units(self):
        source = "The supplier must retain records. The supplier must not disclose records."
        candidates = extract_candidates([{"id": "test-block", "text": source}])
        self.assertEqual(len(candidates), 2)
        for candidate in candidates:
            self.assertEqual(candidate["text_verbatim"], source[candidate["unit_start"] : candidate["unit_end"]])
            self.assertTrue(verify_verbatim(candidate["text_verbatim"], source))
            self.assertEqual(candidate["verifier_version"], "verbatim-source-units-v2")


if __name__ == "__main__":
    unittest.main(verbosity=2)
