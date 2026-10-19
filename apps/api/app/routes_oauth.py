"""OAuth routes (blueprint section 19). Google OAuth 2.0 server-side flow.

Security: tokens and secrets are never logged at any level.
Session tokens are cryptographically random (secrets.token_urlsafe), stored as SHA-256 hashes.
"""

import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone

import psycopg
from fastapi import APIRouter, Header, HTTPException
from fastapi.responses import RedirectResponse

from app.core import oauth
from app.core.config import settings

oauth_router = APIRouter(prefix="/v1/auth")


def _auth_conn():
    """Return a connection using the auth_database_url (auth_user role)."""
    return psycopg.connect(settings.auth_database_url)


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


@oauth_router.get("/google")
def google_login():
    """Initiate Google OAuth: return the auth URL for the frontend to redirect to."""
    state = oauth.make_state(None)
    auth_url = oauth.build_auth_url(state)
    return {"auth_url": auth_url}


@oauth_router.get("/google/callback")
def google_callback(code: str | None = None, state: str | None = None, error: str | None = None):
    """Handle Google redirect. Upsert user and issue a session token."""
    # 1. Handle OAuth errors from Google
    if error:
        raise HTTPException(400, error)
    if not code or not state:
        raise HTTPException(400, "missing code or state")

    # 2. Verify CSRF state
    oauth.verify_state(state)

    # 3. Exchange code → access_token (never logged)
    token_data = oauth.exchange_code(code)
    access_token = token_data.get("access_token")
    if not access_token:
        raise HTTPException(502, "no access_token in google response")

    # 4. Fetch userinfo (sub, email, name, picture) — never log these
    userinfo = oauth.get_userinfo(access_token)
    g_sub = userinfo.get("sub")
    email = (userinfo.get("email") or "").lower().strip()
    display_name = userinfo.get("name") or ""
    avatar_url = userinfo.get("picture") or ""

    if not g_sub or not email:
        raise HTTPException(502, "incomplete userinfo from google")

    # 5. Upsert user and fetch org/role
    with _auth_conn() as conn:
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
            # Check if user exists by email
            user_row = conn.execute("SELECT id FROM users WHERE email = %s", (email,)).fetchone()

            if user_row:
                user_id = user_row[0]
                # Link Google account to existing user
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
                # New user: create org + user + membership + oauth_accounts
                org_id = uuid.uuid4()
                user_id = uuid.uuid4()
                org_name = display_name or email.split("@")[0]
                conn.execute("INSERT INTO organisations (id, name) VALUES (%s, %s)", (org_id, org_name))
                conn.execute(
                    "INSERT INTO users (id, email, google_sub, avatar_url, display_name) VALUES (%s, %s, %s, %s, %s)",
                    (user_id, email, g_sub, avatar_url, display_name),
                )
                conn.execute(
                    "INSERT INTO memberships (user_id, org_id, role) VALUES (%s, %s, 'owner')",
                    (user_id, org_id),
                )
                conn.execute(
                    "INSERT INTO oauth_accounts (user_id, provider, provider_sub, email) VALUES (%s, 'google', %s, %s)",
                    (user_id, g_sub, email),
                )

        # Load membership to get org_id and role
        mem_row = conn.execute(
            "SELECT org_id, role FROM memberships WHERE user_id = %s ORDER BY role DESC LIMIT 1",
            (user_id,),
        ).fetchone()
        if not mem_row:
            raise HTTPException(500, "no membership found for user")
        org_id = mem_row[0]
        role = mem_row[1]

        # 6. Create session token (cryptographically random, stored as hash)
        session_token = secrets.token_urlsafe(32)  # never logged
        token_hash = _hash(session_token)
        expires_at = datetime.now(timezone.utc) + timedelta(days=30)

        # 7. Insert into user_sessions
        conn.execute(
            "INSERT INTO user_sessions (user_id, org_id, role, token_hash, expires_at) VALUES (%s, %s, %s, %s, %s)",
            (user_id, org_id, role, token_hash, expires_at),
        )

    # 8. Issue the session as an HttpOnly cookie and redirect to the dashboard.
    #    The token stays out of the URL. The Next.js callback route relays this
    #    Set-Cookie to the browser under tood.uk (the API host cannot set a
    #    tood.uk cookie directly), so the cookie is stored on the tood.uk origin.
    response = RedirectResponse(url="https://tood.uk/dashboard", status_code=302)
    response.set_cookie(
        key="tood_session",
        value=session_token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=30 * 24 * 60 * 60,
        domain=".tood.uk",
        path="/",
    )
    return response


@oauth_router.get("/session")
def get_session(authorization: str | None = Header(default=None)):
    """Validate a session token. Returns user/org/role if valid and not expired."""
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(401, "missing bearer token")
    raw_token = authorization.split(" ", 1)[1].strip()
    token_hash = _hash(raw_token)  # raw token never logged

    with _auth_conn() as conn:
        row = conn.execute(
            "SELECT user_id, org_id, role, expires_at FROM user_sessions WHERE token_hash = %s AND expires_at > now()",
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
