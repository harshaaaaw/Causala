"""CAUSALA audit trail: signed, hash-chained ledger per simulation.

Every simulate() emits one record per outcome, with the lever, delta,
outcome + CI, causal path citations, graph version, and signer. The
record is HMAC-signed (when a secret is supplied) and hash-chained
(prev_hash = sha256 of previous line) so tampering is detectable.
Local-first: JSONL alongside the DB. Production: S3 + Postgres.

Anti-slop: externalized state (file, not memory), idempotent verify,
no bare except, typed errors.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class AuditRecord:
    audit_id: str
    tenant_id: str
    lever: str
    delta_percent: float
    outcome: str
    point: float
    ci_low: float
    ci_high: float
    confidence: float
    contested: bool
    citations: list[str]
    path: list[dict[str, Any]]
    graph_version: int
    prev_hash: str
    signature: str
    issued_at: int


class AuditSpine:
    """Hash-chained, optionally HMAC-signed audit ledger."""

    def __init__(self, ledger_path: str, signing_secret: str | None = None):
        self.ledger = Path(ledger_path)
        self.ledger.parent.mkdir(parents=True, exist_ok=True)
        self._key = signing_secret.encode() if signing_secret else None

    def _prev_hash(self) -> str:
        if not self.ledger.exists():
            return "0" * 64
        try:
            last = self.ledger.read_text(encoding="utf-8").strip().splitlines()[-1]
            rec = json.loads(last)
            canon = json.dumps(rec, sort_keys=True, separators=(",", ":"))
            return hashlib.sha256(canon.encode()).hexdigest()
        except (IndexError, json.JSONDecodeError, FileNotFoundError):
            return "0" * 64

    def _sign(self, payload: dict[str, Any]) -> str:
        if not self._key:
            canon = json.dumps(payload, sort_keys=True, separators=(",", ":"))
            return hashlib.sha256(canon.encode()).hexdigest()[:32]
        canon = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hmac.new(self._key, canon.encode(), hashlib.sha256).hexdigest()[:32]

    def record(
        self,
        tenant_id: str,
        lever: str,
        delta_percent: float,
        outcome: str,
        point: float,
        ci_low: float,
        ci_high: float,
        confidence: float,
        contested: bool,
        citations: list[str],
        path: list[dict[str, Any]],
        graph_version: int = 0,
    ) -> AuditRecord:
        audit_id = uuid.uuid4().hex[:16]
        prev = self._prev_hash()
        payload = {
            "audit_id": audit_id,
            "tenant_id": tenant_id,
            "lever": lever,
            "delta_percent": delta_percent,
            "outcome": outcome,
            "point": point,
            "ci_low": ci_low,
            "ci_high": ci_high,
            "confidence": confidence,
            "contested": contested,
            "citations": citations,
            "path": path,
            "graph_version": graph_version,
            "prev_hash": prev,
            "issued_at": int(time.time()),
        }
        sig = self._sign(payload)
        payload["signature"] = sig
        with open(self.ledger, "a", encoding="utf-8") as f:
            f.write(json.dumps(payload, sort_keys=True) + "\n")
        return AuditRecord(
            audit_id=audit_id,
            tenant_id=tenant_id,
            lever=lever,
            delta_percent=delta_percent,
            outcome=outcome,
            point=point,
            ci_low=ci_low,
            ci_high=ci_high,
            confidence=confidence,
            contested=contested,
            citations=citations,
            path=path,
            graph_version=graph_version,
            prev_hash=prev,
            signature=sig,
            issued_at=payload["issued_at"],
        )

    def get(self, audit_id: str) -> dict[str, Any] | None:
        if not self.ledger.exists():
            return None
        for line in self.ledger.read_text(encoding="utf-8").splitlines():
            try:
                rec = json.loads(line)
                if rec.get("audit_id") == audit_id:
                    return rec
            except json.JSONDecodeError:
                continue
        return None

    def verify_chain(self) -> tuple[bool, str]:
        if not self.ledger.exists():
            return True, "empty"
        prev = "0" * 64
        for i, line in enumerate(self.ledger.read_text(encoding="utf-8").splitlines()):
            if not line.strip():
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError as e:
                return False, f"line {i}: bad json {e}"
            if rec.get("prev_hash") != prev:
                return False, f"line {i}: prev_hash mismatch"
            # recompute next prev
            canon = json.dumps(rec, sort_keys=True, separators=(",", ":"))
            prev = hashlib.sha256(canon.encode()).hexdigest()
        return True, f"chain ok ({i+1} records)"

    def list_recent(self, tenant_id: str, limit: int = 20) -> list[dict[str, Any]]:
        if not self.ledger.exists():
            return []
        out = []
        for line in reversed(self.ledger.read_text(encoding="utf-8").splitlines()):
            if not line.strip():
                continue
            try:
                rec = json.loads(line)
                if rec.get("tenant_id") == tenant_id:
                    out.append(rec)
                    if len(out) >= limit:
                        break
            except json.JSONDecodeError:
                continue
        return out
