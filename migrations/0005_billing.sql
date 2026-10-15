-- Stripe subscription tracking
CREATE TABLE IF NOT EXISTS subscriptions (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id uuid NOT NULL REFERENCES organisations(id),
  stripe_customer_id text NOT NULL,
  stripe_subscription_id text,
  plan text NOT NULL CHECK (plan IN ('starter','professional','enterprise')),
  status text NOT NULL DEFAULT 'trialing',
  current_period_end timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);
ALTER TABLE subscriptions ENABLE ROW LEVEL SECURITY;
ALTER TABLE subscriptions FORCE ROW LEVEL SECURITY;
CREATE POLICY subscriptions_org ON subscriptions USING (
  org_id = current_setting('app.current_org_id', true)::uuid
);
-- Plan limits enforced in app layer
ALTER TABLE organisations ADD COLUMN IF NOT EXISTS plan text NOT NULL DEFAULT 'starter';
ALTER TABLE organisations ADD COLUMN IF NOT EXISTS stripe_customer_id text;
