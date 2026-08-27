"""Tests for CAUSALA: causal-inference retrieval over a compiled causal layer.

Core idea (IR, not naive RAG): CAUSALA compiles causal relationships ONCE into a
linked causal graph (nodes + directed edges with confidence + provenance), then
retrieves causally-validated, citation-backed answers to "why did X?" and
"what happens if we do Y?". No per-query rediscovery; every claim is traced.

RED first: these assert the behavior we will build.
"""
from __future__ import annotations

from causa import Causala


def test_ingest_compiles_causal_edge_with_provenance(tmp_path):
    c = Causala(db_path=str(tmp_path / "causala.db"))
    cid = c.ingest_claim(
        cause="high_inference_cost", effect="low_margin",
        confidence=0.82, source="incident-2026-014",
        tenant_id="acme", mechanism="per-token billing without cache")
    assert cid
    # the claim is retrievable and carries its provenance
    claims = c.retrieve_causes("low_margin", tenant_id="acme")
    assert any(cl.cause == "high_inference_cost" and cl.source == "incident-2026-014"
               for cl in claims)


def test_retrieval_cites_provenance_not_hallucination(tmp_path):
    c = Causala(db_path=str(tmp_path / "causala.db"))
    c.ingest_claim(cause="retry_storm", effect="timeout", confidence=0.9,
                   source="sre-postmortem-7", tenant_id="acme")
    ans = c.explain_effect("timeout", tenant_id="acme")
    # answer must cite the real source, and must NOT invent a cause we never ingested
    assert "sre-postmortem-7" in ans.citations
    assert ans.cause == "retry_storm"
    assert ans.confidence == 0.9


def test_what_if_counterfactual_is_cite_backed(tmp_path):
    c = Causala(db_path=str(tmp_path / "causala.db"))
    c.ingest_claim(cause="cache_enabled", effect="cost_down", confidence=0.75,
                   source="finops-report-q2", tenant_id="acme")
    ans = c.what_if_cause("cache_enabled", tenant_id="acme")
    assert ans.effect == "cost_down"
    assert "finops-report-q2" in ans.citations


def test_tenant_isolation_on_retrieval(tmp_path):
    c = Causala(db_path=str(tmp_path / "causala.db"))
    c.ingest_claim(cause="x", effect="y", confidence=0.5, source="s1", tenant_id="acme")
    # rival tenant sees nothing
    claims = c.retrieve_causes("y", tenant_id="rival-co")
    assert claims == []


def test_low_confidence_claim_flagged_not_silent(tmp_path):
    c = Causala(db_path=str(tmp_path / "causala.db"))
    cid = c.ingest_claim(cause="a", effect="b", confidence=0.2, source="weak",
                         tenant_id="acme")
    cl = c.get_claim(cid)
    assert cl.contested is True  # confidence < 0.5 -> flagged for review
