-- F02: one current subscription per tenant; fail atomically on duplicates.
-- The migration runner owns the transaction. No row reconciliation/deletion.
SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '60s';
ALTER TABLE public.subscriptions
    ADD CONSTRAINT subscriptions_org_id_key UNIQUE (org_id) NOT DEFERRABLE;
