"""Google OAuth 2.0 helpers — server-side only. Never log or return the client secret."""

import base64
import hashlib
import secrets
import time

import httpx
from fastapi import HTTPException
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from app.core.config import settings

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"

# redirect_uri must match Google Console EXACTLY — no trailing slash, no variation
REDIRECT_URI = "https://tood.uk/auth/google/callback"


def _serializer() -> URLSafeTimedSerializer:
    if len(settings.session_secret) < 32 or settings.session_secret == "change-me-in-production":
        raise HTTPException(503, "OAuth signing is not configured securely")
    return URLSafeTimedSerializer(settings.session_secret)


def make_state(email_hint: str | None, browser_verifier: str | None) -> str:
    """Create a signed state value using itsdangerous URLSafeTimedSerializer."""
    if not _valid_verifier(browser_verifier):
        raise HTTPException(400, "missing or invalid browser verifier")
    payload = {
        "ts": time.time(),
        "hint": email_hint or "",
        "binding": hashlib.sha256(browser_verifier.encode()).hexdigest(),
    }
    return _serializer().dumps(payload)


def _valid_verifier(value: str | None) -> bool:
    return bool(value and len(value) == 64 and all(c in "0123456789abcdef" for c in value))


def verify_state(state: str, browser_verifier: str | None) -> dict:
    """Verify the signed state. Raises HTTPException(400) on tamper or expiry (max 600 s)."""
    try:
        payload = _serializer().loads(state, max_age=600)
        if not isinstance(payload, dict) or not _valid_verifier(browser_verifier):
            raise HTTPException(400, "invalid browser binding")
        expected = hashlib.sha256(browser_verifier.encode()).hexdigest()
        binding = payload.get("binding")
        if not isinstance(binding, str) or not secrets.compare_digest(binding, expected):
            raise HTTPException(400, "invalid browser binding")
        return payload
    except SignatureExpired as exc:
        raise HTTPException(400, "state expired") from exc
    except BadSignature as exc:
        raise HTTPException(400, "invalid state") from exc


def build_auth_url(state: str, browser_verifier: str) -> str:
    """Return Google OAuth authorize URL. redirect_uri=https://tood.uk/auth/google/callback"""
    verify_state(state, browser_verifier)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(browser_verifier.encode()).digest()).decode().rstrip("=")
    params = {
        "code_challenge": challenge,
        "code_challenge_method": "S256",
        "client_id": settings.google_client_id,
        "redirect_uri": settings.google_redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "access_type": "offline",
        "prompt": "select_account",
    }
    # Build URL without httpx Request so we keep dependency minimal; use httpx.URL for encoding
    encoded = httpx.URL(GOOGLE_AUTH_URL, params=params)
    return str(encoded)


def exchange_code(code: str, browser_verifier: str) -> dict:
    """Exchange auth code for tokens. Uses GOOGLE_CLIENT_SECRET — never logged."""
    if not _valid_verifier(browser_verifier):
        raise HTTPException(400, "missing or invalid browser verifier")
    with httpx.Client(timeout=15) as client:
        resp = client.post(
            GOOGLE_TOKEN_URL,
            data={
                "code": code,
                "code_verifier": browser_verifier,
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,  # never logged
                "redirect_uri": settings.google_redirect_uri,
                "grant_type": "authorization_code",
            },
        )
    if resp.status_code != 200:
        raise HTTPException(502, "google token exchange failed")
    return resp.json()


def get_userinfo(access_token: str) -> dict:
    """Fetch user profile from Google. Never log access_token."""
    with httpx.Client(timeout=15) as client:
        resp = client.get(
            GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {access_token}"},  # token never logged
        )
    if resp.status_code != 200:
        raise HTTPException(502, "userinfo fetch failed")
    return resp.json()


# Legacy aliases used by some callers
sign_state = make_state
