-- TOOD-OS schema (Blueprint Appendix A). Run as the admin role by scripts/migrate.py.
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE FUNCTION app_org_id() RETURNS uuid LANGUAGE sql STABLE AS
$$ SELECT NULLIF(current_setting('app.org_id', true), '')::uuid $$;

CREATE TABLE organisations (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name text NOT NULL,
  plan text NOT NULL DEFAULT 'free',
  data_retention_days integer NOT NULL DEFAULT 365,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE users (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  email text NOT NULL UNIQUE,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE memberships (
  user_id uuid NOT NULL REFERENCES users(id),
  org_id  uuid NOT NULL REFERENCES organisations(id),
  role text NOT NULL CHECK (role IN ('owner','admin','bid_manager','contributor','viewer')),
  PRIMARY KEY (user_id, org_id)
);

CREATE TABLE company_profiles (
  org_id uuid PRIMARY KEY REFERENCES organisations(id),
  legal_name text NOT NULL,
  company_number text,
  ppon text,
  ico_registration text,
  registered_office text,
  turnover_band text,
  employees text,
  regions text[],
  cpv_interests text[],
  capabilities jsonb,
  updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE certificates (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id uuid NOT NULL REFERENCES organisations(id),
  type text NOT NULL,
  number text NOT NULL,
  issued_at date,
  expires_at date NOT NULL,
  file_key text,
  approved_by uuid REFERENCES users(id),
  approved_at timestamptz
);
CREATE TABLE evidence_items (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id uuid NOT NULL REFERENCES organisations(id),
  kind text NOT NULL CHECK (kind IN ('case_study','policy','cv','method','financial','company_fact')),
  title text NOT NULL,
  body text NOT NULL,
  owner_id uuid REFERENCES users(id),
  valid_until date,
  status text NOT NULL DEFAULT 'draft' CHECK (status IN ('draft','approved','retired')),
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE evidence_chunks (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id uuid NOT NULL REFERENCES organisations(id),
  evidence_id uuid NOT NULL REFERENCES evidence_items(id) ON DELETE CASCADE,
  chunk_index integer NOT NULL,
  content_text text NOT NULL,
  embedding_model text NOT NULL,
  embedding vector(1536),
  tsv tsvector GENERATED ALWAYS AS (to_tsvector('english', content_text)) STORED
);
CREATE INDEX ON evidence_chunks USING hnsw (embedding vector_cosine_ops);
CREATE INDEX ON evidence_chunks USING gin (tsv);

CREATE TABLE tenders (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id uuid NOT NULL REFERENCES organisations(id),
  ocid text,
  title text NOT NULL,
  stage text NOT NULL DEFAULT 'qualifying',
  submission_due_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE documents (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id uuid NOT NULL REFERENCES organisations(id),
  tender_id uuid NOT NULL REFERENCES tenders(id),
  version_set integer NOT NULL DEFAULT 1,
  file_name text NOT NULL,
  storage_key text NOT NULL,
  mime_type text NOT NULL,
  sha256 char(64) NOT NULL,
  parse_status text NOT NULL DEFAULT 'queued',
  parser_version text
);
CREATE TABLE doc_blocks (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id uuid NOT NULL REFERENCES organisations(id),
  document_id uuid NOT NULL REFERENCES documents(id),
  page integer,
  bbox jsonb,
  kind text NOT NULL,
  text text NOT NULL,
  section_path text,
  block_hash char(64) NOT NULL
);
CREATE TABLE requirements (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id uuid NOT NULL REFERENCES organisations(id),
  tender_id uuid NOT NULL REFERENCES tenders(id),
  type text NOT NULL,
  title text,
  text_verbatim text NOT NULL,
  weighting numeric(5,2),
  word_limit integer,
  due_at timestamptz,
  source_block_id uuid NOT NULL REFERENCES doc_blocks(id),
  confidence numeric(3,2),
  status text NOT NULL DEFAULT 'unassigned',
  assignee_id uuid REFERENCES users(id)
);
CREATE TABLE questions (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id uuid NOT NULL REFERENCES organisations(id),
  tender_id uuid NOT NULL REFERENCES tenders(id),
  requirement_id uuid REFERENCES requirements(id),
  prompt text NOT NULL,
  weighting numeric(5,2),
  word_limit integer
);

CREATE TABLE drafts (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id uuid NOT NULL REFERENCES organisations(id),
  question_id uuid NOT NULL REFERENCES questions(id),
  version integer NOT NULL,
  content jsonb NOT NULL,
  word_count integer NOT NULL DEFAULT 0,
  UNIQUE (question_id, version)
);
CREATE TABLE draft_claims (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id uuid NOT NULL REFERENCES organisations(id),
  draft_id uuid NOT NULL REFERENCES drafts(id),
  sentence_span text NOT NULL,
  evidence_ids uuid[] NOT NULL DEFAULT '{}',
  status text NOT NULL DEFAULT 'unsupported' CHECK (status IN ('supported','unsupported','acknowledged')),
  acknowledged_by uuid REFERENCES users(id)
);
CREATE TABLE revisions (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id uuid NOT NULL REFERENCES organisations(id),
  draft_id uuid NOT NULL REFERENCES drafts(id) ON DELETE RESTRICT,
  seq integer NOT NULL,
  prev_hash char(64),
  hash char(64) NOT NULL UNIQUE,
  content_snapshot jsonb NOT NULL,
  origin_spans jsonb NOT NULL,
  actor_id uuid,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (draft_id, seq)
);
CREATE TABLE approvals (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id uuid NOT NULL REFERENCES organisations(id),
  draft_id uuid NOT NULL REFERENCES drafts(id),
  revision_id uuid NOT NULL REFERENCES revisions(id),
  approver_id uuid NOT NULL REFERENCES users(id),
  approved_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (draft_id, revision_id)
);
CREATE TABLE audit_events (
  id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  org_id uuid,
  actor_id uuid,
  action text NOT NULL,
  target text,
  ip inet,
  at timestamptz NOT NULL DEFAULT now(),
  prev_hash char(64),
  hash char(64) NOT NULL
);
CREATE TABLE daily_anchors (
  day date PRIMARY KEY,
  merkle_root char(64) NOT NULL,
  signature text NOT NULL,
  anchor_uri text NOT NULL,
  tsa_token text
);
CREATE TABLE export_manifests (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id uuid NOT NULL REFERENCES organisations(id),
  tender_id uuid NOT NULL REFERENCES tenders(id),
  file_sha256 char(64) NOT NULL,
  revision_hashes jsonb NOT NULL,
  created_by uuid NOT NULL REFERENCES users(id),
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE model_cards (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  provider text NOT NULL,
  model_id text NOT NULL,
  version text NOT NULL,
  region text NOT NULL,
  status text NOT NULL CHECK (status IN ('candidate','admitted','suspended','retired')),
  eval_results jsonb NOT NULL,
  admitted_by uuid REFERENCES users(id),
  admitted_at timestamptz,
  UNIQUE (provider, model_id, version)
);
CREATE TABLE jobs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id uuid NOT NULL REFERENCES organisations(id),
  kind text NOT NULL,
  status text NOT NULL DEFAULT 'queued'
    CHECK (status IN ('queued','running','awaiting_review','completed','retrying','failed_safe','cancelled')),
  progress integer NOT NULL DEFAULT 0,
  attempts integer NOT NULL DEFAULT 0,
  lease_until timestamptz,
  error text,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX ON jobs (status, created_at) WHERE status IN ('queued','retrying');
