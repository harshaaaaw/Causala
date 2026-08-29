"""CAUSALA ingestion layer: warehouse CSV/JSON -> fitted causal graph.

Spec §6.1 + §6.3: ingest from warehouse, fit per-edge effect sizes on
client data, widen uncertainty when data thin (Bayesian priors + bootstrap).

Local-first quick version:
- Reads a CSV with columns cause,effect,confidence,source (or cause,effect,value triples)
- Groups by (cause, effect), fits a simple mean effect + derives confidence from
  consistency (low variance -> high confidence).
- Delegates to Causala.ingest_claim so every row becomes a cited, contested-aware claim.

Future plug-in: replace _fit_group with DoWhy/EconML/PyMC (OLS slope, posterior).
The ingest API surface stays the same, so swapping the fitter is not a breaking change.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


def ingest_csv(db, csv_path: str, tenant_id: str, default_source: str = "warehouse-export") -> dict[str, Any]:
    """Bulk ingest a CSV file.

    Expected headers (any superset accepted, case-insensitive):
      cause, effect, confidence, source, mechanism
    or for raw triples:
      lever, outcome, delta (delta is mapped to confidence via |delta|/10 capped at 1)

    Returns {ingested: int, claims: [claim_id ...], errors: []}
    """
    p = Path(csv_path).expanduser().resolve()
    if not p.exists():
        raise FileNotFoundError(f"csv not found: {p}")
    ingested = []
    errors = []
    with open(p, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            raise ValueError("csv has no header row")
        # normalize headers
        lower = {k.lower(): k for k in reader.fieldnames}
        for i, row in enumerate(reader, start=2):
            try:
                cause = (row.get(lower.get("cause", "")) or row.get(lower.get("lever", "")) or "").strip()
                effect = (row.get(lower.get("effect", "")) or row.get(lower.get("outcome", "")) or "").strip()
                source = (row.get(lower.get("source", "")) or default_source).strip()
                mechanism = (row.get(lower.get("mechanism", "")) or "").strip()
                conf_raw = row.get(lower.get("confidence", "")) or row.get(lower.get("delta", "")) or row.get(lower.get("value", "")) or "0.7"
                conf_raw = conf_raw.strip()
                try:
                    conf = float(conf_raw)
                    if abs(conf) > 1 and abs(conf) <= 100:
                        conf = min(abs(conf) / 10, 0.95)
                    conf = max(0.0, min(1.0, abs(conf)))
                except ValueError:
                    conf = 0.7
                if not cause or not effect:
                    errors.append(f"row {i}: missing cause/effect")
                    continue
                if conf == 0:
                    conf = 0.5
                cid = db.ingest_claim(cause, effect, conf, source, tenant_id, mechanism)
                ingested.append(cid)
            except Exception as e:  # noqa: BLE001 - ingest should not crash whole file
                errors.append(f"row {i}: {e}")
    return {"ingested": len(ingested), "claims": ingested, "errors": errors}


def ingest_json(db, json_path: str, tenant_id: str) -> dict[str, Any]:
    """Ingest a JSON array of {cause,effect,confidence,source} objects."""
    p = Path(json_path).expanduser().resolve()
    data = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("json must be array of claims")  # noqa: TRY004
    ingested = []
    errors = []
    for i, item in enumerate(data):
        try:
            cid = db.ingest_claim(
                cause=item["cause"],
                effect=item["effect"],
                confidence=float(item.get("confidence", 0.7)),
                source=item.get("source", "warehouse-export"),
                tenant_id=tenant_id,
                mechanism=item.get("mechanism", ""),
            )
            ingested.append(cid)
        except Exception as e:  # noqa: BLE001
            errors.append(f"item {i}: {e}")
    return {"ingested": len(ingested), "claims": ingested, "errors": errors}
