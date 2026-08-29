"""CAUSALA: causal-inference retrieval over a compiled causal knowledge layer.

v0.3 premium: simulation with 90% CI + honesty engine + signed audit + warehouse ingest,
plus idempotent ingest, retraction, bi-directional traversal, conflict detection,
cached graph, structured logging.

Design (anti-slop + IR-correct):
- Compiled-once knowledge with provenance (source) + confidence.
- Idempotent ingest: same (tenant, cause, effect, source) key never duplicates.
- Correctable: claims can be retracted or superseded (history kept).
- Bi-directional: forward `retrieve_path` AND backward `retrieve_ancestors`.
- Conflict surfacing: a cause with two divergent effects is flagged.
- Tenant isolation: every query scoped by tenant_id.
- No hallucination: answers only from ingested, sourced, active claims.
- Honesty: every simulate returns point + 90% CI + contested flag; thin data widens CI.
- Audit: every simulate writes a hash-chained, HMAC-signed record.
"""
from __future__ import annotations

import hashlib
import itertools
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sqlalchemy import Boolean, Column, Float, Integer, String, Text, create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from trustcore.security import get_logger

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


@dataclass
class SimulationResult:
    lever: str
    delta_percent: float
    outcome: str
    point: float
    ci_low: float
    ci_high: float
    ci_width: float
    confidence: float
    contested: bool
    citations: list[str]
    path: list[dict[str, str]]
    honest_note: str
    audit_id: str


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

    def __init__(self, db_path: str, audit_secret: str | None = None):
        url = f"sqlite:///{Path(db_path).as_posix()}"
        self._engine = create_engine(url)
        Base.metadata.create_all(self._engine)
        self._session = sessionmaker(bind=self._engine, expire_on_commit=False)
        self._graph_cache: dict[str, Any] | None = None  # tenant -> DiGraph
        self._graph_dirty: set[str] = set()
        self._db_path = db_path
        # audit is alongside DB: <db>.audit.jsonl hash-chained, optionally signed
        base = str(Path(db_path).with_suffix("")) + ".audit.jsonl"
        audit_path = base if db_path != ":memory:" else str(
            Path.cwd() / ".causala.audit.jsonl"
        )
        # for :memory: use temp file per instance
        if db_path == ":memory:":
            import tempfile

            audit_path = str(
                Path(tempfile.gettempdir()) / f"causala-{uuid.uuid4().hex[:8]}.audit.jsonl"
            )
        self._audit_secret = audit_secret
        self._audit_path = audit_path
        self._graph_version: dict[str, int] = {}

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
        self._graph_version[tenant_id] = self._graph_version.get(tenant_id, 0) + 1
        log.info("ingest", extra={"tenant": tenant_id, "cause": cause, "effect": effect,
                                  "source": source, "contested": contested})
        return claim_id

    def retract_claim(self, claim_id: str, reason: str = "") -> None:
        with self._session() as s:
            row = s.query(_ClaimRow).filter_by(claim_id=claim_id).first()
            if row:
                row.active = False
                self._graph_dirty.add(row.tenant_id)
                self._graph_version[row.tenant_id] = self._graph_version.get(row.tenant_id, 0) + 1
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

    # ---- simulation with honesty + audit (core business problem) --------------

    def simulate(self, lever: str, delta_percent: float, tenant_id: str) -> list[SimulationResult]:
        """Do-calculus: lever +delta% -> downstream outcomes with point + 90% CI.

        Each reachable outcome is recomputed via the cited causal path.
        Honesty: thin data widens CI; contested edges widen further.
        Audit: every outcome writes a hash-chained signed record.
        """
        from .audit import AuditSpine
        from .simulate import _ci_for_path, _honest_note, _path_confidence

        g = self._graph(tenant_id)
        if lever not in g:
            return []
        # count tenant claims for small-data widening
        with self._session() as s:
            n_claims = s.query(_ClaimRow).filter_by(tenant_id=tenant_id, active=True).count()
        audit = AuditSpine(self._audit_path, self._audit_secret)
        graph_ver = self._graph_version.get(tenant_id, 0)
        results: list[SimulationResult] = []
        # BFS to find all reachable outcomes with shortest path
        import networkx as nx
        for outcome in g.nodes:
            if outcome == lever:
                continue
            try:
                path_nodes = nx.shortest_path(g, lever, outcome)
            except (nx.NetworkXNoPath, nx.NodeNotFound):
                continue
            # collect claims along path
            claims = []
            path_dicts: list[dict[str, str]] = []
            for a, b in itertools.pairwise(path_nodes):
                cl = g.get_edge_data(a, b)["claim"]
                claims.append(cl)
                path_dicts.append({"cause": a, "effect": b, "source": cl.source, "confidence": str(cl.confidence)})
            path_conf = _path_confidence(claims)
            # point: delta scaled by path confidence product (direction sign preserved)
            point = round(delta_percent * path_conf, 3)
            # CI
            ci_low, ci_high, widen_note = _ci_for_path(claims, n_claims, point)
            ci_width = round(ci_high - ci_low, 3)
            contested = any(c.contested for c in claims) or path_conf < 0.5
            honest = _honest_note(path_conf, n_claims, ci_low, ci_high, contested)
            if widen_note:
                honest = f"{honest} ({widen_note})"
            citations = list({c.source for c in claims})
            # audit trail per outcome
            rec = audit.record(
                tenant_id=tenant_id,
                lever=lever,
                delta_percent=delta_percent,
                outcome=outcome,
                point=point,
                ci_low=ci_low,
                ci_high=ci_high,
                confidence=path_conf,
                contested=contested,
                citations=citations,
                path=path_dicts,
                graph_version=graph_ver,
            )
            results.append(SimulationResult(
                lever=lever,
                delta_percent=delta_percent,
                outcome=outcome,
                point=point,
                ci_low=ci_low,
                ci_high=ci_high,
                ci_width=ci_width,
                confidence=path_conf,
                contested=contested,
                citations=citations,
                path=path_dicts,
                honest_note=honest,
                audit_id=rec.audit_id,
            ))
        # sort most confident first
        return sorted(results, key=lambda r: r.confidence, reverse=True)

    def get_audit(self, audit_id: str) -> dict[str, Any] | None:
        from .audit import AuditSpine
        audit = AuditSpine(self._audit_path, self._audit_secret)
        return audit.get(audit_id)

    def verify_audit_chain(self) -> tuple[bool, str]:
        from .audit import AuditSpine
        audit = AuditSpine(self._audit_path, self._audit_secret)
        return audit.verify_chain()

    def recent_audits(self, tenant_id: str, limit: int = 20) -> list[dict[str, Any]]:
        from .audit import AuditSpine
        audit = AuditSpine(self._audit_path, self._audit_secret)
        return audit.list_recent(tenant_id, limit)

    def ingest_csv(self, csv_path: str, tenant_id: str, default_source: str = "warehouse-export") -> dict[str, Any]:
        from .ingest import ingest_csv
        return ingest_csv(self, csv_path, tenant_id, default_source)

    def ingest_json(self, json_path: str, tenant_id: str) -> dict[str, Any]:
        from .ingest import ingest_json
        return ingest_json(self, json_path, tenant_id)

    # alias for ergonomics: engine.ingest(...) == ingest_claim
    ingest = ingest_claim

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
        """Backward ancestry walk: every root cause of `effect`, cite-backed."""
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
