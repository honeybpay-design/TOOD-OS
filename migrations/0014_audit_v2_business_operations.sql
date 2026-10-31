-- F03 approved local business-operation boundary. Applied0001-0013 are immutable.
DO $guard$
BEGIN
 IF current_setting('app.audit_v2_prepare',true) IS DISTINCT FROM 'confirmed-v2-prepare'
   OR current_setting('server_version_num')::integer/10000<>16 OR audit_v2.current_version()<>1 THEN
   RAISE EXCEPTION 'guarded inactive audit v2 preparation required'; END IF;
END $guard$;
-- Preserve existing 40000-character Unicode edit/evidence DTOs without lifting the
-- independent 64KiB event limit. Largest current effective JSON request fits256KiB.
ALTER TABLE audit_v2.operations DROP CONSTRAINT operations_request_bytes_check;
ALTER TABLE audit_v2.operations ADD CONSTRAINT operations_request_bytes_check
 CHECK(octet_length(request_bytes)<=262144);

CREATE FUNCTION audit_v2.begin_operation(p_org uuid,p_operation uuid,p_actor uuid,p_action text,
 p_schema text,p_request bytea) RETURNS audit_v2.operations
LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $body$
DECLARE o audit_v2.operations; inserted bigint;
BEGIN
 IF current_setting('transaction_isolation')<>'read committed' THEN RAISE EXCEPTION 'operation requires READ COMMITTED'; END IF;
 IF p_org IS NULL OR p_org IS DISTINCT FROM public.app_org_id() THEN
   RAISE EXCEPTION 'tenant context mismatch' USING ERRCODE='42501'; END IF;
 IF audit_v2.locked_version()<>2 THEN RAISE EXCEPTION 'business operation v2 is not active' USING ERRCODE='55000'; END IF;
 IF p_operation IS NULL OR p_actor IS NULL OR p_action IS NULL OR octet_length(p_action) NOT BETWEEN 1 AND 128
   OR p_schema IS NULL OR octet_length(p_schema) NOT BETWEEN 1 AND 128 OR p_request IS NULL
   OR octet_length(p_request)>262144 THEN RAISE EXCEPTION 'invalid business operation request'; END IF;
 IF NOT EXISTS(SELECT 1 FROM audit_v2.epochs WHERE org_id=p_org) THEN
   RAISE EXCEPTION 'organisation audit epoch missing' USING ERRCODE='55000'; END IF;
 INSERT INTO audit_v2.operations(org_id,operation_id,actor_id,action,request_schema,request_bytes,request_digest)
 VALUES(p_org,p_operation,p_actor,p_action,p_schema,p_request,public.digest(p_request,'sha256'))
 ON CONFLICT(org_id,operation_id) DO NOTHING;
 GET DIAGNOSTICS inserted=ROW_COUNT;
 -- A separate volatile statement sees the winner after an uncommitted conflict resolves.
 SELECT * INTO STRICT o FROM audit_v2.operations WHERE org_id=p_org AND operation_id=p_operation FOR UPDATE;
 IF ROW(o.actor_id,o.action,o.request_schema,o.request_bytes)
   IS DISTINCT FROM ROW(p_actor,p_action,p_schema,p_request) THEN
   RAISE EXCEPTION 'business idempotency request conflict' USING ERRCODE='23505'; END IF;
 IF inserted=0 AND o.status<>'complete' THEN
   RAISE EXCEPTION 'operation is already open in this transaction' USING ERRCODE='55000'; END IF;
 RETURN o;
END $body$;

CREATE FUNCTION audit_v2.complete_operation(p_org uuid,p_operation uuid,p_actor uuid,p_result jsonb)
RETURNS audit_v2.operations LANGUAGE plpgsql VOLATILE SECURITY DEFINER
SET search_path=pg_catalog,pg_temp AS $body$
DECLARE o audit_v2.operations; kind text; resource uuid; target uuid; item record; key text;
 digest text; pointer text; matches bigint;
BEGIN
 IF current_setting('transaction_isolation')<>'read committed' THEN RAISE EXCEPTION 'operation requires READ COMMITTED'; END IF;
 IF p_org IS NULL OR p_org IS DISTINCT FROM public.app_org_id() THEN
   RAISE EXCEPTION 'tenant context mismatch' USING ERRCODE='42501'; END IF;
 IF audit_v2.locked_version()<>2 THEN RAISE EXCEPTION 'business operation v2 is not active' USING ERRCODE='55000'; END IF;
 SELECT * INTO STRICT o FROM audit_v2.operations WHERE org_id=p_org AND operation_id=p_operation FOR UPDATE;
 IF p_actor IS NULL OR o.actor_id<>p_actor THEN
   RAISE EXCEPTION 'business operation actor conflict' USING ERRCODE='23505'; END IF;
 IF p_result IS NULL OR jsonb_typeof(p_result)<>'object' OR octet_length(p_result::text)>8192 THEN
   RAISE EXCEPTION 'invalid operation result reference'; END IF;
 FOR key IN SELECT jsonb_object_keys(p_result) LOOP
  IF key NOT IN ('kind','id','target_id','counts','format','sha256','storage_key','evidence_ids') THEN
    RAISE EXCEPTION 'unapproved operation result field'; END IF;
 END LOOP;
 kind:=p_result->>'kind';resource:=(p_result->>'id')::uuid;
 IF kind IS NULL OR kind NOT IN ('tender','document','evidence','draft','claim','export') OR resource IS NULL THEN
   RAISE EXCEPTION 'operation result requires a typed resource reference'; END IF;
 IF p_result->>'id'<>resource::text THEN RAISE EXCEPTION 'noncanonical result UUID'; END IF;
 target:=coalesce((p_result->>'target_id')::uuid,resource);
 IF kind='document' AND (NOT (p_result ? 'format' AND p_result ? 'counts')
    OR jsonb_typeof(p_result->'counts')<>'object' OR (SELECT count(*) FROM jsonb_object_keys(p_result->'counts'))<>6) THEN
    RAISE EXCEPTION 'document result requires all parser counters'; END IF;
 IF kind='draft' AND o.action='draft.generated' AND NOT (p_result ? 'evidence_ids') THEN
    RAISE EXCEPTION 'generation result requires evidence references'; END IF;
 IF p_result ? 'counts' THEN
  IF kind<>'document' OR jsonb_typeof(p_result->'counts')<>'object' THEN RAISE EXCEPTION 'invalid result counters'; END IF;
  FOR item IN SELECT * FROM jsonb_each(p_result->'counts') LOOP
   IF item.key NOT IN ('blocks','requirements','questions','needs_review','duplicates_merged','rejected_unverifiable')
     OR jsonb_typeof(item.value)<>'number' OR item.value::text !~ '^[0-9]{1,9}$' THEN
     RAISE EXCEPTION 'invalid result counter'; END IF;
  END LOOP;
 END IF;
 IF p_result ? 'format' AND (kind<>'document' OR jsonb_typeof(p_result->'format')<>'string'
   OR octet_length(p_result->>'format') NOT BETWEEN 1 AND 128) THEN RAISE EXCEPTION 'invalid result format'; END IF;
 IF p_result ? 'evidence_ids' THEN
  IF kind<>'draft' OR o.action<>'draft.generated' OR jsonb_typeof(p_result->'evidence_ids')<>'array'
    OR jsonb_array_length(p_result->'evidence_ids')>3 THEN RAISE EXCEPTION 'invalid evidence references'; END IF;
  FOR key IN SELECT jsonb_array_elements_text(p_result->'evidence_ids') LOOP
   IF key IS NULL OR key<>(key::uuid)::text THEN RAISE EXCEPTION 'invalid evidence UUID'; END IF;
  END LOOP;
 END IF;
 IF kind='export' THEN
  digest:=p_result->>'sha256';pointer:=p_result->>'storage_key';
  IF digest IS NULL OR digest !~ '^[0-9a-f]{64}$' OR pointer IS NULL OR octet_length(pointer)>1024 THEN
   RAISE EXCEPTION 'export result requires immutable storage reference and digest'; END IF;
  IF pointer<>p_org::text||'/'||resource::text AND
     pointer !~ ('^gcs:v1:[a-z0-9][a-z0-9._-]{1,220}[a-z0-9]:'||p_org::text||':'||resource::text||':[1-9][0-9]{0,19}:'||digest||'$') THEN
   RAISE EXCEPTION 'export pointer must match its tenant, artifact and digest'; END IF;
 ELSIF p_result ? 'sha256' OR p_result ? 'storage_key' THEN RAISE EXCEPTION 'storage fields require export reference';
 END IF;
 IF o.status='complete' THEN
  IF o.result_reference IS DISTINCT FROM p_result THEN
   RAISE EXCEPTION 'committed operation result conflict' USING ERRCODE='23505'; END IF;
  RETURN o;
 END IF;
 SELECT count(*) INTO matches FROM audit_v2.events e WHERE e.org_id=p_org AND e.operation_id=p_operation
   AND e.actor_id=p_actor AND e.action=o.action AND e.target=target::text
   AND convert_from(e.payload_bytes,'UTF8')::jsonb->>'operation_request_digest'=encode(o.request_digest,'hex')
   AND convert_from(e.payload_bytes,'UTF8')::jsonb->>'operation_request_schema'=o.request_schema;
 IF matches<>1 THEN RAISE EXCEPTION 'operation requires exactly one matching committed-transaction audit event'; END IF;
 UPDATE audit_v2.operations SET status='complete',result_reference=p_result,completed_at=clock_timestamp()
 WHERE org_id=p_org AND operation_id=p_operation RETURNING * INTO o;
 RETURN o;
END $body$;

CREATE FUNCTION audit_v2.require_operation_completion() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $body$
DECLARE final_status text;
BEGIN
 IF NEW.org_id IS DISTINCT FROM public.app_org_id() THEN
   RAISE EXCEPTION 'operation commit tenant context mismatch'; END IF;
 SELECT status INTO final_status FROM audit_v2.operations
   WHERE org_id=NEW.org_id AND operation_id=NEW.operation_id;
 IF final_status IS DISTINCT FROM 'complete' THEN
   RAISE EXCEPTION 'pending business operation cannot commit'; END IF;
 RETURN NULL;
END $body$;
GRANT CREATE ON SCHEMA audit_v2 TO audit_v2_append_executor;
ALTER FUNCTION audit_v2.begin_operation(uuid,uuid,uuid,text,text,bytea) OWNER TO audit_v2_append_executor;
ALTER FUNCTION audit_v2.complete_operation(uuid,uuid,uuid,jsonb) OWNER TO audit_v2_append_executor;
ALTER FUNCTION audit_v2.require_operation_completion() OWNER TO audit_v2_append_executor;
REVOKE CREATE ON SCHEMA audit_v2 FROM audit_v2_append_executor;
REVOKE ALL ON FUNCTION audit_v2.begin_operation(uuid,uuid,uuid,text,text,bytea),
 audit_v2.complete_operation(uuid,uuid,uuid,jsonb),audit_v2.require_operation_completion() FROM PUBLIC,auth_user,app_user;
GRANT EXECUTE ON FUNCTION audit_v2.begin_operation(uuid,uuid,uuid,text,text,bytea),
 audit_v2.complete_operation(uuid,uuid,uuid,jsonb) TO app_user;
CREATE CONSTRAINT TRIGGER operation_completion_required AFTER INSERT OR UPDATE ON audit_v2.operations
 DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION audit_v2.require_operation_completion();
-- No table ownership, role membership, direct runtime writes, credential result or legacy-history change.
