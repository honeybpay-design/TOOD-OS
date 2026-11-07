-- F03v2 additive follow-up to the actual synthetic200writer head-lock timeout.
-- Preserve immutable0010/0011. No active ledger or old hash format is changed.
DO $preflight$
BEGIN
 IF current_setting('app.audit_v2_prepare',true) IS DISTINCT FROM 'confirmed-v2-prepare'
    OR current_setting('server_version_num')::integer / 10000 <> 16 THEN
   RAISE EXCEPTION 'guarded audit v2 preparation required'; END IF;
 IF audit_v2.current_version()<>1 THEN
   RAISE EXCEPTION 'append queue must be prepared before v2 activation'; END IF;
END $preflight$;
CREATE OR REPLACE FUNCTION audit_v2.append_event(p_org uuid,p_source uuid,p_operation uuid,p_actor uuid,
 p_action text,p_target text,p_ip inet,p_schema text,p_payload bytea) RETURNS audit_v2.events
LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $body$
DECLARE h audit_v2.heads; epoch audit_v2.epochs; prior audit_v2.events;
 ev audit_v2.events; pd bytea; rd bytea; latest_seq bigint; latest_hash bytea;
BEGIN
 IF current_setting('transaction_isolation')<>'read committed' THEN
   RAISE EXCEPTION 'audit append requires READ COMMITTED'; END IF;
 IF p_org IS NULL OR p_org IS DISTINCT FROM public.app_org_id() THEN
   RAISE EXCEPTION 'tenant context mismatch' USING ERRCODE='42501'; END IF;
 IF audit_v2.locked_version()<>2 THEN RAISE EXCEPTION 'audit v2 is not active'; END IF;
 IF p_source IS NULL OR p_operation IS NULL OR p_action IS NULL OR
    octet_length(p_action) NOT BETWEEN 1 AND 128 OR octet_length(p_target)>4096 OR
    p_schema IS NULL OR octet_length(p_schema) NOT BETWEEN 1 AND 128 OR
    p_payload IS NULL OR octet_length(p_payload)>65536 THEN RAISE EXCEPTION 'invalid audit request'; END IF;
 PERFORM audit_v2.ip_text(p_ip);
 pd:=public.digest(p_payload,'sha256');
 rd:=public.digest(audit_v2.frame(convert_to('TOOD-AUDIT-REQUEST','UTF8')||decode('00','hex')||convert_to('v2','UTF8'),
 ARRAY[p_org::text,p_source::text,p_operation::text,p_actor::text,p_action,p_target,p_schema,encode(pd,'hex')]),'sha256');
 -- Transaction-level queue avoids the demonstrated 200-backend hot-tuple lock storm.
 -- This is enforced inside the only granted append API. Head rowlock, RLS,
 -- consistency checks and atomic INSERT/head advance remain mandatory.
 -- 64-bit hash collisions can serialize unrelated tenants but cannot mix their rows.
 PERFORM pg_advisory_xact_lock(hashtextextended('tood:audit:v2:'||p_org::text,0));
 SELECT * INTO STRICT h FROM audit_v2.heads WHERE org_id=p_org FOR UPDATE;
 SELECT * INTO STRICT epoch FROM audit_v2.epochs WHERE org_id=p_org;
 SELECT tenant_sequence,hash INTO latest_seq,latest_hash FROM audit_v2.events
   WHERE org_id=p_org AND epoch_id=h.epoch_id ORDER BY tenant_sequence DESC LIMIT 1;
 IF h.epoch_id<>epoch.epoch_id OR
    (h.last_sequence=0 AND (latest_seq IS NOT NULL OR h.last_hash<>epoch.genesis_hash)) OR
    (h.last_sequence>0 AND (latest_seq IS DISTINCT FROM h.last_sequence OR latest_hash IS DISTINCT FROM h.last_hash))
 THEN RAISE EXCEPTION 'audit head inconsistent'; END IF;
 SELECT * INTO prior FROM audit_v2.events WHERE org_id=p_org AND source_event_id=p_source;
 IF FOUND THEN
   IF prior.request_digest<>rd OR prior.payload_bytes<>p_payload OR
      ROW(prior.operation_id,prior.actor_id,prior.action,prior.target,prior.payload_schema)
      IS DISTINCT FROM ROW(p_operation,p_actor,p_action,p_target,p_schema) THEN
     RAISE EXCEPTION 'audit source conflict' USING ERRCODE='23505'; END IF;
   RETURN prior;
 END IF;
 IF h.last_sequence=9223372036854775807 THEN RAISE EXCEPTION 'audit sequence exhausted'; END IF;
 ev.org_id:=p_org; ev.ledger_id:=epoch.ledger_id; ev.epoch_id:=h.epoch_id;
 ev.tenant_sequence:=h.last_sequence+1; ev.event_id:=gen_random_uuid(); ev.source_event_id:=p_source;
 ev.operation_id:=p_operation; ev.actor_id:=p_actor; ev.action:=p_action; ev.target:=p_target;
 ev.recorded_at:=clock_timestamp(); ev.source_ip:=p_ip; ev.payload_schema:=p_schema;
 ev.payload_bytes:=p_payload; ev.payload_digest:=pd; ev.request_digest:=rd; ev.prev_hash:=h.last_hash;
 ev.format_version:=2; ev.hash:=audit_v2.event_hash(ev);
 INSERT INTO audit_v2.events SELECT ev.*;
 UPDATE audit_v2.heads SET last_sequence=ev.tenant_sequence,last_hash=ev.hash WHERE org_id=p_org;
 RETURN ev;
END $body$;
DO $privileges$
BEGIN
 IF NOT has_function_privilege('app_user','audit_v2.append_event(uuid,uuid,uuid,uuid,text,text,inet,text,bytea)','EXECUTE') OR
    has_function_privilege('auth_user','audit_v2.append_event(uuid,uuid,uuid,uuid,text,text,inet,text,bytea)','EXECUTE') OR
    (SELECT proowner FROM pg_proc WHERE oid='audit_v2.append_event(uuid,uuid,uuid,uuid,text,text,inet,text,bytea)'::regprocedure)
      <>(SELECT oid FROM pg_roles WHERE rolname='audit_v2_append_executor') THEN
   RAISE EXCEPTION 'append executor privilege boundary changed'; END IF;
END $privileges$;
