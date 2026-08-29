# Contributing to CAUSALA

Thanks for looking at CAUSALA. CAUSALA is a per-company decision twin that defends million-dollar levers with a point, a 90% band, and a signed audit. It imports no other product.

## What lives here

- `causala/` - the twin (graph, simulate with CI, audit spine, API, CLI, TUI, agents, skills)
- `ragforge/` - structure-aware RAG used to source causal claims from documents (top-level, not under packages)
- `examples/` - warehouse.csv + causal_graph.json you can run without a warehouse
- `docs/` - twin graph logo and demo (amber, not AEGIS green shield)
- `trustcore` - bundled primitives inside `causala/src/trustcore` (event bus, security, audit spine)

## Local setup

```bash
python -m venv .venv && source .venv/Scripts/activate  # Windows: .venv\Scripts\activate
pip install -e ./causala -e ./ragforge
export CAUSALA_JWT_SECRET=$(python -c "import secrets; print(secrets.token_hex(16))")
causala quickstart  # proves the loop: ingest -> simulate + CI + audit
causala tui         # cockpit
```

## Quality gate (runs in CI)

```bash
ruff check causala/src ragforge --config causala/pyproject.toml
mypy causala/src/causa --config-file causala/pyproject.toml --ignore-missing-imports
bandit -r causala/src/causa ragforge --severity-level medium
pytest causala/tests ragforge/tests -q
```

The gate runs on Python 3.11 and 3.14, fail-fast false, two shards. Green is required to merge.

## Rules

- No cross-product imports. CAUSALA must stand alone (`grep -rnE "from (aegis|simforge)[ .]"` should be zero).
- Every claim needs a source (provenance). No unattributed assertions.
- Every simulate must return a point plus 90% CI plus audit_id. No false precision.
- Confidence floor is first-class: weak claims are contested, never promoted silently.
- Tenant isolation on every query and every audit.
- Honesty: thin data widens CI (n<5 -> 1.8x). Document the widening in `honest_note`.

## Good first issues

- Add a warehouse connector (Snowflake/BigQuery) that calls `ingest_csv` with fit.
- Wire DoWhy refutation (placebo) in front of `simulate` and surface the p-value on the audit.
- Add Grafana dashboards per role (CFO margin, COO churn) that query `/api/v1/causal/audits`.
