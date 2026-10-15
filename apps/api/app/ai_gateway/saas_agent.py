"""SaaS management agent (blueprint section 23).

Monitors platform health, subscriptions, quotas, and system alerts.
All DB reads use the admin/app connection (cross-tenant aggregation is an admin function).
"""

from __future__ import annotations

import datetime
import logging

import psycopg
import psycopg.rows

from app.core.config import settings

log = logging.getLogger(__name__)


class SaaSAgent:
    """Monitors platform health, subscriptions, quotas, and system alerts."""

    def _conn(self):
        return psycopg.connect(settings.database_url, row_factory=psycopg.rows.dict_row)

    def check_tenant_quotas(self) -> list[dict]:
        """Return tenants that have used 80%+ of their quota."""
        from app.services.billing import get_plan_limits

        with self._conn() as conn:
            orgs = conn.execute(
                "SELECT o.id, o.name, o.plan,"
                " (SELECT count(*) FROM tenders t WHERE t.org_id = o.id) AS tender_count,"
                " (SELECT count(*) FROM memberships m WHERE m.org_id = o.id) AS user_count"
                " FROM organisations o"
            ).fetchall()

        alerts = []
        for org in orgs:
            limits = get_plan_limits(org["plan"])
            max_t = limits["max_tenders"]
            max_u = limits["max_users"]
            if max_t and max_t < 9999 and org["tender_count"] / max_t >= 0.8:
                alerts.append(
                    {
                        "org_id": str(org["id"]),
                        "org_name": org["name"],
                        "resource": "tenders",
                        "usage": org["tender_count"],
                        "limit": max_t,
                        "pct": round(org["tender_count"] / max_t * 100),
                    }
                )
            if max_u and max_u < 9999 and org["user_count"] / max_u >= 0.8:
                alerts.append(
                    {
                        "org_id": str(org["id"]),
                        "org_name": org["name"],
                        "resource": "users",
                        "usage": org["user_count"],
                        "limit": max_u,
                        "pct": round(org["user_count"] / max_u * 100),
                    }
                )
        return alerts

    def get_platform_metrics(self) -> dict:
        """Return MRR, active subscriptions, churn rate, total orgs."""
        PLAN_PRICES = {"starter": 99, "professional": 299, "enterprise": 799}
        try:
            with self._conn() as conn:
                total_orgs = conn.execute("SELECT count(*) AS n FROM organisations").fetchone()["n"]
                active_subs = conn.execute(
                    "SELECT plan, count(*) AS n FROM subscriptions WHERE status = 'active' GROUP BY plan"
                ).fetchall()
                cancelled_last_30 = conn.execute(
                    "SELECT count(*) AS n FROM subscriptions WHERE status = 'cancelled'"
                    " AND updated_at > now() - interval '30 days'"
                ).fetchone()["n"]
        except Exception:  # noqa: BLE001
            log.exception("get_platform_metrics: DB query failed")
            return {
                "mrr_gbp": 0,
                "active_subscriptions": 0,
                "total_orgs": 0,
                "churn_rate_30d_pct": 0.0,
                "subscriptions_by_plan": {},
                "error": "metrics_unavailable",
                "generated_at": datetime.datetime.utcnow().isoformat(),
            }

        mrr = sum(PLAN_PRICES.get(row["plan"], 0) * row["n"] for row in active_subs)
        total_active = sum(row["n"] for row in active_subs)
        churn_rate = round(cancelled_last_30 / max(total_active, 1) * 100, 1)

        return {
            "mrr_gbp": mrr,
            "active_subscriptions": total_active,
            "subscriptions_by_plan": {row["plan"]: row["n"] for row in active_subs},
            "churn_rate_30d_pct": churn_rate,
            "total_orgs": total_orgs,
            "generated_at": datetime.datetime.utcnow().isoformat(),
        }

    def check_system_health(self) -> dict:
        """Check API, DB connections, and AI provider status."""
        db_ok = False
        db_error = None
        try:
            with self._conn() as conn:
                conn.execute("SELECT 1")
            db_ok = True
        except Exception as exc:  # noqa: BLE001
            db_error = str(exc)

        ai_provider = settings.ai_provider
        ai_status = "configured" if ai_provider != "template" else "template_mode"

        return {
            "database": {"ok": db_ok, "error": db_error},
            "ai_provider": {"name": ai_provider, "status": ai_status},
            "overall": "healthy" if db_ok else "degraded",
        }

    def generate_daily_report(self) -> str:
        """Generate a daily summary report for admin."""
        metrics = self.get_platform_metrics()
        health = self.check_system_health()
        quota_alerts = self.check_tenant_quotas()

        lines = [
            f"TOOD-OS Daily Report — {datetime.date.today().isoformat()}",
            "=" * 50,
            f"MRR: £{metrics['mrr_gbp']:,}",
            f"Active subscriptions: {metrics['active_subscriptions']}",
            f"Total organisations: {metrics['total_orgs']}",
            f"30-day churn rate: {metrics['churn_rate_30d_pct']}%",
            f"System health: {health['overall']}",
            f"AI provider: {health['ai_provider']['name']} ({health['ai_provider']['status']})",
        ]
        if quota_alerts:
            lines.append(f"\nQuota alerts ({len(quota_alerts)}):")
            for a in quota_alerts:
                lines.append(f"  - {a['org_name']}: {a['resource']} at {a['pct']}% ({a['usage']}/{a['limit']})")
        else:
            lines.append("\nNo quota alerts.")
        return "\n".join(lines)

    def detect_anomalies(self) -> list[dict]:
        """Detect unusual usage patterns."""
        with self._conn() as conn:
            # Orgs that created > 5 tenders in the last 24h
            burst_tenders = conn.execute(
                "SELECT o.id, o.name, count(*) AS n"
                " FROM tenders t JOIN organisations o ON o.id = t.org_id"
                " WHERE t.created_at > now() - interval '24 hours'"
                " GROUP BY o.id, o.name HAVING count(*) > 5"
            ).fetchall()

        anomalies = []
        for row in burst_tenders:
            anomalies.append(
                {
                    "type": "burst_tender_creation",
                    "org_id": str(row["id"]),
                    "org_name": row["name"],
                    "count_24h": row["n"],
                }
            )
        return anomalies
