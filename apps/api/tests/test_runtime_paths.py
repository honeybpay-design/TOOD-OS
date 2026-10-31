"""Path regressions without importing Settings, .env files, credentials or a database."""

import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from app.core.paths import application_root


class RuntimePathTests(unittest.TestCase):
    def test_canonical_windows_checkout_keeps_repository_data_root(self):
        source = pathlib.PureWindowsPath(r"C:\Users\Donny\Desktop\tood.com\apps\api\app\core\config.py")
        self.assertEqual(application_root(source), pathlib.PureWindowsPath(r"C:\Users\Donny\Desktop\tood.com"))

    def test_linux_checkout_keeps_repository_data_root(self):
        source = pathlib.PurePosixPath("/workspace/tood.com/apps/api/app/core/config.py")
        self.assertEqual(application_root(source), pathlib.PurePosixPath("/workspace/tood.com"))

    def test_api_container_uses_app_not_filesystem_root(self):
        source = pathlib.PurePosixPath("/app/app/core/config.py")
        self.assertEqual(application_root(source), pathlib.PurePosixPath("/app"))
        self.assertEqual(application_root(source) / "data" / "uploads", pathlib.PurePosixPath("/app/data/uploads"))
