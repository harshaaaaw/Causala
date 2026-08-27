# Contributing to CAUSALA

Thanks for looking at CAUSALA. CAUSALA is a standalone causal-inference retrieval
engine: it compiles a provenance-backed causal knowledge layer and answers
"why did this happen?" and "what if we do X?" with citations. It imports no other
product.

## What lives here
- `causala/` - the engine (ingest, retract, traversal, conflict, API, CLI)
- `ragforge/` - structure-aware RAG used to source causal claims from documents
- `trustcore/` - bundled primitives (event bus, security, audit spine)

## Local setup
```bash
python -m venv .venv && source .venv/Scripts/activate
pip install -e ./causala
export CAUSALA_JWT_SECRET=$(python -c "import secrets; print(secrets.token_hex(16))")
```

## Quality gate (runs in CI)
```bash
ruff check .
mypy . --ignore-missing-imports
bandit -r causa
pytest
```

## Rules
- No cross-product imports. CAUSALA must stand alone.
- Every claim needs a source (provenance). No unattributed assertions.
- Confidence floor is first-class: weak claims are contested, never promoted silently.
- Tenant isolation on every query.
