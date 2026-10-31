-- F03v2 local preparation follow-up;0010 is immutable after its first fixture apply.
-- PostgreSQL renders IPv4-compatible IPv6 using dotted decimal; wire-v2 requires
-- Python/RFC5952 compressed hexadecimal except the explicitly mapped-v4 case.
DO $preflight$
BEGIN
 IF current_setting('app.audit_v2_prepare',true) IS DISTINCT FROM 'confirmed-v2-prepare'
    OR current_setting('server_version_num')::integer / 10000 <> 16 THEN
   RAISE EXCEPTION 'guarded audit v2 preparation required'; END IF;
 IF audit_v2.current_version()<>1 THEN
   RAISE EXCEPTION 'IP canonicalization must be prepared before v2 activation'; END IF;
END $preflight$;
CREATE OR REPLACE FUNCTION audit_v2.ip_text(p_ip inet) RETURNS text
LANGUAGE plpgsql IMMUTABLE SET search_path=pg_catalog,pg_temp AS $body$
DECLARE value text; octets text[]; high_word integer; low_word integer;
BEGIN
 IF p_ip IS NULL THEN RETURN NULL; END IF;
 IF masklen(p_ip)<>(CASE family(p_ip) WHEN 4 THEN 32 ELSE 128 END) THEN
   RAISE EXCEPTION 'audit IP must be host'; END IF;
 value:=host(p_ip);
 IF family(p_ip)=6 AND value ~ '^::[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$' THEN
   octets:=string_to_array(substr(value,3),'.');
   high_word:=octets[1]::integer*256+octets[2]::integer;
   low_word:=octets[3]::integer*256+octets[4]::integer;
   IF high_word=0 AND low_word=0 THEN RETURN '::'; END IF;
   IF high_word=0 THEN RETURN '::'||to_hex(low_word); END IF;
   RETURN '::'||to_hex(high_word)||':'||to_hex(low_word);
 END IF;
 RETURN value;
END $body$;
-- CREATE OR REPLACE preserves owner/ACL; assert that narrow boundary remains.
DO $privileges$
BEGIN
 IF has_function_privilege('app_user','audit_v2.ip_text(inet)','EXECUTE') OR
    has_function_privilege('auth_user','audit_v2.ip_text(inet)','EXECUTE') OR
    (SELECT proowner FROM pg_proc WHERE oid='audit_v2.ip_text(inet)'::regprocedure)
      <>(SELECT oid FROM pg_roles WHERE rolname='audit_v2_ddl_owner') THEN
    RAISE EXCEPTION 'audit helper privilege boundary changed'; END IF;
END $privileges$;
