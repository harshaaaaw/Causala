"""CAUSALA causal-inference retrieval engine (standalone product).

Consumes causal events (ingest / retract / query) on its own event bus and
persists to its own externalized causal store. Agents and analysts ask CAUSALA
'why?' and get citation-backed causal answers. CAUSALA owns its trust primitives
(event bus, security, audit spine) via the bundled trustcore package; it imports
no other product.
"""
from __future__ import annotations

from trustcore.backbone import ControlEvent, EventBus, register_subsystem
from trustcore.security import get_logger

from . import Causala, CausalAnswer

log = get_logger("causala.service")


class CausalaSubsystem:
    name = "causala"

    def __init__(self, db_path: str):
        self._db_path = db_path
        self._engine = Causala(db_path)

    def register(self, bus: EventBus, spine) -> None:
        bus.subscribe(self.name, self.handle)
        register_subsystem(self)

    def handle(self, event: ControlEvent) -> None:
        tenant = event.tenant_id or "acme"
        if event.kind == "causal_ingest":
            p = event.payload
            self._engine.ingest_claim(
                cause=p["cause"], effect=p["effect"], confidence=p["confidence"],
                source=p["source"], tenant_id=tenant,
                mechanism=p.get("mechanism", ""), supersedes=p.get("supersedes"))
            log.info("causal_ingest", extra={"tenant": tenant, "cause": p["cause"]})
        elif event.kind == "causal_retract":
            self._engine.retract_claim(event.payload["claim_id"], reason="bus event")
            log.info("causal_retract", extra={"claim_id": event.payload["claim_id"]})
        elif event.kind == "causal_explain":
            p = event.payload
            ans = self._engine.explain_effect(p["effect"], tenant_id=tenant)
            log.info("causal_explain", extra={"effect": p["effect"], "cause": ans.cause})

    # convenience delegates
    def explain(self, effect: str, tenant_id: str) -> CausalAnswer:
        return self._engine.explain_effect(effect, tenant_id)

    def what_if(self, cause: str, tenant_id: str) -> CausalAnswer:
        return self._engine.what_if_cause(cause, tenant_id)

    def ancestors(self, effect: str, tenant_id: str, max_hops: int = 6):
        return self._engine.retrieve_ancestors(effect, tenant_id, max_hops)

    def ingest(self, cause: str, effect: str, confidence: float,
               source: str, tenant_id: str, mechanism: str = "",
               supersedes: str | None = None) -> str:
        return self._engine.ingest_claim(cause, effect, confidence, source,
                                         tenant_id, mechanism, supersedes)

    def retract(self, claim_id: str, reason: str = "") -> None:
        self._engine.retract_claim(claim_id, reason)

    def path(self, start: str, goal: str, tenant_id: str, max_hops: int = 4):
        return self._engine.retrieve_path(start, goal, tenant_id, max_hops)

    def conflicts(self, tenant_id: str):
        return self._engine.flag_conflicts(tenant_id)
