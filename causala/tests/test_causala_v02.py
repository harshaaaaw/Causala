"""Tests for CAUSALA v0.2 production-grade fixes (gaps C2-C10).

RED first: these assert the new behavior we will build.
"""
from __future__ import annotations

from causa import Causala


def test_idempotent_ingest_does_not_duplicate(tmp_path):
    c = Causala(db_path=str(tmp_path / "causala.db"))
    k = {"cause": "x", "effect": "y", "confidence": 0.8, "source": "s1", "tenant_id": "acme"}
    id1 = c.ingest_claim(**k)
    id2 = c.ingest_claim(**k)  # same idempotency key
    assert id1 == id2  # same claim returned, no duplicate
    assert len(c.retrieve_causes("y", "acme")) == 1


def test_retract_makes_claim_unavailable(tmp_path):
    c = Causala(db_path=str(tmp_path / "causala.db"))
    cid = c.ingest_claim("a", "b", 0.9, "s1", "acme")
    c.retract_claim(cid, reason="superseded by newer evidence")
    assert c.get_claim(cid) is None  # inactive
    assert c.explain_effect("b", "acme").cause is None  # no longer retrievable


def test_supersede_keeps_history(tmp_path):
    c = Causala(db_path=str(tmp_path / "causala.db"))
    old = c.ingest_claim("a", "b", 0.6, "s1", "acme")
    new = c.ingest_claim("a", "b", 0.9, "s2", "acme", supersedes=old)
    assert c.get_claim(new).supersedes == old
    assert c.explain_effect("b", "acme").cause == "a"  # still resolvable


def test_backward_ancestry_walk(tmp_path):
    c = Causala(db_path=str(tmp_path / "causala.db"))
    c.ingest_claim("flag_on", "shift", 0.8, "i1", "acme")
    c.ingest_claim("shift", "hotspot", 0.7, "i2", "acme")  # hotspot <- shift <- flag_on
    chain = c.retrieve_ancestors("hotspot", "acme")
    causes = [cl.cause for cl in chain]
    assert "shift" in causes and "flag_on" in causes  # walks UP the graph


def test_conflict_detection_surfaces_A_to_B_and_C(tmp_path):
    c = Causala(db_path=str(tmp_path / "causala.db"))
    c.ingest_claim("a", "b", 0.8, "s1", "acme")
    c.ingest_claim("a", "c", 0.8, "s2", "acme")  # conflicting outcome for same cause
    conflicts = c.flag_conflicts("acme")
    assert ("a", "b", "c") in conflicts  # surfaces the conflict


def test_graph_cache_invalidated_on_ingest(tmp_path):
    c = Causala(db_path=str(tmp_path / "causala.db"))
    c.ingest_claim("a", "b", 0.8, "s1", "acme")
    c.retrieve_path("a", "b", "acme")  # warms cache
    c.ingest_claim("b", "d", 0.7, "s2", "acme")  # new edge
    chain = c.retrieve_path("a", "d", "acme")
    assert len(chain) == 2  # path reflects the new edge -> cache invalidated
