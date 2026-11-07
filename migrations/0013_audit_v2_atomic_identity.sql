-- F03v2: fixed-purpose atomic identity bootstrap; no live activation.
DO $guard$
BEGIN
 IF current_setting('app.audit_v2_prepare',true) IS DISTINCT FROM 'confirmed-v2-prepare'
   OR current_setting('server_version_num')::integer/10000<>16 OR audit_v2.current_version()<>1 THEN
   RAISE EXCEPTION 'guarded inactive audit v2 preparation required'; END IF;
END $guard$;
ALTER TABLE audit_v2.runtime_state ADD COLUMN cutover_digest bytea
  CHECK(cutover_digest IS NULL OR octet_length(cutover_digest)=32);
ALTER TABLE audit_v2.runtime_state ADD CONSTRAINT active_cutover_reference
  CHECK(version<>2 OR cutover_digest IS NOT NULL);

GRANT USAGE ON SCHEMA public TO audit_v2_onboard_executor;
GRANT INSERT ON public.organisations,public.users,public.memberships,public.api_tokens,public.oauth_accounts
  TO audit_v2_onboard_executor;
GRANT SELECT,INSERT ON public.audit_events TO audit_v2_onboard_executor;
GRANT USAGE ON SEQUENCE public.audit_events_id_seq TO audit_v2_onboard_executor;
GRANT SELECT ON audit_v2.runtime_state,audit_v2.epochs,audit_v2.heads TO audit_v2_onboard_executor;
GRANT EXECUTE ON FUNCTION public.app_org_id(),public.digest(bytea,text) TO audit_v2_onboard_executor;

CREATE POLICY bootstrap_org ON public.organisations FOR INSERT TO audit_v2_onboard_executor
 WITH CHECK(id=public.app_org_id());
CREATE POLICY bootstrap_user ON public.users FOR INSERT TO audit_v2_onboard_executor
 WITH CHECK(id=NULLIF(current_setting('app.user_id',true),'')::uuid);
CREATE POLICY bootstrap_membership ON public.memberships FOR INSERT TO audit_v2_onboard_executor
 WITH CHECK(org_id=public.app_org_id() AND user_id=NULLIF(current_setting('app.user_id',true),'')::uuid);
CREATE POLICY bootstrap_token ON public.api_tokens FOR INSERT TO audit_v2_onboard_executor
 WITH CHECK(org_id=public.app_org_id() AND user_id=NULLIF(current_setting('app.user_id',true),'')::uuid);
CREATE POLICY bootstrap_google ON public.oauth_accounts FOR INSERT TO audit_v2_onboard_executor
 WITH CHECK(provider='google' AND user_id=NULLIF(current_setting('app.user_id',true),'')::uuid);
CREATE POLICY bootstrap_legacy_read ON public.audit_events FOR SELECT TO audit_v2_onboard_executor
 USING(org_id=public.app_org_id());
CREATE POLICY bootstrap_legacy_insert ON public.audit_events FOR INSERT TO audit_v2_onboard_executor
 WITH CHECK(org_id=public.app_org_id() AND actor_id=NULLIF(current_setting('app.user_id',true),'')::uuid);
CREATE POLICY bootstrap_epoch_read ON audit_v2.epochs FOR SELECT TO audit_v2_onboard_executor
 USING(org_id=public.app_org_id());
CREATE POLICY bootstrap_head_read ON audit_v2.heads FOR SELECT TO audit_v2_onboard_executor
 USING(org_id=public.app_org_id());

GRANT EXECUTE ON FUNCTION audit_v2.provision_epoch(uuid,bytea,text,bigint,bigint,bigint,text,bytea),
 audit_v2.append_event(uuid,uuid,uuid,uuid,text,text,inet,text,bytea) TO audit_v2_onboard_executor;

CREATE FUNCTION audit_v2.bootstrap_identity(p_name text,p_email text,p_role text,p_token_hash text,
 p_google_sub text,p_avatar text,p_display text,p_record_legacy boolean)
RETURNS TABLE(org_id uuid,user_id uuid,role text)
LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $body$
DECLARE new_org uuid:=gen_random_uuid(); new_user uuid:=gen_random_uuid(); mode smallint;
 old_org text:=current_setting('app.org_id',true); old_user text:=current_setting('app.user_id',true);
 approved_cutover bytea; legacy_hash text;
BEGIN
 IF current_setting('transaction_isolation')<>'read committed' THEN
   RAISE EXCEPTION 'identity bootstrap requires READ COMMITTED'; END IF;
 mode:=audit_v2.locked_version();
 IF p_name IS NULL OR p_name='' OR octet_length(p_name)>4096 OR p_email IS NULL OR p_email=''
   OR octet_length(p_email)>1024 OR p_role IS NULL OR p_role NOT IN ('owner','admin','bid_manager','contributor','viewer')
   OR p_record_legacy IS NULL THEN RAISE EXCEPTION 'invalid new identity'; END IF;
 IF p_google_sub IS NULL THEN
   IF p_token_hash IS NULL OR p_token_hash !~ '^[0-9a-f]{64}$' OR p_avatar IS NOT NULL OR p_display IS NOT NULL THEN
     RAISE EXCEPTION 'API identity requires only a credential hash'; END IF;
 ELSE
   IF p_google_sub='' OR octet_length(p_google_sub)>512 OR p_role<>'owner' OR p_token_hash IS NOT NULL
      OR octet_length(p_avatar)>4096 OR octet_length(p_display)>4096 THEN
     RAISE EXCEPTION 'invalid Google identity bootstrap'; END IF;
 END IF;
 PERFORM set_config('app.org_id',new_org::text,true);
 PERFORM set_config('app.user_id',new_user::text,true);
 -- Legacy audit has no organisation FK. Never silently label an existing random-ID
 -- collision/preseeded inventory as empty or delete it.
 IF EXISTS(SELECT 1 FROM public.audit_events a WHERE a.org_id=new_org) THEN
   RAISE EXCEPTION 'new identity has pre-existing legacy evidence'; END IF;
 INSERT INTO public.organisations(id,name) VALUES(new_org,p_name);
 INSERT INTO public.users(id,email,google_sub,avatar_url,display_name)
   VALUES(new_user,p_email,p_google_sub,p_avatar,p_display);
 INSERT INTO public.memberships(user_id,org_id,role) VALUES(new_user,new_org,p_role);
 IF p_google_sub IS NULL THEN
   INSERT INTO public.api_tokens(org_id,user_id,role,token_hash) VALUES(new_org,new_user,p_role,p_token_hash);
 ELSE
   INSERT INTO public.oauth_accounts(user_id,provider,provider_sub,email) VALUES(new_user,'google',p_google_sub,p_email);
 END IF;
 IF mode=2 THEN
   SELECT cutover_digest INTO STRICT approved_cutover FROM audit_v2.runtime_state WHERE singleton;
   IF approved_cutover IS NULL THEN RAISE EXCEPTION 'approved cutover reference missing'; END IF;
   -- Exact empty canonical JSON array: no legacy rows exist for this new identity.
   PERFORM audit_v2.provision_epoch(new_org,public.digest(convert_to('[]','UTF8'),'sha256'),
      'verified',0,NULL,NULL,'',approved_cutover);
   PERFORM audit_v2.append_event(new_org,gen_random_uuid(),gen_random_uuid(),new_user,
      'account.created',new_org::text,NULL,'tood.account-created.v1',convert_to('{}','UTF8'));
 ELSIF p_record_legacy THEN
   -- Fixed ASCII UUID/action/target envelope is byte-identical to existing Python
   -- _hash(new_org,new_user,'account.created',new_org,NULL); no general JSON encoder.
   legacy_hash:=encode(public.digest(convert_to(format('["%s","%s","account.created","%s",""]',
      new_org,new_user,new_org),'UTF8'),'sha256'),'hex');
   INSERT INTO public.audit_events(org_id,actor_id,action,target,prev_hash,hash)
      VALUES(new_org,new_user,'account.created',new_org::text,NULL,legacy_hash);
 END IF;
 PERFORM set_config('app.org_id',coalesce(old_org,''),true);
 PERFORM set_config('app.user_id',coalesce(old_user,''),true);
 RETURN QUERY SELECT new_org,new_user,p_role;
END $body$;

CREATE FUNCTION audit_v2.assert_login_ready(p_org uuid) RETURNS void
LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $body$
DECLARE old_org text:=current_setting('app.org_id',true);
BEGIN
 IF p_org IS NULL THEN RAISE EXCEPTION 'organisation is required'; END IF;
 IF audit_v2.locked_version()=2 THEN
   PERFORM set_config('app.org_id',p_org::text,true);
   IF NOT EXISTS(SELECT 1 FROM audit_v2.epochs e JOIN audit_v2.heads h
      ON h.org_id=e.org_id AND h.epoch_id=e.epoch_id WHERE e.org_id=p_org) THEN
     RAISE EXCEPTION 'active organisation audit epoch missing'; END IF;
   PERFORM set_config('app.org_id',coalesce(old_org,''),true);
 END IF;
END $body$;

GRANT CREATE ON SCHEMA audit_v2 TO audit_v2_onboard_executor;
ALTER FUNCTION audit_v2.bootstrap_identity(text,text,text,text,text,text,text,boolean) OWNER TO audit_v2_onboard_executor;
ALTER FUNCTION audit_v2.assert_login_ready(uuid) OWNER TO audit_v2_onboard_executor;
REVOKE CREATE ON SCHEMA audit_v2 FROM audit_v2_onboard_executor;
REVOKE ALL ON FUNCTION audit_v2.bootstrap_identity(text,text,text,text,text,text,text,boolean),
 audit_v2.assert_login_ready(uuid) FROM PUBLIC,app_user;
GRANT EXECUTE ON FUNCTION audit_v2.bootstrap_identity(text,text,text,text,text,text,text,boolean),
 audit_v2.assert_login_ready(uuid) TO auth_user;
-- No auth/app membership, generic provision grant, broad new RLS policy, existing
-- policy rewrite, live cutover, data cleanup or immutable-history mutation.
