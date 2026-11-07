"""OAuth routes (blueprint section 19). Google OAuth 2.0 server-side flow.

Security: tokens and secrets are never logged at any level.
Session tokens are cryptographically random (secrets.token_urlsafe), stored as SHA-256 hashes.
"""

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

import psycopg
from fastapi import APIRouter, Header, HTTPException, Response

from app.core import oauth
from app.core.auth import bootstrap_google_identity
from app.core.config import settings

oauth_router = APIRouter(prefix="/v1/auth")


def _auth_conn():
    """Return a connection using the auth_database_url (auth_user role)."""
    return psycopg.connect(settings.auth_database_url)


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _identity_lock_keys(subject: str, email: str) -> list[int]:
    """Serialize canonical identity writes without changing schema or role grants."""
    names = ("tood:oauth:google:sub:" + subject, "tood:oauth:google:email:" + email)
    return sorted({int.from_bytes(hashlib.sha256(name.encode()).digest()[:8], "big", signed=True) for name in names})


@oauth_router.get("/google")
def google_login(response: Response, x_oauth_verifier: str | None = Header(default=None)):
    """Initiate Google OAuth: return the auth URL for the frontend to redirect to."""
    state = oauth.make_state(None, x_oauth_verifier)
    response.headers["Cache-Control"] = "no-store"
    auth_url = oauth.build_auth_url(state, x_oauth_verifier)
    return {"auth_url": auth_url}


@oauth_router.get("/google/callback")
def google_callback(
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    x_oauth_verifier: str | None = Header(default=None),
):
    """Handle Google redirect. Upsert user and issue a session token."""
    # 1. Handle OAuth errors from Google
    if error:
        raise HTTPException(400, error)
    if not code or not state:
        raise HTTPException(400, "missing code or state")

    # 2. Verify CSRF state
    oauth.verify_state(state, x_oauth_verifier)

    # 3. Exchange code → access_token (never logged)
    token_data = oauth.exchange_code(code, x_oauth_verifier)
    access_token = token_data.get("access_token")
    if not access_token:
        raise HTTPException(502, "no access_token in google response")

    # 4. Fetch userinfo (sub, email, name, picture) — never log these
    userinfo = oauth.get_userinfo(access_token)
    if not isinstance(userinfo, dict):
        raise HTTPException(502, "incomplete userinfo from google")
    g_sub = userinfo.get("sub")
    raw_email = userinfo.get("email")
    if not isinstance(g_sub, str) or not g_sub or not isinstance(raw_email, str) or not raw_email.strip():
        raise HTTPException(502, "incomplete userinfo from google")
    email = raw_email.lower().strip()
    if userinfo.get("email_verified") is not True:
        raise HTTPException(403, "Google email ownership is not verified")
    display_name = userinfo.get("name") if isinstance(userinfo.get("name"), str) else ""
    avatar_url = userinfo.get("picture") if isinstance(userinfo.get("picture"), str) else ""

    # 5. Upsert user and fetch org/role
    try:
        with _auth_conn() as conn:
            # Consistent lock ordering prevents duplicate creation across concurrent
            # callbacks, including different subjects presenting the same email.
            for key in _identity_lock_keys(g_sub, email):
                conn.execute("SELECT pg_advisory_xact_lock(%s)", (key,))
            # Look up by oauth_accounts first (provider+sub)
            acct_row = conn.execute(
                "SELECT user_id FROM oauth_accounts WHERE provider = 'google' AND provider_sub = %s",
                (g_sub,),
            ).fetchone()

            if acct_row:
                user_id = acct_row[0]
                # Update profile fields on existing user (non-sensitive display data)
                conn.execute(
                    "UPDATE users SET google_sub = %s, avatar_url = %s, display_name = %s WHERE id = %s",
                    (g_sub, avatar_url, display_name, user_id),
                )
            else:
                # A previously stored provider subject is an existing identity binding.
                # Email equality alone never authorizes a new provider-account link.
                user_row = conn.execute("SELECT id FROM users WHERE google_sub = %s", (g_sub,)).fetchone()

                if user_row:
                    user_id = user_row[0]
                    # Restore the mapping for an already-bound legacy Google subject.
                    conn.execute(
                        "UPDATE users SET google_sub = %s, avatar_url = %s, display_name = %s WHERE id = %s",
                        (g_sub, avatar_url, display_name, user_id),
                    )
                    conn.execute(
                        "INSERT INTO oauth_accounts (user_id, provider, provider_sub, email)"
                        " VALUES (%s, 'google', %s, %s)"
                        " ON CONFLICT (provider, provider_sub) DO NOTHING",
                        (user_id, g_sub, email),
                    )
                else:
                    if conn.execute("SELECT id FROM users WHERE email = %s", (email,)).fetchone():
                        raise HTTPException(409, "Google account linking requires existing-account authentication")
                    # Narrow DB function creates only a new identity and its required
                    # epoch/event atomically; provider/link checks above stay mandatory.
                    org_name = display_name or email.split("@")[0]
                    org_id, user_id = bootstrap_google_identity(conn, org_name, email, g_sub, avatar_url, display_name)

            # Load membership to get org_id and role
            mem_row = conn.execute(
                "SELECT org_id, role FROM memberships WHERE user_id = %s ORDER BY role DESC LIMIT 1",
                (user_id,),
            ).fetchone()
            if not mem_row:
                raise HTTPException(403, "no active organisation membership")
            org_id = mem_row[0]
            role = mem_row[1]

            # Existing active-v2 tenants must already have a provisioned epoch/head.
            # Never manufacture missing evidence while logging an existing user in.
            conn.execute("SELECT audit_v2.assert_login_ready(%s)", (org_id,))

            # 6. Create session token (cryptographically random, stored as hash)
            session_token = secrets.token_urlsafe(32)  # never logged
            token_hash = _hash(session_token)
            expires_at = datetime.now(timezone.utc) + timedelta(days=30)

            # 7. Insert into user_sessions
            conn.execute(
                "INSERT INTO user_sessions (user_id, org_id, role, token_hash, expires_at) VALUES (%s, %s, %s, %s, %s)",
                (user_id, org_id, role, token_hash, expires_at),
            )
    except psycopg.errors.UniqueViolation:
        raise HTTPException(409, "Google identity conflict; restart sign-in") from None

    # 8. Return session token as JSON — the Next.js callback route sets the
    #    HttpOnly cookie directly on the tood.uk response, bypassing the
    #    Firebase CDN redirect-stripping issue entirely.
    from fastapi.responses import JSONResponse  # noqa: PLC0415

    return JSONResponse({"session_token": session_token}, headers={"Cache-Control": "no-store"})


@oauth_router.get("/session")
def get_session(authorization: str | None = Header(default=None)):
    """Validate a session token. Returns user/org/role if valid and not expired."""
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(401, "missing bearer token")
    raw_token = authorization.split(" ", 1)[1].strip()
    token_hash = _hash(raw_token)  # raw token never logged

    with _auth_conn() as conn:
        row = conn.execute(
            "SELECT s.user_id, s.org_id, m.role, s.expires_at FROM user_sessions AS s "
            "JOIN memberships AS m ON m.user_id = s.user_id AND m.org_id = s.org_id "
            "WHERE s.token_hash = %s AND s.expires_at > now()",
            (token_hash,),
        ).fetchone()

    if not row:
        raise HTTPException(401, "session expired or invalid")

    return {
        "user_id": str(row[0]),
        "org_id": str(row[1]),
        "role": row[2],
        "expires_at": row[3].isoformat(),
    }


@oauth_router.post("/logout")
def logout(authorization: str | None = Header(default=None)):
    """Invalidate a session token."""
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(401, "missing bearer token")
    raw_token = authorization.split(" ", 1)[1].strip()
    token_hash = _hash(raw_token)  # raw token never logged

    with _auth_conn() as conn:
        conn.execute("DELETE FROM user_sessions WHERE token_hash = %s", (token_hash,))

    return {"ok": True}
