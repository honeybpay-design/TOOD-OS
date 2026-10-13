"""Google OAuth 2.0 helpers — server-side only. Never log or return the client secret."""

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
    return URLSafeTimedSerializer(settings.session_secret)


def make_state(email_hint: str | None) -> str:
    """Create a signed state value using itsdangerous URLSafeTimedSerializer."""
    payload = {"ts": time.time(), "hint": email_hint or ""}
    return _serializer().dumps(payload)


def verify_state(state: str) -> dict:
    """Verify the signed state. Raises HTTPException(400) on tamper or expiry (max 600 s)."""
    try:
        return _serializer().loads(state, max_age=600)
    except SignatureExpired as exc:
        raise HTTPException(400, "state expired") from exc
    except BadSignature as exc:
        raise HTTPException(400, "invalid state") from exc


def build_auth_url(state: str) -> str:
    """Return Google OAuth authorize URL. redirect_uri=https://tood.uk/auth/google/callback"""
    params = {
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


def exchange_code(code: str) -> dict:
    """Exchange auth code for tokens. Uses GOOGLE_CLIENT_SECRET — never logged."""
    with httpx.Client(timeout=15) as client:
        resp = client.post(
            GOOGLE_TOKEN_URL,
            data={
                "code": code,
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
