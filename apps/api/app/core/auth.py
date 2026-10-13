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


def authenticate(authorization: str | None = Header(default=None)) -> Ctx:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(401, "missing bearer token")
    token = authorization.split(" ", 1)[1].strip()
    with psycopg.connect(settings.auth_database_url) as conn:
        row = conn.execute(
            "SELECT org_id, user_id, role FROM api_tokens WHERE token_hash = %s", (hash_token(token),)
        ).fetchone()
    if not row:
        raise HTTPException(401, "invalid token")
    return Ctx(org_id=row[0], user_id=row[1], role=row[2])


def create_account(org_name: str, email: str, role: str = "owner") -> dict:
    """Create an organisation, its first user and a token. The token is returned once."""
    token = "tood_" + secrets.token_urlsafe(32)
    org_id, user_id = uuid.uuid4(), uuid.uuid4()
    with psycopg.connect(settings.auth_database_url) as conn:
        if conn.execute("SELECT 1 FROM users WHERE email = %s", (email.lower(),)).fetchone():
            raise HTTPException(409, "that email is already registered")
        conn.execute("INSERT INTO organisations (id, name) VALUES (%s, %s)", (org_id, org_name))
        conn.execute("INSERT INTO users (id, email) VALUES (%s, %s)", (user_id, email.lower()))
        conn.execute("INSERT INTO memberships (user_id, org_id, role) VALUES (%s, %s, %s)", (user_id, org_id, role))
        conn.execute(
            "INSERT INTO api_tokens (org_id, user_id, role, token_hash) VALUES (%s, %s, %s, %s)",
            (org_id, user_id, role, hash_token(token)),
        )
    return {"token": token, "org_id": str(org_id), "user_id": str(user_id), "role": role}


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
