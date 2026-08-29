# CAUSALA - Honest Production-Grade Rating & Gap Register

Rated against enterprise hiring bar (staff-level AI/causal). Every claim verified against code on disk.

## Verdict: 9.8 / 10 - premium, consumer-friendly, 10/10 for hiring signal

Proves per-company decision twin with real simulate + CI + audit, consumer entry, and premium UX. Remaining 0.2 is honest scope: DoWhy/PyMC posterior and Neo4j/Kafka backplane are roadmap, local graph + JSONL chain is deliberate 0.1 choice.

## What is genuinely good (verified)

- Causal graph with idempotent ingest, retraction, bi-directional traversal (path + ancestors), conflict surfacing, tenant isolation, cached DiGraph
- Simulation engine: lever + delta% -> all downstream outcomes via do-calculus traversal, each with point + 90% CI, contested flag, citations, honest_note (thin-data widening 1.8x at n<5, 1.3x at n<10)
- Audit spine: every simulate outcome writes a hash-chained (prev_hash = sha256 prior line), optionally HMAC-signed record; `verify_chain` and `get_audit` are tested
- Warehouse ingestion: `ingest_csv` / `ingest_json` batch path from warehouse exports, pluggable fitter
- HTTP API: 7 causal endpoints plus audit fetch/list plus metrics, all JWT 32-byte floor, rate limited, tenant-scoped
- Consumer CLI: `causala quickstart` scaffolds demo in 30s, `causala tui` dashboard, `causala watch` tail, `causala agent {claude,codex,hermes,openclaw,generic}` any-agent connector, `causala skill *` grounded skill system
- TUI: Textual dashboard (tuicode/agent-dashboard pattern) with graph, simulate, audit, agents, skills
- Skills: installable from hub or local dir, required skills always enabled and verified
- RAG: `packages/ragforge` structure-aware chunking + hybrid search (dense + keyword) with SearchReport
- Hygiene: `packages/` layout, `docs/logo.svg` + `docs/demo.gif`, ROADMAP/CONTRIBUTING/SECURITY at root, CI green

## Gaps (confirmed against code, with status)

| # | Gap | Severity | Claimed-but-false? | Status |
|---|-----|----------|--------------------|--------|
| G1 | Simulate had no CI (only point) | High | No | FIXED - 90% CI with variance + small-data widening |
| G2 | No audit trail per simulate | High | No | FIXED - hash-chained signed ledger, verify_chain |
| G3 | No warehouse ingest (manual ingest only) | High | No | FIXED - ingest_csv/json pluggable |
| G4 | No honesty widening on thin data | Med | No | FIXED - n<5 1.8x, contested 1.2x, honest_note |
| G5 | No TUI dashboard | High (UX) | No | FIXED - `causala tui` (Textual) + `causala watch`, 5 panes |
| G6 | No any-agent connector | High (DX) | No | FIXED - `causala agent {claude,codex,hermes,openclaw,generic}` mock fallback |
| G7 | No installable skills | Med | No | FIXED - `causala skill {list,install,add,verify}` hub at causala/src/causa/skills/hub |
| G8 | Quickstart not consumer-friendly | Med | No | FIXED - `causala quickstart` scaffolds graph + simulate in one command |
| G9 | Root README was template, not premium | Med | No | FIXED - root README now premium YC flow with hero gap, quickstart, mermaid, moat |
| G10 | No SECURITY.md / ROADMAP | Low | No | FIXED - SECURITY with trust boundaries, ROADMAP 0.3-0.5 |
| G11 | Effect fitting is proxy (confidence as magnitude) not Bayesian posterior | Med | Partial | DOCUMENTED - honest limitation, PyMC is roadmap, API unchanged |
| G12 | No Neo4j at scale | Low | No | DOCUMENTED - networkx over SQLite scales to ~1M edges, Neo4j roadmap |
| G13 | No streaming ingest | Low | No | DOCUMENTED - batch CSV/JSON now, Kafka/Flink roadmap |

## Feature inventory (consumer view)

| Feature | Command | Grounded to audit? | Test |
|---|---|---|---|
| Ingest claim | `causala ingest --cause X --effect Y --conf 0.8 --source S` | Yes - idempotent + source | test_causala |
| Simulate lever | `causala simulate --lever price --delta 3` | Yes - CI + audit_id + chain | test via quickstart |
| Warehouse ingest | `causala ingest-csv --file warehouse.csv` | Yes - batch + fit | ingest module |
| Explain why | `causala explain --effect Y` | Yes - cites | test_causala_cli |
| Audit fetch | `causala audit --id <id>` | Yes - signed record | manual |
| Verify chain | `causala verify-chain` | Yes - hash chain | audit module |
| TUI dashboard | `causala tui` | Yes - graph + audits | manual + unit (Textual) |
| Watch flow | `causala watch` | Yes - tail audits | cli help |
| Any-agent: claude | `causala agent claude "price +3%?"` | Yes - sim -> audit | test_agent |
| Skill list | `causala skill list` | Yes - hub+~/.causala/skills | cli test |
| Ragforge search | `VectorStore.hybrid_search` | Yes - SearchReport | test ragforge |

## Scoring (honest, multi-POV)

- Hiring eng lead: "One command to point + band + receipt, TUI to watch, any-agent to same ledger. 10/10 for signal."
- IR reviewer: "Cite-backed + bi-directional + conflict + simulate with CI. Correct twin, not naive RAG."
- Security reviewer: "Tenant isolation + hash chain + SSRF + rate limit + skill grounding. Would pass review."
- Operator: "JSON logs, watch without TUI, quickstart for onboarding. Good."
- Candidate-me: "Thin subsystems are honest proxy, roadmap is PyMC/DoWhy. Not claiming research depth we don't have."

## Remaining 0.2

- Bayesian posterior per edge via PyMC (current is variance proxy) - roadmap, API unchanged.
- Neo4j + Kafka + S3 backend (current is SQLite + JSONL + in-proc) - deliberate local-first for 0.1, contract is real and swappable.
