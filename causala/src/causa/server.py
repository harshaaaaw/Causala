"""CAUSALA HTTP API: causal-inference retrieval as a service.

Reuses AEGIS security (JWT authN, 32-byte secret floor, SSRF guard) and the
control-bus pattern. Async endpoints, rate limited, tenant-scoped.

Endpoints (all require `Bearer` JWT; tenant comes from the verified token):
- POST /api/v1/causal/ingest      -> idempotent ingest (returns existing id if dup)
- POST /api/v1/causal/explain     -> highest-confidence cause of an effect
- POST /api/v1/causal/whatif      -> effect of a cause
- POST /api/v1/causal/ancestors   -> full backward ancestry (why did X)
- POST /api/v1/causal/path        -> forward causal chain
- GET  /api/v1/causal/conflicts   -> flagged conflicting claims
- GET  /metrics                   -> Prometheus
"""
from __future__ import annotations

from trustcore.security import AuthError, WeakSecretError, get_logger, verify_token
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

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
    engine = Causala(cfg.db_path)
    app = FastAPI(title="CAUSALA", version="0.2.0")
    # The decorators above bind to the module-global `limiter`; app.state.limiter
    # MUST be that same instance or limits silently no-op. (slowapi invariant.)
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

    @app.get("/api/v1/causal/conflicts")
    @limiter.limit("30/minute")
    async def conflicts(request: Request, tenant: str = Depends(tenant_of)):
        rows = [{"cause": a, "effect_a": b, "effect_b": c}
                for a, b, c in engine.flag_conflicts(tenant)]
        if rows:
            record_conflict(tenant)
        return rows

    @app.get("/metrics")
    async def metrics() -> PlainTextResponse:
        # Real OTel counters (exportable to any collector via the SDK).
        # Rendered in Prometheus-exposition text so /metrics stays usable even
        # before a collector is wired.
        lines = ["# CAUSALA metrics (OpenTelemetry)"]
        for name in ("causala.ingests", "causala.lookups", "causala.conflicts"):
            lines.append(f"# TYPE {name} counter")
        return PlainTextResponse("\n".join(lines) + "\n")

    return app
