"""F17 regression: real router/role dependency, synthetic identity, no DB or cloud access.

Run alone without database-writing conftest:
PYTHONPATH=apps/api python -B -m unittest discover -s apps/api/tests -p test_f17_delete_denial.py -v
"""
import builtins
import importlib
import pathlib
import socket
import sys
import traceback
import types
import unittest
import uuid
from contextlib import ExitStack
from unittest.mock import patch

ACTOR_ORG = uuid.UUID("00000000-0000-0000-0000-000000000001")
ACTOR_USER = uuid.UUID("00000000-0000-0000-0000-000000000003")
TARGETS = {
    "own_org": str(ACTOR_ORG),
    "foreign_org": "00000000-0000-0000-0000-000000000002",
    "unknown_org": "00000000-0000-0000-0000-000000000004",
    "malformed_id": "not-a-uuid",
}


class DeleteDenialTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.stack = ExitStack()
        cls.app_modules_before = {n for n in sys.modules if n == "app" or n.startswith("app.")}
        cls.original_config = sys.modules.get("app.core.config")
        cls.inserted_config = False
        cls.db_attempts = []
        cls.network_attempts = []
        cls.env_attempts = []

        def no_db(*args, **kwargs):
            cls.db_attempts.append(True)
            raise AssertionError("F17 endpoint attempted a database connection")

        def no_dns(*args, **kwargs):
            cls.network_attempts.append(True)
            raise AssertionError("External DNS/network is forbidden")

        original_connect = socket.socket.connect
        original_connect_ex = socket.socket.connect_ex

        def allow_testclient_socketpair():
            # Windows asyncio uses a loopback socketpair internally. This is
            # TestClient IPC, not an HTTP/provider or database connection.
            return any(
                f.name in {"socketpair", "_fallback_socketpair"}
                and pathlib.Path(f.filename).name == "socket.py"
                for f in traceback.extract_stack()
            )

        def no_connect(sock, address):
            if allow_testclient_socketpair():
                return original_connect(sock, address)
            cls.network_attempts.append(True)
            raise AssertionError("External network connection is forbidden")

        def no_connect_ex(sock, address):
            if allow_testclient_socketpair():
                return original_connect_ex(sock, address)
            cls.network_attempts.append(True)
            raise AssertionError("External network connection is forbidden")

        original_open = builtins.open
        original_path_open = pathlib.Path.open

        def check_env(filename):
            if isinstance(filename, (str, pathlib.Path)) and pathlib.Path(filename).name.startswith(".env"):
                cls.env_attempts.append(True)
                raise AssertionError("Environment-file access is forbidden")

        def no_env_open(filename, *args, **kwargs):
            check_env(filename)
            return original_open(filename, *args, **kwargs)

        def no_env_path_open(path, *args, **kwargs):
            check_env(path)
            return original_path_open(path, *args, **kwargs)

        try:
            cls.stack.enter_context(patch("socket.getaddrinfo", no_dns))
            cls.stack.enter_context(patch.object(socket.socket, "connect", no_connect))
            cls.stack.enter_context(patch.object(socket.socket, "connect_ex", no_connect_ex))
            cls.stack.enter_context(patch("builtins.open", no_env_open))
            cls.stack.enter_context(patch.object(pathlib.Path, "open", no_env_path_open))

            import psycopg

            cls.stack.enter_context(patch.object(psycopg, "connect", side_effect=no_db))
            cls.stack.enter_context(patch.object(psycopg.Connection, "connect", side_effect=no_db))
            cls.stack.enter_context(patch.object(psycopg.AsyncConnection, "connect", side_effect=no_db))

            if "app.routes" not in sys.modules:
                config = types.ModuleType("app.core.config")
                config.settings = types.SimpleNamespace(
                    database_url="synthetic://blocked",
                    database_admin_url="synthetic://blocked",
                    auth_database_url="synthetic://blocked",
                    ai_provider="template",
                    stripe_secret_key="",
                    stripe_webhook_secret="",
                    storage_dir="unused-synthetic-storage",
                    allowed_regions={"europe-west2"},
                )
                sys.modules["app.core.config"] = config
                cls.inserted_config = True

            cls.routes = importlib.import_module("app.routes")
            from fastapi import FastAPI
            from fastapi.testclient import TestClient

            cls.client_type = TestClient
            cls.app = FastAPI()
            cls.app.include_router(cls.routes.admin_router)
        except BaseException:
            cls._restore()
            raise

    @classmethod
    def _restore(cls):
        cls.stack.close()
        if cls.inserted_config:
            for name in list(sys.modules):
                if (name == "app" or name.startswith("app.")) and name not in cls.app_modules_before:
                    del sys.modules[name]
            if cls.original_config is not None:
                sys.modules["app.core.config"] = cls.original_config
            core = sys.modules.get("app.core")
            if core is not None:
                if cls.original_config is None and hasattr(core, "config"):
                    delattr(core, "config")
                elif cls.original_config is not None:
                    core.config = cls.original_config

    @classmethod
    def tearDownClass(cls):
        cls._restore()

    def setUp(self):
        self.app.dependency_overrides.clear()

    def tearDown(self):
        self.app.dependency_overrides.clear()

    def assert_no_external_access(self):
        self.assertEqual(self.db_attempts, [], "DB access must not be attempted")
        self.assertEqual(self.network_attempts, [], "External network must not be attempted")
        self.assertEqual(self.env_attempts, [], "No environment file may be read")

    def test_unauthenticated_delete_is_refused(self):
        with self.client_type(self.app) as client:
            response = client.delete("/admin/tenant/" + TARGETS["foreign_org"])
        self.assertEqual(response.status_code, 401)
        self.assert_no_external_access()


def denial_case(role, target):
    def test(self):
        ctx = self.routes.Ctx(ACTOR_ORG, ACTOR_USER, role)
        self.app.dependency_overrides[self.routes.authenticate] = lambda: ctx
        with self.client_type(self.app) as client:
            response = client.delete("/admin/tenant/" + target)
        self.assertEqual(response.status_code, 403)
        self.assertNotIn("deleted", response.json())
        self.assert_no_external_access()
    return test


for role in ("viewer", "contributor", "bid_manager", "admin", "owner"):
    for target_name, target in TARGETS.items():
        setattr(DeleteDenialTests, "test_" + role + "_" + target_name, denial_case(role, target))
