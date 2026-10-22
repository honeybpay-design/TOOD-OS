"""Offline safety and regression evaluation; no customer or golden-set material."""

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("launch_audit", ROOT / "scripts/launch_audit.py")
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)
sys.path.insert(0, str(ROOT / "apps/api"))
from app.ai_gateway.launch_review import review_readiness  # noqa: E402


class LaunchAuditTests(unittest.TestCase):
    def test_unknown_or_failed_never_releases(self):
        for results in ([], [{"status": "UNVERIFIED"}], [{"status": "FAIL"}]):
            self.assertEqual(audit.release_status(results), "NO_GO")

    def test_detects_firebase_cookie_regression_without_reading_env(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            files = {
                "firebase.json": '{"run": {}}',
                "apps/web/lib/api-proxy.ts": 'get("tood_session")',
                "apps/api/app/routes_oauth.py": 'key="tood_session"',
                ".env": "SECRET=must-not-appear",
            }
            for name, content in files.items():
                target = root / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(content)
            results = audit.collect(root)
            self.assertEqual(results[0]["status"], "FAIL")
            self.assertNotIn("must-not-appear", str(results))

    def test_no_credentials_loaded_without_staging_opt_in(self):
        with patch.dict("os.environ", {"TOOD_AUDIT_ENV": "production"}):
            with self.assertRaises(ValueError):
                review_readiness([{"id": "installation", "status": "PASS"}], "test-staging")

    def test_arbitrary_evidence_rejected_before_credentials(self):
        with patch.dict("os.environ", {"TOOD_AUDIT_ENV": "staging"}):
            with self.assertRaises(ValueError):
                review_readiness([{"id": "secret=abc", "status": "PASS"}], "test-staging")


if __name__ == "__main__":
    unittest.main()
