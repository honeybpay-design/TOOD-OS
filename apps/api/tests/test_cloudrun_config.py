import importlib.util
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]

SECRET_ENV = {
    "DATABASE_URL": "database-url",
    "AUTH_DATABASE_URL": "auth-database-url",
    "DATABASE_ADMIN_URL": "database-admin-url",
    "STRIPE_SECRET_KEY": "stripe-secret-key",
    "STRIPE_PUBLISHABLE_KEY": "stripe-publishable-key",
    "STRIPE_WEBHOOK_SECRET": "stripe-webhook-secret",
    "STRIPE_PRICE_STARTER": "stripe-price-starter",
    "STRIPE_PRICE_PROFESSIONAL": "stripe-price-professional",
    "STRIPE_PRICE_ENTERPRISE": "stripe-price-enterprise",
    "GOOGLE_CLIENT_ID": "google-client-id",
    "GOOGLE_CLIENT_SECRET": "google-client-secret",
    "SESSION_SECRET": "session-secret",
    "AI_PROVIDER": "ai-provider",
}


def _load_secret_keys() -> list[str]:
    path = ROOT / "scripts" / "setup_gcp_secrets.py"
    spec = importlib.util.spec_from_file_location("setup_gcp_secrets", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.SECRET_KEYS


def test_cloudrun_secret_references_match_secret_manager_ids():
    manifest = (ROOT / "infra" / "cloudrun" / "api.yaml").read_text()
    for env_name, secret_id in SECRET_ENV.items():
        pattern = rf"- name: {env_name}\s+valueFrom:\s+secretKeyRef:\s+name: {secret_id}\s+key: latest"
        assert re.search(pattern, manifest), f"{env_name} must reference {secret_id}:latest"


def test_secret_setup_covers_runtime_auth_secrets():
    secret_keys = _load_secret_keys()
    for key in ("GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET", "SESSION_SECRET"):
        assert key in secret_keys


def test_production_manifest_disables_legacy_signup():
    manifest = (ROOT / "infra" / "cloudrun" / "api.yaml").read_text()
    assert re.search(r'- name: ALLOW_SIGNUP\s+value: "false"', manifest)
