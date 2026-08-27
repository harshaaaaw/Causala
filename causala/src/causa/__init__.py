"""CAUSALA: causal-inference retrieval over a compiled causal knowledge layer.

v0.2 production-grade: idempotent ingest, claim retraction/supersession,
bi-directional traversal (forward path + backward ancestry), conflict detection,
cached graph, structured logging. Reuses AEGIS security logging.

Design (anti-slop + IR-correct): - Compiled-once knowledge with provenance (source) + confidence. - Idempotent ingest: same (tenant, cause, effect, source) key never duplicates. - Correctable: claims can be retracted (soft-delete) or superseded (history kept). - Bi-directional: forward `retrieve_path` (cause->effect) AND backward
  `retrieve_ancestors` (effect->root causes). Both citation-backed. - Conflict surfacing: a cause with two divergent effects is flagged, not hidden. - Tenant isolation: every query scoped by tenant_id; idempotency key includes it. - No hallucination: answers only from ingested, sourced, active claims.
"""
from __future__ import annotations

import hashlib
import itertools
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from trustcore.security import get_logger
from sqlalchemy import Boolean, Column, Float, Integer, String, Text, create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

log = get_logger("causala.engine")


@dataclass
class CausalClaim:
    claim_id: str
    cause: str
    effect: str
    confidence: float
    source: str
    tenant_id: str
    mechanism: str = ""
    contested: bool = False
    active: bool = True
    supersedes: str | None = None
    created_at: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "claim_id": self.claim_id, "cause": self.cause, "effect": self.effect,
            "confidence": self.confidence, "source": self.source,
            "tenant_id": self.tenant_id, "mechanism": self.mechanism,
            "contested": self.contested, "active": self.active,
            "supersedes": self.supersedes, "created_at": self.created_at,
        }


@dataclass
class CausalAnswer:
    query: str
    mode: str
    cause: str | None
    effect: str | None
    confidence: float
    citations: list[str]
    contested: bool


class Base(DeclarativeBase):
    pass


class _ClaimRow(Base):
    __tablename__ = "causal_claims"
    id = Column(Integer, primary_key=True)
    claim_id = Column(String(40), unique=True, nullable=False, index=True)
    idem_key = Column(String(64), unique=True, nullable=False, index=True)
    cause = Column(String(256), nullable=False, index=True)
    effect = Column(String(256), nullable=False, index=True)
    confidence = Column(Float, nullable=False)
    source = Column(String(256), nullable=False)
    tenant_id = Column(String(64), nullable=False, index=True)
    mechanism = Column(Text, default="")
    contested = Column(Boolean, default=False)
    active = Column(Boolean, default=True)
    supersedes = Column(String(40), nullable=True)
    created_at = Column(Float, nullable=False)


class Causala:
    CONFIDENCE_FLOOR = 0.5

    def __init__(self, db_path: str):
        url = f"sqlite:///{Path(db_path).as_posix()}"
        self._engine = create_engine(url)
        Base.metadata.create_all(self._engine)
        self._session = sessionmaker(bind=self._engine, expire_on_commit=False)
        self._graph_cache: dict[str, Any] | None = None  # tenant -> DiGraph
        self._graph_dirty: set[str] = set()

    # ---- ingest (compile once, idempotent) -----------------------------------
    def ingest_claim(self, cause: str, effect: str, confidence: float,
                     source: str, tenant_id: str, mechanism: str = "",
                     supersedes: str | None = None) -> str:
        if not (0.0 <= confidence <= 1.0):
            raise ValueError("confidence must be in [0,1]")
        if not source:
            raise ValueError("source (provenance) is required; no unattributed claims")
        idem = hashlib.sha256(
            f"{tenant_id}|{cause}|{effect}|{source}".encode()).hexdigest()[:32]
        contested = confidence < self.CONFIDENCE_FLOOR
        with self._session() as s:
            existing = s.query(_ClaimRow).filter_by(idem_key=idem).first()
            if existing:
                log.info("ingest_idempotent_hit", extra={"tenant": tenant_id, "cause": cause})
                return existing.claim_id
            claim_id = uuid.uuid4().hex[:16]
            s.add(_ClaimRow(
                claim_id=claim_id, idem_key=idem, cause=cause, effect=effect,
                confidence=confidence, source=source, tenant_id=tenant_id,
                mechanism=mechanism, contested=contested, active=True,
                supersedes=supersedes, created_at=time.time()))
            s.commit()
        self._graph_dirty.add(tenant_id)
        log.info("ingest", extra={"tenant": tenant_id, "cause": cause, "effect": effect,
                                  "source": source, "contested": contested})
        return claim_id

    def retract_claim(self, claim_id: str, reason: str = "") -> None:
        with self._session() as s:
            row = s.query(_ClaimRow).filter_by(claim_id=claim_id).first()
            if row:
                row.active = False
                self._graph_dirty.add(row.tenant_id)
                s.commit()
                log.info("retract", extra={"claim_id": claim_id, "reason": reason})

    def get_claim(self, claim_id: str) -> CausalClaim | None:
        with self._session() as s:
            row = s.query(_ClaimRow).filter_by(claim_id=claim_id, active=True).first()
            return self._row_to_claim(row) if row else None

    # ---- retrieval (cite-backed) ---------------------------------------------
    def retrieve_causes(self, effect: str, tenant_id: str) -> list[CausalClaim]:
        with self._session() as s:
            rows = (s.query(_ClaimRow).filter_by(effect=effect, tenant_id=tenant_id,
                                                 active=True).all())
            return [self._row_to_claim(r) for r in rows]

    def retrieve_effects(self, cause: str, tenant_id: str) -> list[CausalClaim]:
        with self._session() as s:
            rows = (s.query(_ClaimRow).filter_by(cause=cause, tenant_id=tenant_id,
                                                 active=True).all())
            return [self._row_to_claim(r) for r in rows]

    def explain_effect(self, effect: str, tenant_id: str) -> CausalAnswer:
        causes = self.retrieve_causes(effect, tenant_id)
        if not causes:
            return CausalAnswer(f"effect={effect}", "explain", None, None, 0.0, [], False)
        top = max(causes, key=lambda c: c.confidence)
        return CausalAnswer(
            query=f"effect={effect}", mode="explain", cause=top.cause, effect=top.effect,
            confidence=top.confidence, citations=[top.source], contested=top.contested)

    def what_if_cause(self, cause: str, tenant_id: str) -> CausalAnswer:
        effects = self.retrieve_effects(cause, tenant_id)
        if not effects:
            return CausalAnswer(f"cause={cause}", "what_if", None, None, 0.0, [], False)
        top = max(effects, key=lambda c: c.confidence)
        return CausalAnswer(
            query=f"cause={cause}", mode="what_if", cause=top.cause, effect=top.effect,
            confidence=top.confidence, citations=[top.source], contested=top.contested)

    def explain(self, query: str, tenant_id: str) -> CausalAnswer:
        return self.explain_effect(self._extract_key(query), tenant_id)

    def what_if(self, query: str, tenant_id: str) -> CausalAnswer:
        return self.what_if_cause(self._extract_key(query), tenant_id)

    # ---- graph traversal ------------------------------------------------------
    def _graph(self, tenant_id: str):
        import networkx as nx
        if tenant_id in self._graph_dirty or self._graph_cache is None \
                or tenant_id not in self._graph_cache:
            g = nx.DiGraph()
            with self._session() as s:
                rows = s.query(_ClaimRow).filter_by(tenant_id=tenant_id, active=True).all()
                for r in rows:
                    cl = self._row_to_claim(r)
                    g.add_edge(cl.cause, cl.effect, claim=cl)
            if self._graph_cache is None:
                self._graph_cache = {}
            self._graph_cache[tenant_id] = g
            self._graph_dirty.discard(tenant_id)
        return self._graph_cache[tenant_id]

    def retrieve_path(self, start: str, goal: str, tenant_id: str,
                      max_hops: int = 4) -> list[CausalClaim]:
        """Forward causal chain cause->effect (shortest, cite-backed)."""
        import networkx as nx
        g = self._graph(tenant_id)
        if start not in g or goal not in g:
            return []
        try:
            nodes = nx.shortest_path(g, start, goal)
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return []
        if len(nodes) - 1 > max_hops:
            return []
        return [g.get_edge_data(a, b)["claim"] for a, b in itertools.pairwise(nodes)]

    def retrieve_ancestors(self, effect: str, tenant_id: str,
                           max_hops: int = 6) -> list[CausalClaim]:
        """Backward ancestry walk: every root cause of `effect`, cite-backed.

        Returns the union of all edges on all simple paths that END at `effect`.
        This is the real 'why did X happen?' - it surfaces every upstream cause,
        not just a single hop.
        """
        import networkx as nx
        g = self._graph(tenant_id)
        if effect not in g:
            return []
        chain: list[CausalClaim] = []
        seen: set[tuple[str, str]] = set()
        for src in g.nodes:
            if src == effect:
                continue
            try:
                for p in nx.all_simple_paths(g, src, effect):
                    if len(p) - 1 > max_hops:
                        continue
                    for a, b in itertools.pairwise(p):
                        key = (a, b)
                        if key in seen:
                            continue
                        seen.add(key)
                        chain.append(g.get_edge_data(a, b)["claim"])
            except nx.NetworkXNoPath:
                continue
        # highest confidence first
        return sorted(chain, key=lambda c: c.confidence, reverse=True)

    def flag_conflicts(self, tenant_id: str) -> list[tuple[str, str, str]]:
        """Surface causes with >1 divergent active effect (e.g. A->{B,C})."""
        from collections import defaultdict
        by_cause: dict[str, list[str]] = defaultdict(list)
        with self._session() as s:
            rows = s.query(_ClaimRow).filter_by(tenant_id=tenant_id, active=True).all()
            for r in rows:
                by_cause[r.cause].append(r.effect)
        out = []
        for cause, effects in by_cause.items():
            uniq = sorted(set(effects))
            if len(uniq) > 1:
                # report every conflicting pair
                for i in range(len(uniq)):
                    for j in range(i + 1, len(uniq)):
                        out.append((cause, uniq[i], uniq[j]))
        return out

    # ---- internals ------------------------------------------------------------
    @staticmethod
    def _row_to_claim(r: _ClaimRow) -> CausalClaim:
        return CausalClaim(
            claim_id=r.claim_id, cause=r.cause, effect=r.effect,
            confidence=r.confidence, source=r.source, tenant_id=r.tenant_id,
            mechanism=r.mechanism or "", contested=bool(r.contested),
            active=bool(r.active), supersedes=r.supersedes,
            created_at=r.created_at)

    @staticmethod
    def _extract_key(query: str) -> str:
        stop = {"why", "did", "the", "service", "happen", "if", "we", "do",
                "what", "happens", "to", "enable", "enabling", "a", "an", "of",
                "does", "will", "in", "on", "and", "or", "?", "!"}
        toks = [t for t in query.lower().replace("?", " ").split() if t not in stop]
        return " ".join(toks)
