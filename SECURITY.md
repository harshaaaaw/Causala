# Security Policy

## Supported versions

| Version | Supported |
|---|---|
| 0.3.x (master) | Yes - active development |

As a pre 1.0 project we support only the latest master. Pin to a commit hash for production use until we tag 1.0.

## Reporting a vulnerability

Do not open a public GitHub issue for security vulnerabilities.

Email the maintainer privately: open an issue with title `[SECURITY] private disclosure` and we will provide a private channel, or use GitHub private vulnerability reporting:

GitHub repo -> Security -> Report a vulnerability

We will acknowledge within 48 hours and provide a fix timeline. We follow coordinated disclosure: you report privately, we fix and release, then we publish an advisory and credit you if you wish.

## Trust boundaries

- **Tenant isolation**: every claim, simulate, and audit is scoped by `tenant_id`. A tenant cannot read another tenant's claims or audits. Idempotency keys include tenant.
- **Untrusted input**: warehouse CSVs are treated as untrusted. Confidences are clamped to [0,1] and sources are required; unattributed claims are rejected.
- **Externalized state**: no causal evidence lives in process memory. The graph (SQLite + networkx cache), audit spine (JSONL hash chain), and idempotency store are the system of record.
- **Provenance required**: every ingested claim must carry a source. No hallucination by construction: answers come only from ingested, sourced, active claims.

## Cryptographic guarantees

- **Signed audits**: HMAC SHA256 over canonical audit payload when a signing secret is supplied. Tampering is detectable via `verify_chain`.
- **Hash chained ledger**: each audit line carries `prev_hash` (SHA256 of prior line). Editing any historical record breaks the chain.
- **Secret policy**: signing secrets must be 32 bytes or more (RFC 7518). The API refuses to boot with a weak secret.

## Network

- **SSRF guard** (`trustcore.security.is_ssrf_safe`): resolves URL host via DNS and blocks link-local, loopback, RFC1918, and ULA ranges. Cloud metadata endpoints are unreachable.
- **Rate limiting**: slowapi limits on `/api/v1/causal/ingest` and `/api/v1/causal/simulate` per IP.

## Abuse resistance

- **Confidence floor**: claims below 0.5 are marked contested, never silently promoted.
- **Honesty widening**: thin data (n<5) widens CI 1.8x, so a low-evidence decision is visibly uncertain.
- **Immutable audit**: retraction soft-deletes; history is kept for regulator replay.

## Supply chain

- **SAST**: `bandit -r causala/src/causa --severity-level medium` - no medium+ issues
- **SCA**: `pip-audit` - no known vulnerabilities (run before release)
- CI blocks merges on any medium+ bandit finding or gate regression

## Known limitations

- The in-proc graph is for a single twin instance. Multi-replica would use Postgres + Neo4j backplane (wired in deploy, not in process).
- Effect-size fitting today uses confidence as proxy for magnitude plus variance-derived CI. A full PyMC posterior per edge is roadmap but the simulate API does not change when it lands.
- Warehouse ingestion today is CSV/JSON batch. Streaming via Kafka/Flink is roadmap.
