"""Tests for CAUSALA graph traversal + AEGIS control-bus integration."""

from __future__ import annotations

from causa import Causala


def test_multihop_causal_path_is_cite_backed(tmp_path):
    c = Causala(db_path=str(tmp_path / "causala.db"))
    # A -> B -> C chain (two hops)
    c.ingest_claim("feature_flag_on", "traffic_shift", 0.8, "inc-1", "acme")
    c.ingest_claim("traffic_shift", "db_hotspot", 0.7, "inc-2", "acme")
    chain = c.retrieve_path("feature_flag_on", "db_hotspot", tenant_id="acme")
    assert len(chain) == 2
    # every link in the chain is citation-backed
    assert {cl.source for cl in chain} == {"inc-1", "inc-2"}


def test_multihop_respects_tenant_isolation(tmp_path):
    c = Causala(db_path=str(tmp_path / "causala.db"))
    c.ingest_claim("a", "b", 0.8, "s1", "acme")
    c.ingest_claim("b", "c", 0.8, "s2", "acme")
    # rival tenant has no claims -> no path
    assert c.retrieve_path("a", "c", tenant_id="rival-co") == []


def test_contested_claim_excluded_from_confident_path(tmp_path):
    c = Causala(db_path=str(tmp_path / "causala.db"))
    c.ingest_claim("x", "y", 0.9, "strong", "acme")
    # a low-confidence alternative edge should be flagged contested
    cid = c.ingest_claim("x", "z", 0.1, "weak", "acme")
    cl = c.get_claim(cid)
    assert cl.contested is True
