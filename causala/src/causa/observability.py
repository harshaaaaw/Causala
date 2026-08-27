"""Observability for CAUSALA: OpenTelemetry metrics (mirror of AEGIS).

Exports the same signals OTel consumers expect. Falls back to the SDK no-op
meter when no MeterProvider is configured, so importing this is always safe
(under tests and a bare CLI run).
"""
from __future__ import annotations

from opentelemetry import metrics

_meter = metrics.get_meter("causala", "0.1.0")

INGESTS = _meter.create_counter(
    "causala.ingests", description="Causal claims ingested, by tenant")
LOOKUPS = _meter.create_counter(
    "causala.lookups", description="Causal lookups (explain/whatif), by tenant")
CONFLICTS = _meter.create_counter(
    "causala.conflicts", description="Conflict flags raised, by tenant")


def record_ingest(tenant: str) -> None:
    INGESTS.add(1, {"tenant": tenant})


def record_lookup(tenant: str) -> None:
    LOOKUPS.add(1, {"tenant": tenant})


def record_conflict(tenant: str) -> None:
    CONFLICTS.add(1, {"tenant": tenant})
