-- 0006_oauth.sql: Google OAuth columns and server-side session storage

-- OAuth profile columns on users
ALTER TABLE users ADD COLUMN IF NOT EXISTS google_sub text UNIQUE;
ALTER TABLE users ADD COLUMN IF NOT EXISTS avatar_url text;
ALTER TABLE users ADD COLUMN IF NOT EXISTS display_name text;

-- OAuth accounts: links Google identity to a TOOD user
CREATE TABLE IF NOT EXISTS oauth_accounts (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  provider text NOT NULL DEFAULT 'google',
  provider_sub text NOT NULL,
  email text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (provider, provider_sub)
);
ALTER TABLE oauth_accounts ENABLE ROW LEVEL SECURITY;
ALTER TABLE oauth_accounts FORCE ROW LEVEL SECURITY;
CREATE POLICY IF NOT EXISTS oauth_identity ON oauth_accounts TO auth_user USING (true) WITH CHECK (true);
GRANT SELECT, INSERT, DELETE ON oauth_accounts TO auth_user;

-- Server-side sessions: token stored as SHA-256 hash, never raw
CREATE TABLE IF NOT EXISTS user_sessions (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  org_id uuid NOT NULL REFERENCES organisations(id) ON DELETE CASCADE,
  role text NOT NULL,
  token_hash char(64) NOT NULL UNIQUE,
  expires_at timestamptz NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);
ALTER TABLE user_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_sessions FORCE ROW LEVEL SECURITY;
CREATE POLICY IF NOT EXISTS session_identity ON user_sessions TO auth_user USING (true) WITH CHECK (true);
GRANT SELECT, INSERT, DELETE ON user_sessions TO auth_user;
