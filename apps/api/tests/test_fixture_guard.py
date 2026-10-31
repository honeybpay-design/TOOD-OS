"""Standalone negative-target safety regressions; no conftest, credentials or database."""

import copy
import unittest
from unittest.mock import patch

from fixture_guard import RLS_TABLES, TRIGGERS, FixtureGuardError, guard_environment, verify_database


def environment():
    return {
        "TOOD_TEST_SUITE_ONLY": "true",
        "TOOD_TEST_RUN_ID": "a" * 32,
        "TOOD_TEST_EVIDENCE_DIR": "/results",
        "AI_PROVIDER": "template",
        "STORAGE_BACKEND": "local",
        "GCP_PROJECT": "synthetic-no-cloud",
        "GOOGLE_APPLICATION_CREDENTIALS": "/nonexistent/synthetic-audit-credentials.json",
        "DATABASE_ADMIN_URL": "postgresql://postgres@synthetic-db:5432/postgres",
        "DATABASE_URL": "postgresql://app_user@synthetic-db:5432/postgres",
        "AUTH_DATABASE_URL": "postgresql://auth_user@synthetic-db:5432/postgres",
    }


class FakeDatabase:
    def __init__(self):
        self.identity = ("16.15", "postgres", "postgres")
        self.marker = [("a" * 32,)]
        self.triggers = list(TRIGGERS)
        self.roles = [("app_user", False, False), ("auth_user", False, False)]
        self.rls = [(name, True, True) for name in RLS_TABLES]
        self.sql = []

    def execute(self, sql, params=None):
        self.sql.append(sql)
        if "current_setting('server_version')" in sql:
            self.rows = [self.identity]
        elif "audit_test_only.run_identity" in sql:
            self.rows = self.marker
        elif "pg_trigger" in sql:
            self.rows = self.triggers
        elif "pg_roles" in sql:
            self.rows = self.roles
        elif "relrowsecurity" in sql:
            self.rows = self.rls
        else:
            raise AssertionError("Unexpected or non-read-only guard SQL")
        return self

    def fetchone(self):
        return self.rows[0] if self.rows else None

    def fetchall(self):
        return self.rows


class FixtureGuardTests(unittest.TestCase):
    def test_explicit_internal_configuration_requires_no_file_or_network_access(self):
        with patch("builtins.open", side_effect=AssertionError("Unexpected file read")):
            self.assertEqual(guard_environment(environment()), "a" * 32)

    def test_missing_or_wrong_mandatory_settings_fail_closed(self):
        for key in [
            "TOOD_TEST_SUITE_ONLY",
            "TOOD_TEST_RUN_ID",
            "AI_PROVIDER",
            "STORAGE_BACKEND",
            "GCP_PROJECT",
            "DATABASE_ADMIN_URL",
            "DATABASE_URL",
            "AUTH_DATABASE_URL",
            "GOOGLE_APPLICATION_CREDENTIALS",
            "TOOD_TEST_EVIDENCE_DIR",
        ]:
            env = environment()
            env.pop(key)
            with self.subTest(key=key), self.assertRaises(FixtureGuardError):
                guard_environment(env)

    def test_external_localhost_other_role_credentials_options_and_malformed_urls_are_rejected(self):
        for url in [
            "postgresql://app_user@production.invalid:5432/postgres",
            "postgresql://app_user@127.0.0.1:5432/postgres",
            "postgresql://postgres@synthetic-db:5432/postgres",
            "postgresql://app_user:sentinel-secret@synthetic-db:5432/postgres",
            "postgresql://app_user@synthetic-db:5432/other",
            "postgresql://app_user@synthetic-db:5432/postgres?hostaddr=192.0.2.1",
            "postgresql://app_user@synthetic-db:invalid/postgres",
            "not-a-url",
        ]:
            env = environment()
            env["DATABASE_URL"] = url
            with self.subTest(url=url), self.assertRaises(FixtureGuardError) as error:
                guard_environment(env)
            self.assertNotIn("sentinel-secret", str(error.exception))
            self.assertNotIn(url, str(error.exception))

    def test_ambient_libpq_and_provider_secrets_are_rejected_without_value_disclosure(self):
        for key in ["PGSERVICE", "PGHOSTADDR", "PGOPTIONS", "STRIPE_SECRET_KEY", "GOOGLE_CLIENT_SECRET"]:
            env = environment()
            env[key] = "sentinel-secret"
            with self.subTest(key=key), self.assertRaises(FixtureGuardError) as error:
                guard_environment(env)
            self.assertNotIn("sentinel-secret", str(error.exception))

    def test_nonce_and_external_provider_or_storage_are_rejected(self):
        for key, value in [("TOOD_TEST_RUN_ID", "old-run"), ("AI_PROVIDER", "vertex"), ("STORAGE_BACKEND", "gcs")]:
            env = environment()
            env[key] = value
            with self.subTest(key=key), self.assertRaises(FixtureGuardError):
                guard_environment(env)

    def test_exact_fresh_marker_and_controls_pass_using_only_read_only_queries(self):
        conn = FakeDatabase()
        self.assertEqual(verify_database(conn, "a" * 32)["append_triggers_enabled"], 3)
        self.assertTrue(all(sql.startswith("SELECT ") for sql in conn.sql))

    def test_missing_or_mismatched_marker_rejected_before_control_or_write_queries(self):
        for marker in [[], [("b" * 32,)]]:
            conn = FakeDatabase()
            conn.marker = marker
            with self.subTest(marker=marker), self.assertRaises(FixtureGuardError):
                verify_database(conn, "a" * 32)
            self.assertEqual(len(conn.sql), 2)

    def test_wrong_version_database_or_identity_is_rejected_before_marker(self):
        for identity in [
            ("18.6", "postgres", "postgres"),
            ("16.15", "production", "postgres"),
            ("16.15", "postgres", "app_user"),
        ]:
            conn = FakeDatabase()
            conn.identity = identity
            with self.subTest(identity=identity), self.assertRaises(FixtureGuardError):
                verify_database(conn, "a" * 32)
            self.assertEqual(len(conn.sql), 1)

    def test_disabled_trigger_elevated_role_or_missing_forced_rls_is_rejected(self):
        base = FakeDatabase()
        variants = [
            ("triggers", []),
            ("triggers", [("revisions", "revisions_append_only", "D")]),
            ("roles", [("app_user", True, False), ("auth_user", False, False)]),
            ("roles", [("app_user", False, True), ("auth_user", False, False)]),
            ("rls", [(n, True, False) for n in RLS_TABLES]),
        ]
        for field, value in variants:
            conn = copy.deepcopy(base)
            setattr(conn, field, value)
            with self.subTest(field=field), self.assertRaises(FixtureGuardError):
                verify_database(conn, "a" * 32)
            self.assertTrue(all(sql.startswith("SELECT ") for sql in conn.sql))


if __name__ == "__main__":
    unittest.main()
