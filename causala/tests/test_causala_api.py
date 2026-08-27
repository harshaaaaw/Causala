"""Tests for CAUSALA HTTP API + anti-slop gate (gaps C6, C7)."""
from __future__ import annotations

from trustcore.security import make_token
from fastapi.testclient import TestClient

from causa.server import get_app

SECRET = "0" * 32  # 32-byte floor


def _client(tmp_path):
    db = str(tmp_path / "api.db")
    app = get_app(db, SECRET, enable_rate_limit=False)
    return TestClient(app)


def test_ingest_and_explain_via_api(tmp_path):
    c = _client(tmp_path)
    tok = make_token("acme", "svc", SECRET)
    r = c.post("/api/v1/causal/ingest",
               json={"cause": "flag_on", "effect": "hotspot", "confidence": 0.8,
                     "source": "inc-1"},
               headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 200
    r2 = c.post("/api/v1/causal/explain", json={"key": "hotspot"},
                headers={"Authorization": f"Bearer {tok}"})
    assert r2.status_code == 200
    assert r2.json()["cause"] == "flag_on"
    assert "inc-1" in r2.json()["citations"]


def test_api_rejects_missing_token(tmp_path):
    c = _client(tmp_path)
    r = c.post("/api/v1/causal/explain", json={"key": "x"})
    assert r.status_code == 401


def test_api_tenant_isolation(tmp_path):
    c = _client(tmp_path)
    tok_acme = make_token("acme", "svc", SECRET)
    tok_rival = make_token("rival", "svc", SECRET)
    c.post("/api/v1/causal/ingest",
           json={"cause": "a", "effect": "b", "confidence": 0.8, "source": "s1"},
           headers={"Authorization": f"Bearer {tok_acme}"})
    r = c.post("/api/v1/causal/explain", json={"key": "b"},
               headers={"Authorization": f"Bearer {tok_rival}"})
    assert r.json()["cause"] is None  # rival sees nothing


def test_ancestors_endpoint_returns_chain(tmp_path):
    c = _client(tmp_path)
    tok = make_token("acme", "svc", SECRET)
    c.post("/api/v1/causal/ingest",
           json={"cause": "f", "effect": "s", "confidence": 0.8, "source": "i1"},
           headers={"Authorization": f"Bearer {tok}"})
    c.post("/api/v1/causal/ingest",
           json={"cause": "s", "effect": "h", "confidence": 0.7, "source": "i2"},
           headers={"Authorization": f"Bearer {tok}"})
    r = c.post("/api/v1/causal/ancestors", json={"key": "h"},
               headers={"Authorization": f"Bearer {tok}"})
    causes = {x["cause"] for x in r.json()}
    assert {"f", "s"} <= causes
