"""F18 deterministic evidence-support regressions, with no env, DB or network.
Run: PYTHONPATH=apps/api python -B -m unittest discover -s apps/api/tests -p test_f18_claim_support.py -v
"""
import builtins
import importlib
import pathlib
import socket
import sys
import types
import unittest
from contextlib import ExitStack
from unittest.mock import patch

EID = '00000000-0000-0000-0000-000000000001'
OTHER = '00000000-0000-0000-0000-000000000002'


class ClaimSupportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.stack = ExitStack()
        cls.before = {name for name in sys.modules if name == 'app' or name.startswith('app.')}
        cls.original_config = sys.modules.get('app.core.config')
        cls.inserted = cls.original_config is None

        def forbidden(*args, **kwargs):
            raise AssertionError('F18 regression attempted external I/O')

        original_open = builtins.open
        original_path_open = pathlib.Path.open

        def check_env(path):
            if isinstance(path, (str, pathlib.Path)) and pathlib.Path(path).name.startswith('.env'):
                raise AssertionError('F18 regression attempted an environment-file read')

        def safe_open(path, *args, **kwargs):
            check_env(path)
            return original_open(path, *args, **kwargs)

        def safe_path_open(path, *args, **kwargs):
            check_env(path)
            return original_path_open(path, *args, **kwargs)

        try:
            cls.stack.enter_context(patch('builtins.open', safe_open))
            cls.stack.enter_context(patch.object(pathlib.Path, 'open', safe_path_open))
            cls.stack.enter_context(patch('socket.getaddrinfo', forbidden))
            cls.stack.enter_context(patch.object(socket.socket, 'connect', forbidden))
            cls.stack.enter_context(patch.object(socket.socket, 'connect_ex', forbidden))
            import psycopg
            cls.stack.enter_context(patch.object(psycopg, 'connect', forbidden))
            cls.stack.enter_context(patch.object(psycopg.Connection, 'connect', forbidden))
            cls.stack.enter_context(patch.object(psycopg.AsyncConnection, 'connect', forbidden))
            if cls.inserted:
                config = types.ModuleType('app.core.config')
                config.settings = types.SimpleNamespace(ai_provider='template', allowed_regions={'local'})
                sys.modules['app.core.config'] = config
            cls.drafting = importlib.import_module('app.services.drafting')
        except BaseException:
            cls.tearDownClass()
            raise

    @classmethod
    def tearDownClass(cls):
        cls.stack.close()
        if cls.inserted:
            for name in list(sys.modules):
                if (name == 'app' or name.startswith('app.')) and name not in cls.before:
                    del sys.modules[name]
            core = sys.modules.get('app.core')
            if core is not None and hasattr(core, 'config'):
                delattr(core, 'config')

    def verify(self, claim, body, status='approved', tag=EID):
        return self.drafting.verify_claims(
            f'{claim} [EV:{tag}]',
            {EID: {'body': body, 'status': status, 'title': 'Synthetic approved evidence'}},
        )

    def test_exact_approved_claim_is_supported(self):
        result = self.verify('We delivered 42 projects.', 'We delivered 42 projects.')
        self.assertEqual(result[0]['status'], 'supported')

    def test_whitespace_and_ordinary_case_variants_are_supported(self):
        result = self.verify('We are ISO certified.', 'WE are  ISO\ncertified.')
        self.assertEqual(result[0]['status'], 'supported')

    def test_complete_sentence_inside_longer_evidence_is_supported(self):
        result = self.verify('We delivered 42 projects.', 'Our office is in London. We delivered 42 projects. Contact us.')
        self.assertEqual(result[0]['status'], 'supported')

    def test_unrelated_and_meaning_reversed_evidence_is_unsupported(self):
        cases = [
            ('We are ISO certified.', 'Our office walls are blue.'),
            ('We delivered 42 projects.', 'We have 142 desks.'),
            ('We delivered 42 projects.', 'We have 42 desks.'),
            ('We are ISO certified.', 'We are not ISO certified.'),
            ('We are not ISO certified.', 'We are ISO certified.'),
            ('We reduced costs by 18%.', 'We increased costs by 18%.'),
            ('We delivered 42 projects.', 'We delivered 24 projects.'),
            ('We saved \u00a342 million.', 'We spent \u00a342 million.'),
        ]
        for claim, body in cases:
            with self.subTest(claim=claim, body=body):
                result = self.verify(claim, body)
                self.assertTrue(result)
                self.assertEqual(result[0]['status'], 'unsupported')

    def test_substring_cannot_drop_attribution(self):
        result = self.verify('We are certified.', 'A supplier said we are certified. This is unverified.')
        self.assertEqual(result[0]['status'], 'unsupported')

    def test_substring_cannot_drop_qualifying_clause(self):
        result = self.verify('We delivered 42 projects.', 'We delivered 42 projects, according to an unverified estimate.')
        self.assertEqual(result[0]['status'], 'unsupported')

    def test_unapproved_evidence_never_passes(self):
        for status in ('draft', 'retired'):
            with self.subTest(status=status):
                result = self.verify('We delivered 42 projects.', 'We delivered 42 projects.', status=status)
                self.assertEqual(result[0]['status'], 'unsupported')

    def test_missing_or_foreign_evidence_never_passes(self):
        result = self.verify('We delivered 42 projects.', 'We delivered 42 projects.', tag=OTHER)
        self.assertEqual(result[0]['status'], 'unsupported')
        result = self.drafting.verify_claims(f'We delivered 42 projects. [EV:{EID}]', {})
        self.assertEqual(result[0]['status'], 'unsupported')

    def test_missing_citation_is_unsupported(self):
        result = self.drafting.verify_claims('We delivered 42 projects.', {})
        self.assertEqual(result[0]['status'], 'unsupported')

    def test_multiple_citations_cannot_launder_one_unsupported_source(self):
        text = f'We delivered 42 projects. [EV:{EID}] [EV:{OTHER}]'
        evidence = {
            EID: {'body':'We delivered 42 projects.', 'status':'approved', 'title':'Exact'},
            OTHER: {'body':'We have 42 desks.', 'status':'approved', 'title':'Unrelated'},
        }
        self.assertEqual(self.drafting.verify_claims(text, evidence)[0]['status'], 'unsupported')
        evidence[OTHER]['body'] = 'We delivered 42 projects.'
        self.assertEqual(self.drafting.verify_claims(text, evidence)[0]['status'], 'supported')

    def test_sentences_keep_their_own_citations(self):
        text = f'We delivered 42 projects. [EV:{EID}] We are ISO certified. [EV:{OTHER}]'
        evidence = {
            EID: {'body':'We delivered 42 projects.', 'status':'approved', 'title':'Exact'},
            OTHER: {'body':'We are not ISO certified.', 'status':'approved', 'title':'Contradiction'},
        }
        results = self.drafting.verify_claims(text, evidence)
        self.assertEqual([r['status'] for r in results], ['supported', 'unsupported'])
        self.assertEqual(results[0]['evidence_ids'], [EID])
        self.assertEqual(results[1]['evidence_ids'], [OTHER])

    def test_unproven_paraphrase_remains_unsupported(self):
        result = self.verify('We delivered 42 projects.', 'Our team completed 42 projects.')
        self.assertEqual(result[0]['status'], 'unsupported')


if __name__ == '__main__':
    unittest.main()
