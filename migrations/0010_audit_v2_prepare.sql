-- F03v2 additive preparation. LOCAL implementation authorized; no live activation.
-- Applied 0001-0009 are immutable. This file must run inside a verified target transaction.
-- The confirmation GUC expresses operator intent, not authentication; the guarded driver
-- must independently attest the target. The unsafe legacy migration CLI does not set it.
DO $preflight$
BEGIN
  IF current_setting('app.audit_v2_prepare', true) IS DISTINCT FROM 'confirmed-v2-prepare' THEN
    RAISE EXCEPTION 'audit v2 requires the approved guarded migration driver';
  END IF;
  IF current_setting('server_version_num')::integer / 10000 <> 16
     OR current_setting('server_encoding') <> 'UTF8' THEN
    RAISE EXCEPTION 'audit v2 requires the reviewed PostgreSQL 16 UTF8 target';
  END IF;
  IF current_user IN ('app_user','auth_user') THEN
    RAISE EXCEPTION 'runtime identities cannot prepare the ledger';
  END IF;
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname IN
    ('audit_v2_ddl_owner','audit_v2_append_executor','audit_v2_epoch_provisioner','audit_v2_onboard_executor'))
     OR to_regnamespace('audit_v2') IS NOT NULL THEN
    RAISE EXCEPTION 'untracked audit v2 objects/roles already exist; inspect rather than silently reuse';
  END IF;
  IF NOT EXISTS (
    SELECT 1 FROM pg_extension e JOIN pg_namespace n ON n.oid=e.extnamespace
    JOIN pg_depend d ON d.refobjid=e.oid AND d.deptype='e'
    WHERE e.extname='pgcrypto' AND n.nspname='public'
      AND d.objid=to_regprocedure('public.digest(bytea,text)')::oid
  ) THEN
    RAISE EXCEPTION 'trusted public pgcrypto digest extension dependency is required';
  END IF;
  IF has_schema_privilege('app_user','public','CREATE') OR has_schema_privilege('auth_user','public','CREATE') THEN
    RAISE EXCEPTION 'runtime CREATE on trusted public schema must be separately reviewed';
  END IF;
END
$preflight$;

CREATE ROLE audit_v2_ddl_owner NOLOGIN NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE NOINHERIT;
CREATE ROLE audit_v2_append_executor NOLOGIN NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE NOINHERIT;
CREATE ROLE audit_v2_epoch_provisioner NOLOGIN NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE NOINHERIT;
CREATE ROLE audit_v2_onboard_executor NOLOGIN NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE NOINHERIT;
CREATE SCHEMA audit_v2 AUTHORIZATION audit_v2_ddl_owner;
REVOKE ALL ON SCHEMA audit_v2 FROM PUBLIC;
GRANT USAGE ON SCHEMA audit_v2 TO app_user,auth_user,audit_v2_append_executor,
  audit_v2_epoch_provisioner,audit_v2_onboard_executor;

-- Global non-customer capability metadata; no tenant rows or credentials.
CREATE TABLE audit_v2.runtime_state (
  singleton boolean PRIMARY KEY DEFAULT true CHECK(singleton),
  version smallint NOT NULL DEFAULT 1 CHECK(version IN (1,2)),
  ledger_id uuid NOT NULL UNIQUE DEFAULT gen_random_uuid(),
  prepared_at timestamptz NOT NULL DEFAULT clock_timestamp(),
  activated_at timestamptz
);
INSERT INTO audit_v2.runtime_state(singleton) VALUES(true);
ALTER TABLE audit_v2.runtime_state OWNER TO audit_v2_ddl_owner;
REVOKE ALL ON audit_v2.runtime_state FROM PUBLIC,app_user,auth_user;

CREATE TABLE audit_v2.epochs (
  org_id uuid PRIMARY KEY REFERENCES public.organisations(id) ON DELETE RESTRICT,
  ledger_id uuid NOT NULL,
  epoch_id uuid NOT NULL UNIQUE,
  format_version smallint NOT NULL DEFAULT 2 CHECK(format_version=2),
  manifest_version smallint NOT NULL DEFAULT 1 CHECK(manifest_version=1),
  manifest_digest bytea NOT NULL CHECK(octet_length(manifest_digest)=32),
  legacy_status text NOT NULL CHECK(legacy_status IN ('verified','broken','unverified')),
  legacy_count bigint NOT NULL CHECK(legacy_count>=0),
  legacy_max_id bigint,
  legacy_first_bad_id bigint,
  incident_ref text NOT NULL CHECK(octet_length(incident_ref)<=512),
  cutover_digest bytea NOT NULL CHECK(octet_length(cutover_digest)=32),
  initialized_at timestamptz NOT NULL CHECK(isfinite(initialized_at)),
  genesis_hash bytea NOT NULL CHECK(octet_length(genesis_hash)=32),
  UNIQUE(org_id,epoch_id), UNIQUE(org_id,epoch_id,ledger_id),
  CHECK((legacy_count=0)=(legacy_max_id IS NULL)),
  CHECK(legacy_count>0 OR legacy_first_bad_id IS NULL),
  CHECK(legacy_first_bad_id IS NULL OR legacy_first_bad_id<=legacy_max_id),
  CHECK(legacy_status<>'broken' OR legacy_first_bad_id IS NOT NULL),
  CHECK(legacy_status<>'verified' OR legacy_first_bad_id IS NULL),
  CHECK(legacy_status='verified' OR octet_length(incident_ref)>0)
);
CREATE TABLE audit_v2.heads (
  org_id uuid PRIMARY KEY,
  epoch_id uuid NOT NULL,
  last_sequence bigint NOT NULL DEFAULT 0 CHECK(last_sequence>=0),
  last_hash bytea NOT NULL CHECK(octet_length(last_hash)=32),
  FOREIGN KEY(org_id,epoch_id) REFERENCES audit_v2.epochs(org_id,epoch_id) ON DELETE RESTRICT
);
CREATE TABLE audit_v2.events (
  org_id uuid NOT NULL,
  ledger_id uuid NOT NULL,
  epoch_id uuid NOT NULL,
  tenant_sequence bigint NOT NULL CHECK(tenant_sequence>0),
  event_id uuid NOT NULL UNIQUE,
  source_event_id uuid NOT NULL,
  operation_id uuid NOT NULL,
  actor_id uuid,
  action text NOT NULL CHECK(octet_length(action) BETWEEN 1 AND 128),
  target text CHECK(octet_length(target)<=4096),
  recorded_at timestamptz NOT NULL CHECK(isfinite(recorded_at)),
  source_ip inet CHECK(masklen(source_ip)=CASE family(source_ip) WHEN 4 THEN 32 ELSE 128 END),
  payload_schema text NOT NULL CHECK(octet_length(payload_schema) BETWEEN 1 AND 128),
  payload_bytes bytea NOT NULL CHECK(octet_length(payload_bytes)<=65536),
  payload_digest bytea NOT NULL CHECK(octet_length(payload_digest)=32),
  request_digest bytea NOT NULL CHECK(octet_length(request_digest)=32),
  prev_hash bytea NOT NULL CHECK(octet_length(prev_hash)=32),
  hash bytea NOT NULL CHECK(octet_length(hash)=32),
  format_version smallint NOT NULL DEFAULT 2 CHECK(format_version=2),
  PRIMARY KEY(org_id,epoch_id,tenant_sequence),
  UNIQUE(org_id,source_event_id), UNIQUE(org_id,epoch_id,hash),
  FOREIGN KEY(org_id,epoch_id,ledger_id) REFERENCES audit_v2.epochs(org_id,epoch_id,ledger_id) ON DELETE RESTRICT,
  CHECK(payload_digest=public.digest(payload_bytes,'sha256'))
);
CREATE TABLE audit_v2.operations (
  org_id uuid NOT NULL,
  operation_id uuid NOT NULL,
  actor_id uuid NOT NULL,
  action text NOT NULL CHECK(octet_length(action) BETWEEN 1 AND 128),
  request_schema text NOT NULL CHECK(octet_length(request_schema) BETWEEN 1 AND 128),
  request_bytes bytea NOT NULL CHECK(octet_length(request_bytes)<=65536),
  request_digest bytea NOT NULL CHECK(octet_length(request_digest)=32),
  status text NOT NULL DEFAULT 'pending' CHECK(status IN ('pending','complete')),
  result_reference jsonb,
  created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
  completed_at timestamptz,
  PRIMARY KEY(org_id,operation_id),
  FOREIGN KEY(org_id) REFERENCES audit_v2.epochs(org_id) ON DELETE RESTRICT,
  CHECK(request_digest=public.digest(request_bytes,'sha256')),
  CHECK((status='complete')=(completed_at IS NOT NULL)),
  CHECK(result_reference IS NULL OR jsonb_typeof(result_reference)='object')
);

ALTER TABLE audit_v2.epochs OWNER TO audit_v2_ddl_owner;
ALTER TABLE audit_v2.heads OWNER TO audit_v2_ddl_owner;
ALTER TABLE audit_v2.events OWNER TO audit_v2_ddl_owner;
ALTER TABLE audit_v2.operations OWNER TO audit_v2_ddl_owner;
ALTER TABLE audit_v2.epochs ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_v2.epochs FORCE ROW LEVEL SECURITY;
ALTER TABLE audit_v2.heads ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_v2.heads FORCE ROW LEVEL SECURITY;
ALTER TABLE audit_v2.events ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_v2.events FORCE ROW LEVEL SECURITY;
ALTER TABLE audit_v2.operations ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_v2.operations FORCE ROW LEVEL SECURITY;
REVOKE ALL ON ALL TABLES IN SCHEMA audit_v2 FROM PUBLIC,app_user,auth_user;

CREATE POLICY epoch_read ON audit_v2.epochs FOR SELECT
  TO app_user,audit_v2_append_executor,audit_v2_epoch_provisioner
  USING(org_id=public.app_org_id());
CREATE POLICY epoch_insert ON audit_v2.epochs FOR INSERT TO audit_v2_epoch_provisioner
  WITH CHECK(org_id=public.app_org_id());
CREATE POLICY head_read ON audit_v2.heads FOR SELECT
  TO app_user,audit_v2_append_executor,audit_v2_epoch_provisioner
  USING(org_id=public.app_org_id());
CREATE POLICY head_insert ON audit_v2.heads FOR INSERT TO audit_v2_epoch_provisioner
  WITH CHECK(org_id=public.app_org_id());
CREATE POLICY head_advance ON audit_v2.heads FOR UPDATE TO audit_v2_append_executor
  USING(org_id=public.app_org_id()) WITH CHECK(org_id=public.app_org_id());
CREATE POLICY event_read ON audit_v2.events FOR SELECT TO app_user,audit_v2_append_executor
  USING(org_id=public.app_org_id());
CREATE POLICY event_append ON audit_v2.events FOR INSERT TO audit_v2_append_executor
  WITH CHECK(org_id=public.app_org_id());
CREATE POLICY operation_read ON audit_v2.operations FOR SELECT TO app_user,audit_v2_append_executor
  USING(org_id=public.app_org_id());
CREATE POLICY operation_insert ON audit_v2.operations FOR INSERT TO audit_v2_append_executor
  WITH CHECK(org_id=public.app_org_id());
CREATE POLICY operation_complete ON audit_v2.operations FOR UPDATE TO audit_v2_append_executor
  USING(org_id=public.app_org_id()) WITH CHECK(org_id=public.app_org_id());

GRANT SELECT ON audit_v2.epochs,audit_v2.heads,audit_v2.events,audit_v2.operations TO app_user;
GRANT SELECT ON audit_v2.epochs,audit_v2.heads,audit_v2.events,audit_v2.operations TO audit_v2_append_executor;
GRANT INSERT ON audit_v2.events,audit_v2.operations TO audit_v2_append_executor;
GRANT UPDATE(last_sequence,last_hash) ON audit_v2.heads TO audit_v2_append_executor;
GRANT UPDATE(status,result_reference,completed_at) ON audit_v2.operations TO audit_v2_append_executor;
GRANT SELECT,INSERT ON audit_v2.epochs,audit_v2.heads TO audit_v2_epoch_provisioner;
GRANT EXECUTE ON FUNCTION public.app_org_id() TO audit_v2_append_executor,audit_v2_epoch_provisioner;

CREATE FUNCTION audit_v2.block_mutation() RETURNS trigger LANGUAGE plpgsql
SET search_path=pg_catalog,pg_temp AS $body$
BEGIN RAISE EXCEPTION 'immutable audit v2 object'; END
$body$;
ALTER FUNCTION audit_v2.block_mutation() OWNER TO audit_v2_ddl_owner;
CREATE TRIGGER epochs_immutable BEFORE UPDATE OR DELETE ON audit_v2.epochs
  FOR EACH ROW EXECUTE FUNCTION audit_v2.block_mutation();
CREATE TRIGGER events_immutable BEFORE UPDATE OR DELETE ON audit_v2.events
  FOR EACH ROW EXECUTE FUNCTION audit_v2.block_mutation();

CREATE FUNCTION audit_v2.frame(p_domain bytea,p_fields text[]) RETURNS bytea
LANGUAGE plpgsql IMMUTABLE SET search_path=pg_catalog,pg_temp AS $body$
DECLARE item text; encoded bytea; result bytea:=p_domain;
BEGIN
  IF p_domain IS NULL OR p_fields IS NULL OR p_domain NOT IN (
    convert_to('TOOD-AUDIT-EVENT','UTF8')||decode('003200','hex'),
    convert_to('TOOD-AUDIT-REQUEST','UTF8')||decode('00','hex')||convert_to('v2','UTF8'),
    convert_to('TOOD-AUDIT-GENESIS','UTF8')||decode('00','hex')||convert_to('v2','UTF8'),
    convert_to('TOOD-AUDIT-CHECKPOINT','UTF8')||decode('00','hex')||convert_to('v2','UTF8'))
    THEN RAISE EXCEPTION 'invalid audit frame'; END IF;
  FOREACH item IN ARRAY p_fields LOOP
    IF item IS NULL THEN result:=result||decode('00','hex');
    ELSE
      encoded:=convert_to(item,'UTF8');
      IF octet_length(encoded)>65536 THEN RAISE EXCEPTION 'audit field exceeds limit'; END IF;
      result:=result||decode('01','hex')||int8send(octet_length(encoded)::bigint)||encoded;
    END IF;
  END LOOP;
  RETURN result;
END $body$;
ALTER FUNCTION audit_v2.frame(bytea,text[]) OWNER TO audit_v2_ddl_owner;

CREATE FUNCTION audit_v2.utc_text(p_time timestamptz) RETURNS text
LANGUAGE plpgsql IMMUTABLE SET search_path=pg_catalog,pg_temp AS $body$
BEGIN
  IF p_time IS NULL OR NOT isfinite(p_time) OR extract(year FROM p_time AT TIME ZONE 'UTC') NOT BETWEEN 1 AND 9999 THEN
    RAISE EXCEPTION 'unsupported audit timestamp';
  END IF;
  RETURN to_char(p_time AT TIME ZONE 'UTC','YYYY-MM-DD"T"HH24:MI:SS.US"Z"');
END $body$;
ALTER FUNCTION audit_v2.utc_text(timestamptz) OWNER TO audit_v2_ddl_owner;

CREATE FUNCTION audit_v2.ip_text(p_ip inet) RETURNS text
LANGUAGE plpgsql IMMUTABLE SET search_path=pg_catalog,pg_temp AS $body$
BEGIN
  IF p_ip IS NULL THEN RETURN NULL; END IF;
  IF masklen(p_ip)<>(CASE family(p_ip) WHEN 4 THEN 32 ELSE 128 END) THEN RAISE EXCEPTION 'audit IP must be host'; END IF;
  RETURN host(p_ip);
END $body$;
ALTER FUNCTION audit_v2.ip_text(inet) OWNER TO audit_v2_ddl_owner;

CREATE FUNCTION audit_v2.current_version() RETURNS smallint
LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp
AS $body$ SELECT version FROM audit_v2.runtime_state WHERE singleton $body$;
ALTER FUNCTION audit_v2.current_version() OWNER TO audit_v2_ddl_owner;
CREATE FUNCTION audit_v2.locked_version() RETURNS smallint
LANGUAGE sql VOLATILE SECURITY DEFINER SET search_path=pg_catalog,pg_temp
AS $body$ SELECT version FROM audit_v2.runtime_state WHERE singleton FOR SHARE $body$;
ALTER FUNCTION audit_v2.locked_version() OWNER TO audit_v2_ddl_owner;

REVOKE ALL ON ALL FUNCTIONS IN SCHEMA audit_v2 FROM PUBLIC,app_user,auth_user;
GRANT EXECUTE ON FUNCTION audit_v2.current_version(),audit_v2.locked_version() TO app_user,auth_user,
  audit_v2_append_executor,audit_v2_epoch_provisioner,audit_v2_onboard_executor;
GRANT EXECUTE ON FUNCTION audit_v2.frame(bytea,text[]),audit_v2.utc_text(timestamptz),audit_v2.ip_text(inet)
  TO audit_v2_append_executor,audit_v2_epoch_provisioner,audit_v2_onboard_executor;
GRANT EXECUTE ON FUNCTION public.digest(bytea,text) TO audit_v2_append_executor,audit_v2_epoch_provisioner;
-- No new role membership, tenant data, epoch or active v2 write path is created here.
-- Existing public grants/triggers, including legacy INSERT, remain unchanged until approved cutover.


-- Pure encoders take typed rows; no JSONB rendering participates in event hashes.
CREATE FUNCTION audit_v2.event_hash(e audit_v2.events) RETURNS bytea
LANGUAGE sql IMMUTABLE SET search_path=pg_catalog,pg_temp AS $body$
SELECT public.digest(audit_v2.frame(convert_to('TOOD-AUDIT-EVENT','UTF8')||decode('003200','hex'),
 ARRAY[e.ledger_id::text,e.org_id::text,e.epoch_id::text,e.tenant_sequence::text,
 e.event_id::text,e.source_event_id::text,e.operation_id::text,e.actor_id::text,e.action,e.target,
 audit_v2.utc_text(e.recorded_at),audit_v2.ip_text(e.source_ip),e.payload_schema,
 encode(public.digest(e.payload_bytes,'sha256'),'hex'),encode(e.prev_hash,'hex')]),'sha256')
$body$;
ALTER FUNCTION audit_v2.event_hash(audit_v2.events) OWNER TO audit_v2_ddl_owner;
REVOKE ALL ON FUNCTION audit_v2.event_hash(audit_v2.events) FROM PUBLIC,app_user,auth_user;
GRANT EXECUTE ON FUNCTION audit_v2.event_hash(audit_v2.events) TO audit_v2_append_executor;

-- Operator/provisioner-only entry, not a generic runtime capability. Legacy status is
-- a retained operator assertion; the guarded cutover must independently verify it.
CREATE FUNCTION audit_v2.provision_epoch(p_org uuid,p_manifest bytea,p_status text,p_count bigint,
 p_max bigint,p_bad bigint,p_incident text,p_cutover bytea) RETURNS uuid
LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $body$
DECLARE ep uuid:=gen_random_uuid(); lid uuid; t timestamptz:=clock_timestamp(); g bytea;
BEGIN
 IF p_org IS NULL OR p_org IS DISTINCT FROM public.app_org_id() THEN
   RAISE EXCEPTION 'tenant context mismatch' USING ERRCODE='42501'; END IF;
 PERFORM audit_v2.locked_version();
 SELECT ledger_id INTO STRICT lid FROM audit_v2.runtime_state WHERE singleton;
 g:=public.digest(audit_v2.frame(convert_to('TOOD-AUDIT-GENESIS','UTF8')||decode('00','hex')||convert_to('v2','UTF8'),
 ARRAY[lid::text,p_org::text,ep::text,'1','v1-org-actor-action-target-prev',p_status,
 encode(p_manifest,'hex'),p_count::text,p_max::text,p_bad::text,p_incident,
 encode(p_cutover,'hex'),audit_v2.utc_text(t)]),'sha256');
 INSERT INTO audit_v2.epochs(org_id,ledger_id,epoch_id,manifest_digest,legacy_status,legacy_count,
 legacy_max_id,legacy_first_bad_id,incident_ref,cutover_digest,initialized_at,genesis_hash)
 VALUES(p_org,lid,ep,p_manifest,p_status,p_count,p_max,p_bad,p_incident,p_cutover,t,g);
 INSERT INTO audit_v2.heads(org_id,epoch_id,last_sequence,last_hash) VALUES(p_org,ep,0,g);
 RETURN ep;
END $body$;
GRANT SELECT ON audit_v2.runtime_state TO audit_v2_epoch_provisioner;
GRANT CREATE ON SCHEMA audit_v2 TO audit_v2_epoch_provisioner;
ALTER FUNCTION audit_v2.provision_epoch(uuid,bytea,text,bigint,bigint,bigint,text,bytea)
 OWNER TO audit_v2_epoch_provisioner;
REVOKE CREATE ON SCHEMA audit_v2 FROM audit_v2_epoch_provisioner;
REVOKE ALL ON FUNCTION audit_v2.provision_epoch(uuid,bytea,text,bigint,bigint,bigint,text,bytea)
 FROM PUBLIC,app_user,auth_user;
-- No runtime provision grant; narrow onboarding integration follows in a new migration.

CREATE FUNCTION audit_v2.append_event(p_org uuid,p_source uuid,p_operation uuid,p_actor uuid,
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
GRANT CREATE ON SCHEMA audit_v2 TO audit_v2_append_executor;
ALTER FUNCTION audit_v2.append_event(uuid,uuid,uuid,uuid,text,text,inet,text,bytea) OWNER TO audit_v2_append_executor;
REVOKE CREATE ON SCHEMA audit_v2 FROM audit_v2_append_executor;
REVOKE ALL ON FUNCTION audit_v2.append_event(uuid,uuid,uuid,uuid,text,text,inet,text,bytea) FROM PUBLIC,auth_user;
GRANT EXECUTE ON FUNCTION audit_v2.append_event(uuid,uuid,uuid,uuid,text,text,inet,text,bytea) TO app_user;
