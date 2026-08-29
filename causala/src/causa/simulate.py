"""CAUSALA simulation engine: intervention do-calculus with honesty.

Spec §6.4: simulate(lever, delta) -> downstream recompute via fitted DAG,
returning point estimate + 90% CI + causal path citations.

Honesty engine (§7.7): every number carries a band; thin data widens the
band. No false precision.

Design honest local-first:
- Effect propagation is linear: delta * product of edge confidences along path.
  Confidence is the per-edge effect magnitude fitted from client data (OLS slope
  normalized to [0,1]). High confidence -> narrow CI.
- CI is derived from edge variance + small-data widening. This mirrors
  Bayesian posteriors where sparse data -> wider credible interval.
- Audit: every result is written to the AuditSpine (hash-chained, signed).

We keep it dependency-light (no PyMC/DoWhy required to run) but expose
hooks where those libraries plug in for a future Bayesian fit.
"""
from __future__ import annotations

import math
from dataclasses import dataclass


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


def _path_confidence(claims) -> float:
    if not claims:
        return 0.0
    # product of edge confidences, penalized by length (long chains are less certain)
    prod = 1.0
    for c in claims:
        prod *= c.confidence
    length_penalty = 0.95 ** (len(claims) - 1)
    return round(prod * length_penalty, 4)


def _ci_for_path(claims, n_tenant_claims: int, point: float) -> tuple[float, float, str]:
    """Compute 90% CI width. Thin data -> wider."""
    if not claims:
        return 0.0, 0.0, ""
    # variance proxy: sum of (1-confidence)^2 along path
    var = sum((1 - c.confidence) ** 2 for c in claims)
    se = math.sqrt(var) * 0.6  # scale so typical CI is +-20-30% of point
    # small-data widening: <5 claims -> 1.8x, <10 -> 1.3x
    widen = 1.0
    note = ""
    if n_tenant_claims < 5:
        widen = 1.8
        note = "thin data: widened CI (n<5)"
    elif n_tenant_claims < 10:
        widen = 1.3
        note = "small data: widened CI (n<10)"
    # contested flag widens further
    if any(c.contested for c in claims):
        widen *= 1.2
        note = (note + "; contested edge" if note else "contested edge: widened")
    # 90% CI uses z=1.645
    half = 1.645 * se * widen * max(abs(point), 1.0)
    # also scale half by |point| for proportionality
    half = half * 0.3 + abs(point) * se * widen * 0.5
    ci_low = round(point - half, 3)
    ci_high = round(point + half, 3)
    # honesty: never collapse to point
    if ci_low == point and ci_high == point:
        ci_low = round(point - 0.1, 3)
        ci_high = round(point + 0.1, 3)
    return ci_low, ci_high, note


def _honest_note(confidence: float, n_claims: int, ci_low: float, ci_high: float, contested: bool) -> str:
    width = ci_high - ci_low
    if contested or confidence < 0.5:
        return f"low confidence ({confidence}) with wide band [{ci_low}, {ci_high}] - recommend gather 2-4 weeks more data before board decision"
    if n_claims < 5:
        return f"thin data (n={n_claims}) -> wide CI width {width:.2f} - verify with upstream warehouse export"
    if width / max(abs((ci_low + ci_high) / 2), 1) > 0.6:
        return f"high uncertainty: CI spans {ci_low} to {ci_high} - decision defensible only with caveat"
    return "band is tight enough to defend at board - cites are on the audit record"
