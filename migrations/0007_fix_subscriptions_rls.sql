-- Migration 0007: Fix subscriptions RLS policy
-- The previous policy in 0005_billing.sql used app.current_org_id (never set).
-- The system sets app.org_id via tenant_connection(). This migration corrects that.

DROP POLICY IF EXISTS subscriptions_org ON subscriptions;

CREATE POLICY subscriptions_org ON subscriptions TO app_user
  USING (org_id = app_org_id())
  WITH CHECK (org_id = app_org_id());
