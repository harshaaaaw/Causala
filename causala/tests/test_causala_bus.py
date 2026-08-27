"""Consumer test: CAUSALA subsystem reacts to AEGIS bus causal events (service.py)."""
from __future__ import annotations

import tempfile

from trustcore.backbone import ControlEvent, EventBus, reset_registry

from causa.service import CausalaSubsystem


def test_subsystem_ingests_on_bus_event():
    reset_registry()
    bus = EventBus()
    db = tempfile.mkdtemp() + "/causala.db"
    sub = CausalaSubsystem(db)
    bus.subscribe("causala", sub.handle)
    bus.publish(ControlEvent("causala", kind="causal_ingest",
                             payload={"cause": "x", "effect": "y",
                                      "confidence": 0.9, "source": "s1"},
                             tenant_id="acme"))
    ans = sub._engine.explain_effect("y", "acme")
    assert ans.cause == "x"
    # exercise the convenience delegates (what_if / ancestors / path / conflicts)
    sub.ingest("y", "z", 0.7, "s2", tenant_id="acme")
    assert sub.what_if("x", "acme").effect == "y"
    assert sub.ancestors("z", "acme")[0].cause == "x"  # root of the chain
    assert sub.path("x", "z", "acme")[0].cause == "x"
    assert sub.conflicts("acme") == []  # x->y, y->z are consistent, no conflict
    reset_registry()
