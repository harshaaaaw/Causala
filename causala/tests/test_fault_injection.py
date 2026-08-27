"""FAULT-INJECTION (mutation) tests: prove CAUSALA guards its core invariants.

These run standalone in the causa repo. The AEGIS cross-tenant invariant lives
in the aegis repo where aegis is importable.
"""
from __future__ import annotations

from causa import Causala


def test_causala_idempotency_invariant(tmp_path):
    c = Causala(str(tmp_path / "c.db"))
    k = {"cause": "x", "effect": "y", "confidence": 0.8, "source": "s1", "tenant_id": "acme"}
    assert c.ingest_claim(**k) == c.ingest_claim(**k)


def test_causala_tenant_isolation_invariant(tmp_path):
    c = Causala(str(tmp_path / "c.db"))
    c.ingest_claim("a", "b", 0.8, "s1", "acme")
    assert c.explain_effect("b", "rival").cause is None
