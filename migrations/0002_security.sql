-- Row-level security, privileges and append-only enforcement.
DO $$
DECLARE t text;
BEGIN
  FOREACH t IN ARRAY ARRAY['company_profiles','certificates','evidence_items','evidence_chunks',
    'tenders','documents','doc_blocks','requirements','questions','drafts','draft_claims',
    'revisions','approvals','export_manifests','jobs']
  LOOP
    EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY', t);
    EXECUTE format('ALTER TABLE %I FORCE ROW LEVEL SECURITY', t);
    EXECUTE format('CREATE POLICY tenant_isolation ON %I TO app_user USING (org_id = app_org_id()) WITH CHECK (org_id = app_org_id())', t);
  END LOOP;
END $$;

-- Identity tables: app_user sees only the current organisation. auth_user (the auth module) manages identity.
ALTER TABLE organisations ENABLE ROW LEVEL SECURITY;
ALTER TABLE organisations FORCE ROW LEVEL SECURITY;
ALTER TABLE memberships ENABLE ROW LEVEL SECURITY;
ALTER TABLE memberships FORCE ROW LEVEL SECURITY;
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE users FORCE ROW LEVEL SECURITY;
CREATE POLICY org_self ON organisations TO app_user USING (id = app_org_id());
CREATE POLICY org_identity ON organisations TO auth_user USING (true) WITH CHECK (true);
CREATE POLICY member_tenant ON memberships TO app_user USING (org_id = app_org_id());
CREATE POLICY member_identity ON memberships TO auth_user USING (true) WITH CHECK (true);
CREATE POLICY user_in_org ON users TO app_user
  USING (EXISTS (SELECT 1 FROM memberships m WHERE m.user_id = users.id AND m.org_id = app_org_id()));
CREATE POLICY user_identity ON users TO auth_user USING (true) WITH CHECK (true);

GRANT USAGE ON SCHEMA public TO app_user, auth_user;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO app_user;
GRANT SELECT, INSERT, UPDATE, DELETE ON organisations, users, memberships TO auth_user;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO app_user;
GRANT EXECUTE ON FUNCTION app_org_id() TO app_user, auth_user;

-- Append-only assurance tables.
REVOKE UPDATE, DELETE, TRUNCATE ON revisions, audit_events, daily_anchors FROM app_user;
REVOKE ALL ON model_cards FROM app_user;
GRANT SELECT ON model_cards TO app_user;

CREATE FUNCTION block_mutation() RETURNS trigger LANGUAGE plpgsql AS
$$ BEGIN RAISE EXCEPTION 'append-only table: % is not modifiable', TG_TABLE_NAME; END $$;
CREATE TRIGGER revisions_append_only BEFORE UPDATE OR DELETE ON revisions
  FOR EACH ROW EXECUTE FUNCTION block_mutation();
CREATE TRIGGER audit_append_only BEFORE UPDATE OR DELETE ON audit_events
  FOR EACH ROW EXECUTE FUNCTION block_mutation();
CREATE TRIGGER anchors_append_only BEFORE UPDATE OR DELETE ON daily_anchors
  FOR EACH ROW EXECUTE FUNCTION block_mutation();
