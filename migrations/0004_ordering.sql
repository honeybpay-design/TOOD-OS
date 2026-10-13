-- Stable document order: requirements and questions keep the order in which they appear in the tender.
ALTER TABLE documents ADD COLUMN created_at timestamptz NOT NULL DEFAULT clock_timestamp();
ALTER TABLE requirements ADD COLUMN created_at timestamptz NOT NULL DEFAULT clock_timestamp();
ALTER TABLE questions ADD COLUMN created_at timestamptz NOT NULL DEFAULT clock_timestamp();
