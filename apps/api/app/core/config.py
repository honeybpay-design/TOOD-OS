import pathlib
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.paths import application_root

# Checkouts use their shared repository root; a deployed API uses its own package root.
_here = pathlib.Path(__file__).resolve()
ROOT = pathlib.Path(application_root(_here))


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ROOT / ".env" if (ROOT / ".env").exists() else None,
        extra="ignore",
    )

    database_url: str = "postgresql://app_user:tood_dev_app@localhost:5432/tood"
    database_admin_url: str = "postgresql://postgres:tood_dev_admin@localhost:5432/tood"
    auth_database_url: str = "postgresql://auth_user:tood_dev_auth@localhost:5432/tood"
    ai_allowed_regions: str = "uk-south,eu-west-2,eu-west-1,eu-central-1,europe-west2,europe-west1,europe-west4"
    ai_provider: str = "template"  # no language model is connected in the local pack
    gcp_project: str = "tood-os"
    gcp_region: str = "europe-west2"
    ai_model_id: str = ""  # no remote model is selected or admitted by default
    ai_admission_file: str = ""
    ai_admission_public_key: str = ""  # public verification key, no default trust
    ai_admission_key_id: str = ""
    storage_dir: str = str(ROOT / "data" / "uploads")
    storage_backend: Literal["local", "gcs"] = "local"
    storage_gcs_bucket: str = ""
    storage_gcs_project_number: str = ""
    max_upload_mb: int = 20
    allow_signup: bool = True  # development sign-up. Turn off in any shared environment
    stripe_secret_key: str = ""
    stripe_publishable_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_price_starter: str = ""
    stripe_price_professional: str = ""
    stripe_price_enterprise: str = ""
    google_client_id: str = ""
    google_client_secret: str = ""  # NEVER log this field
    google_redirect_uri: str = "https://tood.uk/auth/google/callback"
    session_secret: str = "change-me-in-production"

    @property
    def allowed_regions(self) -> set[str]:
        return {r.strip().lower() for r in self.ai_allowed_regions.split(",") if r.strip()}


settings = Settings()
