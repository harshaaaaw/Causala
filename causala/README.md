# CAUSALA - Package README

**Use this if you `pip install causala`. For the full product, see the [root README](../README.md).**

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](../../LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](#)
[![Tests](https://img.shields.io/badge/tests-29%20green-brightgreen.svg)](#quality)

## What this package is

`causala` is the twin library: causal graph, simulation with 90% CI, honesty engine, hash-chained audit, tenant isolation. The repo bundles `ragforge` (structure-aware RAG for claim sourcing) at top level `ragforge/` and `examples/warehouse.csv` for try-without-warehouse. This package alone is importable and testable.

## Install

```bash
pip install -e ./causala -e ./ragforge  # from repo root, twin + retriever
# or after publish
pip install causala
```

## Use - simulate a lever

```bash
causala quickstart --tenant acme --db ./causala.db
# -> ingest price -> demand 0.82
# -> Simulate: price +3% -> demand: 2.46%  [1.985, 2.935]  audit 82f15708

causala simulate --lever price --delta 3 --tenant acme --db ./causala.db
causala audit --id 82f15708 --tenant acme --db ./causala.db
causala verify-chain --tenant acme --db ./causala.db
```

```python
from causa import Causala

engine = Causala("./causala.db")
engine.ingest_claim("price", "demand", 0.82, source="finance-q3-review", tenant_id="acme")
engine.ingest_claim("demand", "margin", 0.75, source="finance-q3-review", tenant_id="acme")

results = engine.simulate("price", 3.0, tenant_id="acme")
for r in results:
    print(r.outcome, r.point, r.ci_low, r.ci_high, r.audit_id, r.honest_note)
    # -> demand 2.46 1.985 2.935 82f15708 thin data -> wide CI
```

## Warehouse ingest

```bash
causala ingest-csv --file warehouse.csv --tenant acme --db ./causala.db
# csv header: cause,effect,confidence,source  (or lever,outcome,delta)
```

```python
engine.ingest_csv("warehouse.csv", tenant_id="acme")
```

## HTTP API

All endpoints require `Bearer` JWT (HS256, 32-byte secret floor). Rate limited by slowapi.

- `POST /api/v1/causal/ingest` - idempotent ingest
- `POST /api/v1/causal/explain` - why did X happen, citation-backed
- `POST /api/v1/causal/whatif` - what if we do X
- `POST /api/v1/causal/simulate` - lever + delta% -> outcomes with point + 90% CI + audit (core)
- `POST /api/v1/causal/ancestors` - every root cause
- `POST /api/v1/causal/path` - forward causal chain
- `GET  /api/v1/causal/conflicts` - flagged conflicts
- `GET  /api/v1/causal/audit/{id}` - signed audit record
- `GET  /api/v1/causal/audits` - recent audits
- `GET  /metrics` - Prometheus exposition of OTel counters

See `src/causa/server.py` for request shapes.

## CLI reference

| Command | What it does |
|---|---|
| `causala quickstart` | Scaffold demo graph + simulate price +3% -> point + CI + audit |
| `causala simulate --lever X --delta 3` | Lever intervention -> outcomes with 90% CI and receipt |
| `causala ingest --cause X --effect Y --conf 0.8 --source S` | Ingest a cited causal claim |
| `causala ingest-csv --file warehouse.csv` | Batch ingest from warehouse export |
| `causala explain --effect Y` | Why did Y happen, citation-backed |
| `causala whatif --cause X` | What happens if X |
| `causala audit --id <audit_id>` | Fetch signed audit record |
| `causala verify-chain` | Verify hash chain integrity |
| `causala tui` | Terminal dashboard: graph, simulate, audit |
| `causala agent claude "task"` | Connect any agent to same ledger |

## Security model

- JWT 32-byte floor, SSRF guard, rate limiting, tenant-scoped queries and audit.
- Hash-chained ledger: `prev_hash` is sha256 of prior line; tampering is detectable via `verify-chain`.
- When `audit_secret` is supplied, records are HMAC-signed.

Full model: [SECURITY.md](SECURITY.md)

## Quality

| Signal | Value |
|---|---|
| Tests | 29 green |
| Ruff | clean |
| Mypy | clean via overrides |
| Bandit | clean at medium severity (subprocess lows are agent connector, expected) |

Run: `pytest causala/tests -q`

## License

MIT - see [LICENSE](../../LICENSE)
