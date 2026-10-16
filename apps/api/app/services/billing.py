"""Stripe billing service (blueprint section 22).

All Stripe calls are funnelled through this module. Business code never calls stripe directly.
Every DB write uses tenant_connection() to honour RLS.
"""

from __future__ import annotations

import logging
import uuid

import stripe

from app.core.config import settings
from app.core.tenant import tenant_connection

log = logging.getLogger(__name__)


def _stripe() -> stripe.Stripe:
    """Return a configured Stripe client. Key resolved at call time so tests can patch settings."""
    return stripe.Stripe(settings.stripe_secret_key)


PLAN_LIMITS: dict[str, dict] = {
    "starter": {"max_tenders": 3, "max_users": 2, "ai_provider": "template"},
    "professional": {"max_tenders": 20, "max_users": 10, "ai_provider": "gemini"},
    "enterprise": {"max_tenders": 9999, "max_users": 9999, "ai_provider": "gemini"},
}

PRICE_IDS: dict[str, str] = {}


def _price_id(plan: str) -> str:
    """Resolve Stripe price ID for a plan from settings."""
    mapping = {
        "starter": settings.stripe_price_starter,
        "professional": settings.stripe_price_professional,
        "enterprise": settings.stripe_price_enterprise,
    }
    price = mapping.get(plan, "")
    if not price:
        raise ValueError(f"No Stripe price configured for plan '{plan}'. Run scripts/setup_stripe.py first.")
    return price


def get_plan_limits(plan: str) -> dict:
    """Return max_tenders, max_users, ai_provider for a plan."""
    return PLAN_LIMITS.get(plan, PLAN_LIMITS["starter"]).copy()


def create_customer(org_id: str, email: str, org_name: str) -> str:
    """Create a Stripe customer for an org and persist the customer_id via RLS-respecting connection."""
    client = _stripe()
    customer = client.customers.create(
        email=email,
        name=org_name,
        metadata={"org_id": str(org_id)},
    )
    with tenant_connection(uuid.UUID(str(org_id))) as conn:
        conn.execute(
            "UPDATE organisations SET stripe_customer_id = %s WHERE id = %s",
            (customer.id, uuid.UUID(str(org_id))),
        )
    log.info("stripe_customer_created org=%s customer=%s", org_id, customer.id)
    return customer.id


def create_checkout_session(org_id: str, plan: str, success_url: str, cancel_url: str) -> str:
    """Create a Stripe Checkout session and return its URL."""
    client = _stripe()
    # Fetch or create customer
    with tenant_connection(uuid.UUID(str(org_id))) as conn:
        row = conn.execute(
            "SELECT stripe_customer_id, name FROM organisations WHERE id = %s",
            (uuid.UUID(str(org_id)),),
        ).fetchone()
    customer_id = row["stripe_customer_id"] if row else None

    session_params: dict = {
        "mode": "subscription",
        "line_items": [{"price": _price_id(plan), "quantity": 1}],
        "success_url": success_url,
        "cancel_url": cancel_url,
        "metadata": {"org_id": str(org_id), "plan": plan},
    }
    if customer_id:
        session_params["customer"] = customer_id

    session = client.checkout.sessions.create(**session_params)
    log.info("checkout_session_created org=%s plan=%s session=%s", org_id, plan, session.id)
    return session.url


def _upsert_subscription(
    conn,
    org_id: uuid.UUID,
    stripe_customer_id: str,
    stripe_subscription_id: str,
    plan: str,
    status: str,
    current_period_end,
) -> None:
    conn.execute(
        """
        INSERT INTO subscriptions
            (org_id, stripe_customer_id, stripe_subscription_id, plan, status, current_period_end)
        VALUES (%s, %s, %s, %s, %s, to_timestamp(%s))
        ON CONFLICT (org_id) DO UPDATE SET
            stripe_customer_id = EXCLUDED.stripe_customer_id,
            stripe_subscription_id = EXCLUDED.stripe_subscription_id,
            plan = EXCLUDED.plan,
            status = EXCLUDED.status,
            current_period_end = EXCLUDED.current_period_end,
            updated_at = now()
        """,
        (org_id, stripe_customer_id, stripe_subscription_id, plan, status, current_period_end),
    )
    conn.execute("UPDATE organisations SET plan = %s WHERE id = %s", (plan, org_id))


def handle_webhook(payload: bytes, sig_header: str) -> dict:
    """Verify Stripe webhook signature and process the event."""
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.stripe_webhook_secret
        )
    except stripe.error.SignatureVerificationError as exc:
        log.warning("stripe_webhook_signature_invalid: %s", exc)
        raise ValueError("Invalid signature") from exc

    event_type = event["type"]
    log.info("stripe_webhook_received type=%s", event_type)

    if event_type == "checkout.session.completed":
        session = event["data"]["object"]
        org_id = uuid.UUID(session["metadata"]["org_id"])
        plan = session["metadata"].get("plan", "starter")
        customer_id = session.get("customer", "")
        subscription_id = session.get("subscription", "")
        with tenant_connection(org_id) as conn:
            _upsert_subscription(conn, org_id, customer_id, subscription_id, plan, "active", None)

    elif event_type == "customer.subscription.updated":
        sub = event["data"]["object"]
        # Determine plan from price metadata
        price_id = sub["items"]["data"][0]["price"]["id"] if sub["items"]["data"] else ""
        plan = "starter"
        if price_id == settings.stripe_price_professional:
            plan = "professional"
        elif price_id == settings.stripe_price_enterprise:
            plan = "enterprise"
        customer_id = sub["customer"]
        # Find org by customer id using admin connection
        import psycopg
        with psycopg.connect(settings.database_url) as conn:
            row = conn.execute(
                "SELECT id FROM organisations WHERE stripe_customer_id = %s", (customer_id,)
            ).fetchone()
        if row:
            org_id = uuid.UUID(str(row[0]))
            with tenant_connection(org_id) as conn:
                _upsert_subscription(
                    conn, org_id, customer_id, sub["id"],
                    plan, sub["status"],
                    sub.get("current_period_end"),
                )

    elif event_type == "customer.subscription.deleted":
        sub = event["data"]["object"]
        customer_id = sub["customer"]
        import psycopg
        with psycopg.connect(settings.database_url) as conn:
            row = conn.execute(
                "SELECT id FROM organisations WHERE stripe_customer_id = %s", (customer_id,)
            ).fetchone()
        if row:
            org_id = uuid.UUID(str(row[0]))
            with tenant_connection(org_id) as conn:
                _upsert_subscription(
                    conn, org_id, customer_id, sub["id"],
                    "starter", "cancelled",
                    sub.get("current_period_end"),
                )

    return {"received": True, "type": event_type}
