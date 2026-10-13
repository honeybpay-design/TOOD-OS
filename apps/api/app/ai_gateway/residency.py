"""Residency guard: the AI Gateway rejects any endpoint outside the approved UK/EU regions."""

from app.core.config import settings


class ResidencyError(Exception):
    pass


def check_endpoint(region: str, allowed: set[str] | None = None) -> None:
    allowed = allowed if allowed is not None else settings.allowed_regions
    if not region or region.lower() not in allowed:
        raise ResidencyError(f"region {region!r} is not approved for processing")


def check_provider(provider) -> None:
    """Local providers (no network, no data leaves the machine) are allowed. Remote ones need an approved region."""
    if getattr(provider, "is_local", False):
        return
    check_endpoint(provider.region)
