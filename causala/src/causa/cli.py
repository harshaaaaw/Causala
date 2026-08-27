"""Consumer-friendly CAUSALA CLI (zero config, tenant-isolated by --db)."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

import typer

from . import Causala

app = typer.Typer(help="CAUSALA: causal-inference retrieval over a compiled causal layer.")


def _engine(db: str | None, tenant: str) -> Causala:
    # default to a tenant-scoped file so isolation is real, not shared OS-temp
    path = db or str(Path(tempfile.gettempdir()) / f"causala-{tenant}.db")
    return Causala(path)


@app.command()
def ingest(cause: str = typer.Option(..., "--cause"),
          effect: str = typer.Option(..., "--effect"),
          conf: float = typer.Option(..., "--conf"),
          source: str = typer.Option(..., "--source"),
          tenant: str = "local", mechanism: str = "",
          db: str = typer.Option(None, "--db")):
    cid = _engine(db, tenant).ingest_claim(cause, effect, conf, source, tenant, mechanism)
    typer.echo(json.dumps({"claim_id": cid, "cause": cause, "effect": effect,
                           "confidence": conf, "source": source}, indent=2))


@app.command("explain")
def explain(effect: str = typer.Option(..., "--effect"),
            tenant: str = "local", db: str = typer.Option(None, "--db")):
    ans = _engine(db, tenant).explain_effect(effect, tenant)
    typer.echo(json.dumps({"cause": ans.cause, "effect": ans.effect,
                           "confidence": ans.confidence, "citations": ans.citations,
                           "contested": ans.contested}, indent=2))


@app.command("whatif")
def whatif(cause: str = typer.Option(..., "--cause"),
           tenant: str = "local", db: str = typer.Option(None, "--db")):
    ans = _engine(db, tenant).what_if_cause(cause, tenant)
    typer.echo(json.dumps({"cause": ans.cause, "effect": ans.effect,
                           "confidence": ans.confidence, "citations": ans.citations}, indent=2))


@app.command("ancestors")
def ancestors(effect: str = typer.Option(..., "--effect"),
              tenant: str = "local", db: str = typer.Option(None, "--db"),
              max_hops: int = 6):
    chain = _engine(db, tenant).retrieve_ancestors(effect, tenant, max_hops)
    typer.echo(json.dumps(
        [{"cause": c.cause, "effect": c.effect, "confidence": c.confidence,
          "source": c.source} for c in chain], indent=2))


@app.command("path")
def path(from_: str = typer.Option(..., "--from"), to: str = typer.Option(..., "--to"),
         tenant: str = "local", db: str = typer.Option(None, "--db"), max_hops: int = 4):
    chain = _engine(db, tenant).retrieve_path(from_, to, tenant, max_hops)
    typer.echo(json.dumps(
        [{"cause": c.cause, "effect": c.effect, "confidence": c.confidence,
          "source": c.source} for c in chain], indent=2))


@app.command("conflicts")
def conflicts(tenant: str = "local", db: str = typer.Option(None, "--db")):
    out = _engine(db, tenant).flag_conflicts(tenant)
    rows = [{"cause": a, "effect_a": b, "effect_b": c} for a, b, c in out]
    typer.echo(json.dumps(rows, indent=2))


if __name__ == "__main__":
    app()
