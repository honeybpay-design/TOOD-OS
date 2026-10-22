"""Local go-to-market evidence collection; optional staging Gemini advisory review."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps" / "api"))


def collect(root: Path) -> list[dict]:
    def read(path: str) -> str:
        target = root / path
        return target.read_text(encoding="utf-8") if target.is_file() else ""

    hosting = read("firebase.json")
    proxy = read("apps/web/lib/api-proxy.ts")
    oauth = read("apps/api/app/routes_oauth.py")
    cookie_conflict = '"run"' in hosting and 'get("tood_session")' in proxy and 'key="tood_session"' in oauth
    return [
        {"id": "hosting_session_cookie", "status": "FAIL" if cookie_conflict else "UNVERIFIED"},
        *[{"id": name, "status": "UNVERIFIED"} for name in (
            "installation", "api_tests", "web_build", "evaluation_gates",
            "google_login_end_to_end", "billing_staging", "tenant_isolation",
            "backup_restore", "deployed_revision", "model_admission",
        )],
    ]


def release_status(evidence: list[dict]) -> str:
    return "GO" if evidence and all(x["status"] == "PASS" for x in evidence) else "NO_GO"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checks", action="store_true", help="Run fixed local checks; stop on first failure")
    parser.add_argument("--staging-project", help="Opt in to one paid Gemini call using staging-only ADC")
    args = parser.parse_args()
    evidence = collect(ROOT)
    if args.checks:
        commands = [
            ("installation", [sys.executable, "scripts/verify_install.py"], ROOT),
            ("api_tests", [sys.executable, "-m", "pytest", "-q"], ROOT / "apps/api"),
            ("web_build", ["npm.cmd" if sys.platform == "win32" else "npm", "run", "build"], ROOT / "apps/web"),
            ("evaluation_gates", [sys.executable, "scripts/check_gates.py"], ROOT),
        ]
        for check_id, command, cwd in commands:
            print(f"Running {check_id}...", flush=True)
            try:
                completed = subprocess.run(command, cwd=cwd, capture_output=True, text=True, timeout=300)
                ok = completed.returncode == 0
                if check_id == "installation":
                    ok = ok and "17/17 checks passed" in completed.stdout
                if check_id == "api_tests":
                    ok = ok and "passed" in completed.stdout and "skipped" not in completed.stdout
            except (OSError, subprocess.TimeoutExpired):
                ok = False
            next(x for x in evidence if x["id"] == check_id)["status"] = "PASS" if ok else "FAIL"
            if not ok:
                print(f"FAIL: {check_id}; stopped. Run the command directly for local diagnostics.")
                break
    report = {"scope": "local/staging", "release_status": release_status(evidence), "checks": evidence}
    if args.staging_project:
        from app.ai_gateway.launch_review import review_readiness

        try:
            report["gemini_review"] = review_readiness(evidence, args.staging_project)
        except Exception as exc:
            # SDK and credential errors may contain private paths or tokens; print only type.
            report["gemini_review"] = {"status": "ERROR", "error_type": type(exc).__name__}
            print("Gemini unavailable: verify staging ADC, project, regional access and quota. No fallback.")
    output = ROOT / "tmp" / "launch-audit.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=True, indent=2))
    print(f"Report: {output}")
    return 0 if report["release_status"] == "GO" else 1


if __name__ == "__main__":
    raise SystemExit(main())
