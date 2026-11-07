"""F19 actual OAuth helpers/router with synthetic settings and guarded I/O."""

import hashlib
import importlib
import json
import secrets
import types
import unittest
import uuid
from contextlib import contextmanager
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

from offline_guards import offline_application

VERIFIER = "a" * 64


class OAuthBindingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.settings = types.SimpleNamespace(
            auth_database_url="synthetic://blocked",
            session_secret=secrets.token_hex(32),
            google_client_id="synthetic-client",
            google_client_secret="",
            google_redirect_uri="https://synthetic.example.invalid/auth/google/callback",
        )
        cls.guard = offline_application(cls.settings)
        cls.stack, forbidden = cls.guard.__enter__()
        try:
            cls.oauth = importlib.import_module("app.core.oauth")
            cls.routes = importlib.import_module("app.routes_oauth")
            cls.exchange_impl = staticmethod(cls.oauth.exchange_code)
            cls.stack.enter_context(patch.object(cls.oauth, "settings", cls.settings))
            cls.stack.enter_context(patch.object(cls.routes, "settings", cls.settings))
            cls.stack.enter_context(patch.object(cls.oauth, "exchange_code", side_effect=forbidden))
            cls.stack.enter_context(patch.object(cls.oauth, "get_userinfo", side_effect=forbidden))
            from fastapi import FastAPI
            from fastapi.testclient import TestClient

            cls.app = FastAPI()
            cls.app.include_router(cls.routes.oauth_router)
            cls.client_type = TestClient
        except BaseException:
            cls.guard.__exit__(*__import__("sys").exc_info())
            raise

    @classmethod
    def tearDownClass(cls):
        cls.guard.__exit__(None, None, None)

    def test_start_requires_well_formed_browser_verifier(self):
        with self.client_type(self.app) as client:
            for verifier in (None, "", "a" * 63, "a" * 65, "z" * 64):
                with self.subTest(verifier=verifier):
                    headers = {"x-oauth-verifier": verifier} if verifier is not None else {}
                    self.assertEqual(client.get("/v1/auth/google", headers=headers).status_code, 400)

    def test_start_binds_state_to_hash_and_is_not_cacheable(self):
        with self.client_type(self.app) as client:
            response = client.get("/v1/auth/google", headers={"x-oauth-verifier": VERIFIER})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["cache-control"], "no-store")
        url = urlparse(response.json()["auth_url"])
        self.assertEqual(url.scheme, "https")
        self.assertEqual(url.hostname, "accounts.google.com")
        params = parse_qs(url.query)
        self.assertEqual(params["redirect_uri"], [self.settings.google_redirect_uri])
        self.assertEqual(params["code_challenge_method"], ["S256"])
        self.assertEqual(params["code_challenge"], ["_-BU_nrgy23GXDr5th1SCfQ5hR20PQulmXM33xVGaOs"])
        self.assertNotIn(VERIFIER, url.query)
        state = params["state"][0]
        payload = self.oauth.verify_state(state, VERIFIER)
        self.assertEqual(payload["binding"], hashlib.sha256(VERIFIER.encode()).hexdigest())
        self.assertNotIn(VERIFIER, json.dumps(payload))

    def test_short_and_default_signing_configuration_fail_closed(self):
        for secret in ("", "short", "change-me-in-production"):
            with self.subTest(configuration="unsafe"), patch.object(self.settings, "session_secret", secret):
                with self.client_type(self.app) as client:
                    response = client.get("/v1/auth/google", headers={"x-oauth-verifier": VERIFIER})
                self.assertEqual(response.status_code, 503)

    def test_callback_rejects_other_browser_before_provider_or_db(self):
        state = self.oauth.make_state(None, VERIFIER)
        with self.client_type(self.app) as client:
            for verifier in (None, "", "b" * 64, "a" * 63, "z" * 64):
                with self.subTest(verifier=verifier):
                    headers = {"x-oauth-verifier": verifier} if verifier is not None else {}
                    response = client.get(
                        "/v1/auth/google/callback", params={"code": "synthetic", "state": state}, headers=headers
                    )
                    self.assertEqual(response.status_code, 400)

    def test_tampered_state_is_rejected(self):
        from fastapi import HTTPException

        state = self.oauth.make_state(None, VERIFIER)
        with self.assertRaises(HTTPException) as caught:
            self.oauth.verify_state(state + "tampered", VERIFIER)
        self.assertEqual(caught.exception.status_code, 400)

    def test_expiry_is_enforced_by_actual_timed_signer(self):
        from fastapi import HTTPException

        with patch("itsdangerous.timed.time.time", return_value=1_000_000):
            state = self.oauth.make_state(None, VERIFIER)
        with patch("itsdangerous.timed.time.time", return_value=1_000_601):
            with self.assertRaises(HTTPException) as caught:
                self.oauth.verify_state(state, VERIFIER)
        self.assertEqual(caught.exception.status_code, 400)
        self.assertEqual(caught.exception.detail, "state expired")

    def test_legacy_unbound_and_non_object_signed_payloads_are_rejected(self):
        from fastapi import HTTPException

        for payload in ({"hint": "legacy"}, ["invalid-object"], {"binding": 7}):
            with self.subTest(payload_type=type(payload).__name__):
                state = self.oauth._serializer().dumps(payload)
                with self.assertRaises(HTTPException) as caught:
                    self.oauth.verify_state(state, VERIFIER)
                self.assertEqual(caught.exception.status_code, 400)

    def test_new_transaction_does_not_validate_older_browser_binding(self):
        from fastapi import HTTPException

        second = "b" * 64
        first_state = self.oauth.make_state(None, VERIFIER)
        second_state = self.oauth.make_state(None, second)
        with self.assertRaises(HTTPException):
            self.oauth.verify_state(first_state, second)
        self.assertEqual(
            self.oauth.verify_state(second_state, second)["binding"], hashlib.sha256(second.encode()).hexdigest()
        )

    def test_cancelled_or_incomplete_callback_never_contacts_provider(self):
        with self.client_type(self.app) as client:
            for params in ({"error": "access_denied"}, {}, {"code": "synthetic"}, {"state": "synthetic"}):
                with self.subTest(keys=sorted(params)):
                    self.assertEqual(client.get("/v1/auth/google/callback", params=params).status_code, 400)

    def test_valid_callback_keeps_hashed_session_storage_and_no_store(self):
        user_id, org_id = uuid.uuid4(), uuid.uuid4()
        writes = []

        class Cursor:
            def __init__(self, row=None):
                self.row = row

            def fetchone(self):
                return self.row

        class Connection:
            def execute(self, query, params=()):
                if query.startswith("SELECT user_id FROM oauth_accounts"):
                    return Cursor((user_id,))
                if query.startswith("SELECT org_id, role FROM memberships"):
                    return Cursor((org_id, "owner"))
                writes.append((query, params))
                return Cursor()

        @contextmanager
        def fake_connection():
            yield Connection()

        state = self.oauth.make_state(None, VERIFIER)
        with (
            patch.object(self.routes, "_auth_conn", fake_connection),
            patch.object(self.oauth, "exchange_code", return_value={"access_token": "synthetic"}),
            patch.object(
                self.oauth,
                "get_userinfo",
                return_value={"sub": "synthetic", "email": "test@example.invalid", "email_verified": True},
            ),
        ):
            with self.client_type(self.app) as client:
                response = client.get(
                    "/v1/auth/google/callback",
                    params={"code": "synthetic", "state": state},
                    headers={"x-oauth-verifier": VERIFIER},
                )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["cache-control"], "no-store")
        token = response.json()["session_token"]
        stored = next(params for query, params in writes if query.startswith("INSERT INTO user_sessions"))
        self.assertEqual(stored[3], hashlib.sha256(token.encode()).hexdigest())
        self.assertNotIn(token, repr(writes))

    def test_actual_token_exchange_sends_transaction_pkce_verifier(self):
        httpx = self.oauth.httpx
        original_client = httpx.Client
        seen = []

        def token_endpoint(request):
            self.assertEqual(str(request.url), self.oauth.GOOGLE_TOKEN_URL)
            self.assertEqual(request.method, "POST")
            fields = parse_qs(request.content.decode())
            self.assertEqual(fields["code_verifier"], [VERIFIER])
            self.assertEqual(fields["code"], ["synthetic-code"])
            self.assertEqual(fields["grant_type"], ["authorization_code"])
            seen.append(True)
            return httpx.Response(200, json={"access_token": "synthetic"})

        transport = httpx.MockTransport(token_endpoint)

        def client_factory(*args, **kwargs):
            return original_client(*args, transport=transport, **kwargs)

        with patch.object(httpx, "Client", client_factory):
            self.assertEqual(self.exchange_impl("synthetic-code", VERIFIER), {"access_token": "synthetic"})
        self.assertEqual(seen, [True])

    def test_provider_contract_rejects_code_for_a_different_verifier(self):
        from fastapi import HTTPException

        httpx = self.oauth.httpx
        original_client = httpx.Client

        def token_endpoint(request):
            fields = parse_qs(request.content.decode())
            if fields.get("code_verifier") != [VERIFIER]:
                return httpx.Response(400, json={"error": "invalid_grant"})
            return httpx.Response(200, json={"access_token": "synthetic"})

        transport = httpx.MockTransport(token_endpoint)

        def client_factory(*args, **kwargs):
            return original_client(*args, transport=transport, **kwargs)

        with patch.object(httpx, "Client", client_factory):
            with self.assertRaises(HTTPException) as caught:
                self.exchange_impl("synthetic-code", "b" * 64)
        self.assertEqual(caught.exception.status_code, 502)
        self.assertEqual(caught.exception.detail, "google token exchange failed")

    def test_token_exchange_requires_verifier_before_http_client_creation(self):
        from fastapi import HTTPException

        with patch.object(self.oauth.httpx, "Client", side_effect=AssertionError("must fail before network setup")):
            with self.assertRaises(HTTPException) as caught:
                self.exchange_impl("synthetic-code", "")
        self.assertEqual(caught.exception.status_code, 400)


if __name__ == "__main__":
    unittest.main()
