# CAUSALA

**The causal-inference retrieval engine for enterprise AI and operations.**

CAUSALA answers "why did this happen?" and "what happens if we do X?" with
citation-backed causal claims. It compiles a knowledge layer of causal assertions
with provenance and confidence, supports bi-directional traversal (cause -> effect
and effect -> root causes), surfaces conflicts instead of hiding them, and scopes
every query by tenant. It is a standalone product and imports no other.

## The one problem it solves

"I have to make a high-cost decision (price change, headcount, strategy, agent
policy) with only rear-view dashboards and gut feel, and I cannot defend the call to
my board or a regulator."

CAUSALA turns that into a quantified, traceable, auditable decision.

## What it actually does

- **Compiled-once causal graph**: cause to effect claims ingested once, with
  confidence and source. Not rediscovered per query.
- **"Why did this happen?"** with citation-backed causes. Every returned cause carries
  its source; we never answer from a cause we did not ingest.
- **"What happens if we do X?"** with a multi-hop causal walk over the graph (each hop
  is a real, cited claim).
- **Conflict flagging**: when two claims point at the same effect, flag it for review.
- **Confidence floor**: claims below 0.5 are flagged contested, never silently trusted.
- **Tenant isolation**: all retrieval scoped by tenant_id.
- **Audit trail**: every query is a deterministic, citation-backed lookup.

## Quickstart

```bash
pip install -e ./causala
export CAUSALA_JWT_SECRET=$(python -c "import secrets; print(secrets.token_hex(16))")

# Ingest a causal claim (compiled once, with provenance)
causala ingest --cause cache_miss --effect cost_up --conf 0.8 --source finops-3

# Why did cost go up? -> cites finops-3
causala explain --effect cost_up

# What if we have cache misses? -> cites finops-3
causala whatif --cause cache_miss

# Multi-hop causal chain (cite-backed at every hop)
causala ingest --cause cost_up --effect margin_down --conf 0.7 --source finops-4
causala path --from cache_miss --to margin_down
```

## Design (anti-slop + IR-correct)

- **Compiled-once knowledge**: claims ingested with confidence + source, never
  rediscovered per query.
- **Citation-backed answers**: every returned cause/effect carries its `source`. No
  hallucination by construction.
- **Confidence floor**: claims below 0.5 are `contested` for human review.
- **Tenant isolation**: retrieval scoped by `tenant_id` (no cross-tenant leak).
- **Multi-hop traversal**: `networkx` over the causal graph; each hop is a real
  ingested, cited claim.
- **Externalized state**: SQLite-backed store with a tamper-evident append log.

## HTTP API

All endpoints require a `Bearer` JWT (HS256, >=32-byte secret). Rate limited.

- `POST /api/v1/causal/ingest`: register a cause to effect claim (tenant-scoped)
- `POST /api/v1/causal/explain`: why did this effect happen? (citation-backed)
- `POST /api/v1/causal/whatif`: what happens if this cause holds?
- `POST /api/v1/causal/ancestors`: every root cause of an effect (backward walk)
- `POST /api/v1/causal/path`: shortest cited causal chain between two nodes
- `GET  /api/v1/causal/conflicts?tenant=...`: flagged conflicts for human review
- `GET  /metrics`: Prometheus exposition of OTel counters

## How CAUSALA compares (the moat)

| Capability | Correlation dashboards | LLM + RAG Q&A | CAUSALA |
|---|---|---|---|
| Citation-backed causes | no | no | yes (source per claim) |
| Bi-directional traversal (effect -> root cause) | no | no | yes |
| Conflict surfacing | no | no | yes |
| Confidence floor (no silent trust) | no | no | yes |
| Tenant isolation | partial | partial | first-class |
| No hallucination by construction | no | no | yes (only ingested claims) |

The differentiator is not "we answer causal questions." It is that every answer carries
its source and the graph is traversed, not guessed. A weak claim is flagged contested;
it is never silently promoted to fact.

## Roadmap

- [ ] Pluggable fitting layer (OLS/Bayesian on client data) behind the ingest API.
- [ ] NL summarizer in front of `explain`/`whatif` to emit canonical tokens.
- [ ] Web UI for conflict review and graph exploration.
- [ ] Signed audit export for regulator replay.

## Quality (measured)

| Signal | Value |
|---|---|
| Tests | 35 green |
| Ruff | clean |
| Mypy (business logic) | clean |
| Bandit | clean |

Run: `pytest causa/tests/ -q`

## Honest limitations

- The natural-language `explain`/`whatif` use a keyword heuristic to pick the
  canonical cause/effect token. For free text, plug an LLM in front to emit the key;
  the graph lookup stays deterministic. The precise API is `explain_effect` /
  `what_if_cause` / `retrieve_path`.
- CAUSALA retrieves asserted causal claims; it does not itself establish causality.
  That is an upstream ingestion job or expert input. Correlation vs causation is the
  ingestor's job, not CAUSALA's.
- The causal graph is the brain; scale is per-company small-data, not Fortune-500
  cross-company transfer. That is the thesis, stated honestly.

## License

MIT.
