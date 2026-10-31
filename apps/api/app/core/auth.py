"""Token authentication and development sign-up.

Tokens are random, shown once, and stored only as SHA-256 hashes. The lookup runs as the auth role
(identity tables only); every customer query then runs as app_user inside a tenant transaction.
Password sign-in, MFA and SSO replace this module (blueprint section 19).
"""

import hashlib
import secrets
import uuid
from dataclasses import dataclass

import psycopg
from fastapi import Header, HTTPException

from app.core.config import settings

ROLE_RANK = {"viewer": 0, "contributor": 1, "bid_manager": 2, "admin": 3, "owner": 4}


@dataclass
class Ctx:
    org_id: uuid.UUID
    user_id: uuid.UUID
    role: str

    def require(self, minimum: str) -> None:
        if ROLE_RANK[self.role] < ROLE_RANK[minimum]:
            raise HTTPException(403, f"role '{self.role}' cannot do this; '{minimum}' or higher is required")


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def authenticate_session(token: str) -> Ctx | None:
    """Look up a valid, non-expired session token from user_sessions. Returns Ctx or None."""
    token_hash = hash_token(token)
    with psycopg.connect(settings.auth_database_url) as conn:
        row = conn.execute(
            "SELECT s.user_id, s.org_id, m.role FROM user_sessions AS s "
            "JOIN memberships AS m ON m.user_id = s.user_id AND m.org_id = s.org_id "
            "WHERE s.token_hash = %s AND s.expires_at > now()",
            (token_hash,),
        ).fetchone()
    if not row:
        return None
    return Ctx(org_id=row[1], user_id=row[0], role=row[2])


def authenticate(
    authorization: str | None = Header(default=None),
    x_session_token: str | None = Header(default=None),
) -> Ctx:
    # Try X-Session-Token header first (OAuth session flow)
    if x_session_token:
        ctx = authenticate_session(x_session_token)
        if ctx:
            return ctx
        raise HTTPException(401, "session expired or invalid")

    # Fall back to Bearer token (existing JWT/API key flow)
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(401, "missing bearer token")
    token = authorization.split(" ", 1)[1].strip()
    with psycopg.connect(settings.auth_database_url) as conn:
        row = conn.execute(
            "SELECT t.org_id, t.user_id, m.role FROM api_tokens AS t "
            "JOIN memberships AS m ON m.user_id = t.user_id AND m.org_id = t.org_id "
            "WHERE t.token_hash = %s",
            (hash_token(token),),
        ).fetchone()
    if not row:
        raise HTTPException(401, "invalid token")
    return Ctx(org_id=row[0], user_id=row[1], role=row[2])


def _bootstrap_identity(conn, org_name, email, role, token_hash, subject, avatar, display, record_legacy):
    """Fixed-purpose DB boundary; returns identity references, never plaintext credentials."""
    if conn.autocommit:
        raise ValueError("identity bootstrap requires a transaction")
    row = conn.execute(
        "SELECT org_id, user_id, role FROM audit_v2.bootstrap_identity(%s,%s,%s,%s,%s,%s,%s,%s)",
        (org_name, email, role, token_hash, subject, avatar, display, record_legacy),
    ).fetchone()
    if row is None:
        raise RuntimeError("identity bootstrap did not return identity references")
    return (row["org_id"], row["user_id"], row["role"]) if isinstance(row, dict) else tuple(row)


def create_account(org_name: str, email: str, role: str = "owner", *, audit_creation: bool = False) -> dict:
    """Return a new token once, after identity and required audit transaction commit.

    Actual signup requests the legacy creation event atomically. Internal v1 helper
    callers keep their existing optional-event behavior. V2 always requires the
    fixed account-created event and epoch, regardless of this compatibility flag.
    """
    token = "tood_" + secrets.token_urlsafe(32)
    try:
        with psycopg.connect(settings.auth_database_url) as conn:
            if conn.execute("SELECT 1 FROM users WHERE email = %s", (email.lower(),)).fetchone():
                raise HTTPException(409, "that email is already registered")
            org_id, user_id, actual_role = _bootstrap_identity(
                conn, org_name, email.lower(), role, hash_token(token), None, None, None, audit_creation
            )
    except psycopg.errors.UniqueViolation:
        raise HTTPException(409, "that email is already registered") from None
    return {"token": token, "org_id": str(org_id), "user_id": str(user_id), "role": actual_role}


def bootstrap_google_identity(conn, org_name: str, email: str, subject: str, avatar: str, display: str):
    """Only after verified provider identity/link checks; join caller session transaction."""
    org_id, user_id, _ = _bootstrap_identity(conn, org_name, email, "owner", None, subject, avatar, display, False)
    return org_id, user_id


def add_member(org_id: uuid.UUID, email: str, role: str) -> dict:
    """Add a user with a role to an existing organisation (used by tests and the admin console)."""
    token = "tood_" + secrets.token_urlsafe(32)
    user_id = uuid.uuid4()
    with psycopg.connect(settings.auth_database_url) as conn:
        conn.execute("INSERT INTO users (id, email) VALUES (%s, %s)", (user_id, email.lower()))
        conn.execute("INSERT INTO memberships (user_id, org_id, role) VALUES (%s, %s, %s)", (user_id, org_id, role))
        conn.execute(
            "INSERT INTO api_tokens (org_id, user_id, role, token_hash) VALUES (%s, %s, %s, %s)",
            (org_id, user_id, role, hash_token(token)),
        )
    return {"token": token, "user_id": str(user_id), "role": role}
