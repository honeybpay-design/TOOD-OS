"""Offline guards for standalone security regressions; no conftest/.env imports."""

import builtins
import pathlib
import socket
import sys
import traceback
import types
from contextlib import ExitStack, contextmanager
from unittest.mock import patch


@contextmanager
def offline_application(settings):
    before = {name for name in sys.modules if name == "app" or name.startswith("app.")}
    original_config = sys.modules.get("app.core.config")
    with ExitStack() as stack:

        def forbidden(*args, **kwargs):
            raise AssertionError("Unexpected database, credentials or external network access")

        original_open = builtins.open
        original_path_open = pathlib.Path.open
        original_connect = socket.socket.connect
        original_connect_ex = socket.socket.connect_ex

        def check_file(path):
            if isinstance(path, (str, pathlib.Path)) and (
                pathlib.Path(path).name.startswith(".env")
                or pathlib.Path(path).name == "application_default_credentials.json"
            ):
                forbidden()

        def safe_open(path, *args, **kwargs):
            check_file(path)
            return original_open(path, *args, **kwargs)

        def safe_path_open(path, *args, **kwargs):
            check_file(path)
            return original_path_open(path, *args, **kwargs)

        def socketpair_only():
            return any(
                frame.name in {"socketpair", "_fallback_socketpair"}
                and pathlib.Path(frame.filename).name == "socket.py"
                for frame in traceback.extract_stack()
            )

        def safe_connect(sock, address):
            if socketpair_only():
                return original_connect(sock, address)
            forbidden()

        def safe_connect_ex(sock, address):
            if socketpair_only():
                return original_connect_ex(sock, address)
            forbidden()

        stack.enter_context(patch("builtins.open", safe_open))
        stack.enter_context(patch.object(pathlib.Path, "open", safe_path_open))
        stack.enter_context(patch("socket.getaddrinfo", forbidden))
        stack.enter_context(patch.object(socket.socket, "connect", safe_connect))
        stack.enter_context(patch.object(socket.socket, "connect_ex", safe_connect_ex))
        import psycopg

        stack.enter_context(patch.object(psycopg, "connect", forbidden))
        stack.enter_context(patch.object(psycopg.Connection, "connect", forbidden))
        stack.enter_context(patch.object(psycopg.AsyncConnection, "connect", forbidden))
        if original_config is None:
            config = types.ModuleType("app.core.config")
            config.settings = settings
            sys.modules["app.core.config"] = config
        try:
            yield stack, forbidden
        finally:
            if original_config is None:
                for name in list(sys.modules):
                    if (name == "app" or name.startswith("app.")) and name not in before:
                        del sys.modules[name]
                core = sys.modules.get("app.core")
                if core is not None and hasattr(core, "config"):
                    delattr(core, "config")
