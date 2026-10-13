-- API tokens (used by the auth module through auth_user) and tenant isolation for the audit log.
CREATE TABLE api_tokens (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id uuid NOT NULL REFERENCES organisations(id),
  user_id uuid NOT NULL REFERENCES users(id),
  role text NOT NULL CHECK (role IN ('owner','admin','bid_manager','contributor','viewer')),
  token_hash char(64) NOT NULL UNIQUE,
  created_at timestamptz NOT NULL DEFAULT now()
);
ALTER TABLE api_tokens ENABLE ROW LEVEL SECURITY;
ALTER TABLE api_tokens FORCE ROW LEVEL SECURITY;
CREATE POLICY token_identity ON api_tokens TO auth_user USING (true) WITH CHECK (true);
GRANT SELECT, INSERT, DELETE ON api_tokens TO auth_user;

-- The audit log was readable across organisations: isolate it like every other customer table.
ALTER TABLE audit_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_events FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON audit_events TO app_user
  USING (org_id = app_org_id()) WITH CHECK (org_id = app_org_id());
