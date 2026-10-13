# Threat model (blueprint section 22)

| Threat | Mitigation | Verified by |
|---|---|---|
| Cross-tenant access | Forced RLS, `tenant_connection()`, object prefixes | D03, D04, D05 |
| History tampering | Append-only tables, triggers, hash chain, daily anchoring | D06, D07 |
| Malicious files | Quarantine, magic-byte check, malware scan, sandbox | to be added with the ingestion task |
| Prompt injection | File text is data, no side-effect tools | to be added with the AI Gateway task |
| Data residency breach | Residency guard | D08 |
| Credential theft | MFA, secret manager, no production access for agents | AGENTS.md, CI secret scan (D11) |
