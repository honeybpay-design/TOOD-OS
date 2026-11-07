-- F36 PROPOSAL ONLY until owner approval; never edit0001 or old hashes.
DO $guard$
BEGIN
 IF current_setting('app.audit_v2_prepare',true) IS DISTINCT FROM 'confirmed-v2-prepare'
   OR current_setting('server_version_num')::integer/10000<>16 OR audit_v2.current_version()<>1 THEN
   RAISE EXCEPTION 'guarded inactive local preparation required'; END IF;
 IF NOT EXISTS(SELECT 1 FROM pg_constraint WHERE conrelid='public.revisions'::regclass
    AND conname='revisions_hash_key' AND contype='u' AND pg_get_constraintdef(oid)='UNIQUE (hash)')
   OR NOT EXISTS(SELECT 1 FROM pg_constraint WHERE conrelid='public.revisions'::regclass
    AND contype='u' AND pg_get_constraintdef(oid)='UNIQUE (draft_id, seq)') THEN
   RAISE EXCEPTION 'reviewed revision identity constraints required'; END IF;
 IF NOT EXISTS(SELECT 1 FROM pg_trigger WHERE tgrelid='public.revisions'::regclass
    AND tgname='revisions_append_only' AND tgenabled='O') THEN
   RAISE EXCEPTION 'append-only control must remain enabled'; END IF;
END $guard$;
CREATE INDEX revisions_hash_lookup_idx ON public.revisions(hash);
-- RESTRICT is intentional: unexpected dependencies must stop the migration.
ALTER TABLE public.revisions DROP CONSTRAINT revisions_hash_key RESTRICT;
-- UUID PK, UNIQUE(draft_id,seq), hash NOT NULL, FK, RLS, triggers, ownership,
-- permissions, all existing rows and compute_hash bytes remain unchanged.
