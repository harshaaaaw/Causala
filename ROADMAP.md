# ROADMAP

## Now (0.3.x)

- Simulate with 90% CI + honesty engine + signed hash-chained audit (shipped)
- TUI dashboard (Textual) with Graph/Simulate/Audit/Agents/Skills
- Any-agent connector (claude, codex, hermes, openclaw, generic) to same ledger
- Warehouse CSV/JSON ingest with pluggable fitter
- Skill system: hub at `causala/src/causa/skills/hub` + `~/.causala/skills`

## Next (0.4)

- Bayesian posterior per edge via PyMC + CI from posterior samples (replaces variance proxy, API unchanged)
- DoWhy refutation (placebo, bootstrap, subset) and surface p-value on audit
- Neo4j backplane for graph at 100k+ edges (current networkx over SQLite scales to ~1M edges)
- Signed audit export bundle for regulator replay (SAML-compatible package)

## Later (0.5)

- Streaming ingest: Kafka/Flink exactly-once into the same graph
- Per-role Grafana panes (CFO margin, CMO churn, COO supply) querying audit API
- Hosted multi-user TUI and SAML SSO (ABAC, PII redaction)

## Not planned

- Competing with 250B-transaction Fortune-500 causal foundation models. Per-company small-data honesty is the thesis.

Progress is tracked in GitHub issues. PRs welcome - see CONTRIBUTING.md quality gate.
