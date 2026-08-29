"""CAUSALA HTTP API: causal-inference retrieval as a service.

Endpoints (all require `Bearer` JWT; tenant comes from verified token):
- POST /api/v1/causal/ingest      -> idempotent ingest (returns existing id if dup)
- POST /api/v1/causal/explain     -> highest-confidence cause of an effect
- POST /api/v1/causal/whatif      -> effect of a cause
- POST /api/v1/causal/ancestors   -> full backward ancestry (why did X)
- POST /api/v1/causal/path        -> forward causal chain
- POST /api/v1/causal/simulate    -> lever + delta -> outcomes + 90% CI + audit (core business problem)
- GET  /api/v1/causal/conflicts   -> flagged conflicting claims
- GET  /api/v1/causal/audit/{id}  -> audit record
- GET  /api/v1/causal/audits      -> recent audits for tenant
- GET  /metrics                   -> Prometheus
"""
from __future__ import annotations

import os

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from trustcore.security import AuthError, WeakSecretError, get_logger, verify_token

from . import Causala
from .observability import record_conflict, record_ingest, record_lookup


class IngestReq(BaseModel):
    cause: str
    effect: str
    confidence: float
    source: str
    mechanism: str = ""


class KeyReq(BaseModel):
    key: str


class SimulateReq(BaseModel):
    lever: str
    delta_percent: float


log = get_logger("causala.server")


class CausalaConfig:
    def __init__(self, db_path: str, jwt_secret: str):
        from trustcore.security import require_strong_secret
        require_strong_secret(jwt_secret)  # refuses weak secrets (RFC 7518)
        self.db_path = db_path
        self.jwt_secret = jwt_secret


limiter = Limiter(key_func=get_remote_address, storage_uri="memory://")


def get_app(db_path: str, jwt_secret: str, enable_rate_limit: bool = True) -> FastAPI:
    cfg = CausalaConfig(db_path=db_path, jwt_secret=jwt_secret)
    engine = Causala(cfg.db_path, audit_secret=jwt_secret)
    app = FastAPI(title="CAUSALA", version="0.3.0")
    # The decorators bind to module-global limiter; state must be same instance or limits no-op.
    limiter.enabled = enable_rate_limit
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    def tenant_of(req: Request) -> str:
        auth = req.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            raise HTTPException(401, "missing bearer token")
        token = auth.split(" ", 1)[1]
        try:
            claims = verify_token(token, cfg.jwt_secret)
        except (AuthError, WeakSecretError) as e:
            raise HTTPException(401, f"invalid token: {e}")
        return claims["tenant_id"]

    @app.post("/api/v1/causal/ingest")
    @limiter.limit("20/minute")
    async def ingest(request: Request, body: IngestReq, tenant: str = Depends(tenant_of)):
        cid = engine.ingest_claim(body.cause, body.effect, body.confidence,
                                  body.source, tenant, body.mechanism)
        record_ingest(tenant)
        return {"claim_id": cid, "tenant": tenant}

    @app.post("/api/v1/causal/explain")
    @limiter.limit("30/minute")
    async def explain(request: Request, body: KeyReq, tenant: str = Depends(tenant_of)):
        ans = engine.explain_effect(body.key, tenant)
        record_lookup(tenant)
        return {"cause": ans.cause, "effect": ans.effect, "confidence": ans.confidence,
                "citations": ans.citations, "contested": ans.contested}

    @app.post("/api/v1/causal/whatif")
    @limiter.limit("30/minute")
    async def whatif(request: Request, body: KeyReq, tenant: str = Depends(tenant_of)):
        ans = engine.what_if_cause(body.key, tenant)
        return {"cause": ans.cause, "effect": ans.effect, "confidence": ans.confidence,
                "citations": ans.citations}

    @app.post("/api/v1/causal/ancestors")
    @limiter.limit("30/minute")
    async def ancestors(request: Request, body: KeyReq, tenant: str = Depends(tenant_of)):
        chain = engine.retrieve_ancestors(body.key, tenant)
        return [{"cause": c.cause, "effect": c.effect, "confidence": c.confidence,
                 "source": c.source} for c in chain]

    @app.post("/api/v1/causal/path")
    @limiter.limit("30/minute")
    async def path(request: Request, start: str, goal: str, tenant: str = Depends(tenant_of)):
        chain = engine.retrieve_path(start, goal, tenant)
        return [{"cause": c.cause, "effect": c.effect, "confidence": c.confidence,
                 "source": c.source} for c in chain]

    @app.post("/api/v1/causal/simulate")
    @limiter.limit("20/minute")
    async def simulate(request: Request, body: SimulateReq, tenant: str = Depends(tenant_of)):
        """Core decision twin: lever + delta -> outcomes with point + 90% CI + audit."""
        if abs(body.delta_percent) > 100:
            raise HTTPException(400, "delta_percent must be within [-100, 100]")
        results = engine.simulate(body.lever, body.delta_percent, tenant)
        record_lookup(tenant)
        return [
            {
                "lever": r.lever,
                "delta_percent": r.delta_percent,
                "outcome": r.outcome,
                "point": r.point,
                "ci_low": r.ci_low,
                "ci_high": r.ci_high,
                "ci_width": r.ci_width,
                "confidence": r.confidence,
                "contested": r.contested,
                "citations": r.citations,
                "path": r.path,
                "honest_note": r.honest_note,
                "audit_id": r.audit_id,
            }
            for r in results
        ]

    @app.get("/api/v1/causal/conflicts")
    @limiter.limit("30/minute")
    async def conflicts(request: Request, tenant: str = Depends(tenant_of)):
        rows = [{"cause": a, "effect_a": b, "effect_b": c}
                for a, b, c in engine.flag_conflicts(tenant)]
        if rows:
            record_conflict(tenant)
        return rows

    @app.get("/api/v1/causal/audit/{audit_id}")
    @limiter.limit("30/minute")
    async def audit_get(request: Request, audit_id: str, tenant: str = Depends(tenant_of)):
        rec = engine.get_audit(audit_id)
        if not rec or rec.get("tenant_id") != tenant:
            raise HTTPException(404, "audit not found")
        return rec

    @app.get("/api/v1/causal/audits")
    @limiter.limit("30/minute")
    async def audits(request: Request, tenant: str = Depends(tenant_of)):
        return engine.recent_audits(tenant)

    @app.get("/metrics")
    async def metrics() -> PlainTextResponse:
        lines = ["# CAUSALA metrics (OpenTelemetry)"]
        for name in ("causala.ingests", "causala.lookups", "causala.conflicts"):
            lines.append(f"# TYPE {name} counter")
        return PlainTextResponse("\n".join(lines) + "\n")

    @app.get("/api/v1/causal/graph")
    @limiter.limit("30/minute")
    async def graph_snapshot(request: Request, tenant: str = Depends(tenant_of)):
        """All active claims for the tenant as edges (cause, effect, confidence, source)."""
        try:
            g = engine._graph(tenant)
        except RuntimeError as _e:  # graph build failure (e.g. db locked) must not crash the UI
            log.warning("graph snapshot failed: %s", _e)
            return []
        edges = []
        for cause, effect, data in g.edges(data=True):
            claim = data.get("claim")
            edges.append({
                "cause": cause,
                "effect": effect,
                "confidence": claim.confidence if claim else 0.0,
                "source": claim.source if claim else "",
            })
        return edges

    @app.post("/token")
    async def bootstrap_token(request: Request, tenant: str = "acme"):
        """Dev bootstrap: mint a Bearer token for the local twin.

        Only exposed when CAUSALA_UI_TOKEN=1 (the serve default). Production
        deployments must set CAUSALA_UI_TOKEN=0 and issue tokens via their IdP.
        """
        if os.environ.get("CAUSALA_UI_TOKEN", "1") != "1":
            raise HTTPException(403, "token bootstrap disabled (set CAUSALA_UI_TOKEN=1 for local UI)")
        from trustcore.security import make_token
        token = make_token(tenant, "ui", cfg.jwt_secret)
        return {"tenant_id": tenant, "token": token}

    @app.post("/api/v1/causal/verify-chain")
    @limiter.limit("10/minute")
    async def verify_chain(request: Request, tenant: str = Depends(tenant_of)):
        ok, broken_at = engine.verify_audit_chain()
        return {"ok": ok, "broken_at": broken_at, "entries": len(engine.recent_audits(tenant, limit=10 ** 9))}

    # Web UI — premium browser twin, no build step, same twin as CLI/TUI
    try:
        import pathlib as _pl
        _static = _pl.Path(__file__).parent / "static"
        if _static.exists():
            app.mount("/web", StaticFiles(directory=str(_static), html=True), name="web")

            @app.get("/", include_in_schema=False)
            async def _web_root():
                return FileResponse(str(_static / "index.html"))
    except (OSError, RuntimeError) as _e:
        log.warning("web UI not mounted: %s", _e)

    return app
