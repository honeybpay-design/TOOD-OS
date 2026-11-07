-- F01: billing/status reads only these columns; retain forced tenant RLS.
GRANT SELECT (org_id, plan, status, current_period_end, created_at)
ON public.subscriptions TO app_user;
