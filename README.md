# CAUSALA

**The causal-inference retrieval engine for enterprise AI and operations.**

CAUSALA answers "why did this happen?" and "what happens if we do X?" with
citation-backed causal claims. It compiles a knowledge layer of causal assertions
with provenance and confidence, supports bi-directional traversal (cause -> effect
and effect -> root causes), surfaces conflicts instead of hiding them, and scopes
every query by tenant.

## The one problem it solves

"I have to make a high-cost decision (price change, headcount, agent policy) with
only rear-view dashboards and gut feel, and I cannot defend the call to my board or
a regulator."

CAUSALA turns that into a quantified, traceable, auditable decision.

## What it does

- **Idempotent ingest** - same (tenant, cause, effect, source) never duplicates.
- **Retraction & supersession** - claims can be corrected; history is kept.
- **Bi-directional traversal** - forward path (cause -> effect) and backward ancestry
  (every root cause of an effect), both citation-backed.
- **Conflict surfacing** - a cause with two divergent effects is flagged, not hidden.
- **Confidence gating** - claims below a floor are marked contested, never presented
  as fact.
- **Tenant isolation** - every query is scoped by tenant_id; idempotency includes it.
- **No hallucination** - answers come only from ingested, sourced, active claims.

## Why it is real

- Built on `networkx` for the causal graph and `sqlalchemy` for the provenance store.
- Every ingest writes a structured, source-attributed record. Retrieval is graph
  traversal over that store, not a vector guess.
- Honest about uncertainty: the confidence floor and contested flag are first-class,
  so a weak claim is never silently promoted.

## Quickstart

```bash
python -m venv .venv && source .venv/Scripts/activate   # or bin/activate
pip install -e ./causala
export CAUSALA_JWT_SECRET=$(python -c "import secrets; print(secrets.token_hex(16))")
causala serve --db ./causala.db
```

Ingest and query:

```python
from causa import Causala

engine = Causala("./causala.db")
cid = engine.ingest_claim("discount", "margin_up", 0.82,
                          source="finance-q3-review", tenant_id="acme")
ans = engine.explain_effect("margin_up", tenant_id="acme")
print(ans.cause, ans.confidence, ans.citations)
# -> discount 0.82 ['finance-q3-review']
```

## How CAUSALA compares (the moat)

| Capability | Correlation dashboards | LLM + RAG Q&A | CAUSALA |
|---|---|---|---|
| Citation-backed causes | no | no | yes (source per claim) |
| Bi-directional traversal (effect to root cause) | no | no | yes |
| Conflict surfacing | no | no | yes |
| Confidence floor (no silent trust) | no | no | yes |
| Tenant isolation | partial | partial | first-class |
| No hallucination by construction | no | no | yes (only ingested claims) |

The differentiator is that every answer carries its source and the graph is traversed,
not guessed. A weak claim is flagged contested; it is never silently promoted to fact.

## Roadmap

- [ ] Pluggable fitting layer (OLS/Bayesian on client data) behind the ingest API.
- [ ] NL summarizer in front of `explain`/`whatif` to emit canonical tokens.
- [ ] Web UI for conflict review and graph exploration.
- [ ] Signed audit export for regulator replay.

## Quality

- `pytest` across the engine, API, bus adapter, CLI, graph traversal, and fault
  injection.
- Static gates: `ruff`, `mypy --ignore-missing-imports`, `bandit` stay clean in CI.
- FastAPI surface: `POST /graph`, `POST /fit`, `POST /simulate`, `GET /audit/{id}`.

## Honest limitations

- CAUSALA is a causal-knowledge retrieval and reasoning engine over ingested claims.
  It does not itself fit effect sizes from raw warehouse data (that is an upstream
  ingestion job); it reasons over whatever causal claims are fed to it, with
  provenance. The confidence floor and traversal are real; a full Bayesian/DoWhy
  fitting layer is a natural next build.
- The bundled `trustcore` package provides the event bus, JWT/SSRF security, and
  tamper-evident spine CAUSALA relies on. CAUSALA imports no other product.

## Repo layout

```
causala/     the engine (ingest, retract, traversal, conflict, API, CLI)
ragforge/    structure-aware RAG used to source causal claims from documents
trustcore/   bundled primitives: event bus, security, audit spine
```
