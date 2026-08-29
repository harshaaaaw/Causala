"""Consumer-friendly CAUSALA CLI (zero config, tenant-isolated, audit backed).

Quickstart (30 seconds):
    causala quickstart                 # scaffold demo graph and simulate price +3%
    causala tui                        # dashboard - watch graph, simulate, audit
    causala agent claude "price +3%"   # connect any agent to same ledger

Core:
    causala ingest   --cause X --effect Y --conf 0.8 --source S
    causala explain  --effect Y
    causala whatif   --cause X
    causala ancestors --effect Y
    causala path     --from A --to B
    causala simulate --lever price --delta 3   # lever + delta% -> outcomes + 90% CI + audit
    causala ingest-csv --file warehouse.csv
    causala audit    --id <audit_id>
    causala verify-chain
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

import typer

from . import Causala

app = typer.Typer(help="CAUSALA: decision twin that defends million-dollar calls with citations.")
agent_app = typer.Typer(help="Connect any agent to the same causal ledger.")
skill_app = typer.Typer(help="Install and manage skills grounded to the flow.")
app.add_typer(agent_app, name="agent")
app.add_typer(skill_app, name="skill")


def _engine(db: str | None, tenant: str) -> Causala:
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


# ---- simulate: the business problem ------------------------------------------------

@app.command("simulate")
def simulate(lever: str = typer.Option(..., "--lever"),
             delta: float = typer.Option(..., "--delta", help="percent change, e.g. 3 for +3%"),
             tenant: str = "local", db: str = typer.Option(None, "--db")):
    """Simulate a lever intervention -> outcomes with point + 90% CI + audit."""
    engine = _engine(db, tenant)
    results = engine.simulate(lever, delta, tenant)
    if not results:
        typer.echo(json.dumps({"msg": f"no path from lever {lever!r} - ingest a graph first: causala quickstart"}, indent=2))
        raise typer.Exit(code=0)
    out = []
    for r in results:
        out.append({
            "lever": r.lever, "delta_percent": r.delta_percent, "outcome": r.outcome,
            "point": r.point, "ci_low": r.ci_low, "ci_high": r.ci_high, "ci_width": r.ci_width,
            "confidence": r.confidence, "contested": r.contested,
            "citations": r.citations, "path": r.path,
            "honest_note": r.honest_note, "audit_id": r.audit_id,
        })
    typer.echo(json.dumps(out, indent=2))


@app.command("ingest-csv")
def ingest_csv(file: str = typer.Option(..., "--file", help="path to warehouse csv"),
               tenant: str = "local", db: str = typer.Option(None, "--db"),
               source: str = typer.Option("warehouse-export", "--source")):
    """Bulk ingest a warehouse CSV (cause,effect,confidence,source)."""
    engine = _engine(db, tenant)
    res = engine.ingest_csv(file, tenant, source)
    typer.echo(json.dumps(res, indent=2))


@app.command("audit")
def audit_cmd(id: str = typer.Option(..., "--id", help="audit_id from simulate"),
              tenant: str = "local", db: str = typer.Option(None, "--db")):
    """Fetch a signed audit record."""
    engine = _engine(db, tenant)
    rec = engine.get_audit(id)
    if not rec:
        typer.echo(json.dumps({"error": "audit not found", "audit_id": id}))
        raise typer.Exit(code=1)
    typer.echo(json.dumps(rec, indent=2))


@app.command("verify-chain")
def verify_chain(tenant: str = "local", db: str = typer.Option(None, "--db")):
    """Verify the hash chain integrity of the audit ledger."""
    engine = _engine(db, tenant)
    ok, msg = engine.verify_audit_chain()
    typer.echo(json.dumps({"ok": ok, "msg": msg}, indent=2))
    if not ok:
        raise typer.Exit(code=1)


@app.command("audits")
def audits(tenant: str = "local", db: str = typer.Option(None, "--db"), limit: int = 20):
    """List recent audits for a tenant."""
    engine = _engine(db, tenant)
    rows = engine.recent_audits(tenant, limit)
    typer.echo(json.dumps(rows, indent=2))


# ---- quickstart: the one command that proves the loop ------------------------------

_DEMO_CLAIMS = [
    ("price", "demand", 0.82, "finance-q3-review"),
    ("demand", "margin", 0.75, "finance-q3-review"),
    ("cache_miss", "cost_up", 0.80, "finops-3"),
    ("cost_up", "margin_down", 0.70, "finops-4"),
]


@app.command()
def quickstart(tenant: str = "acme", db: str = typer.Option(None, "--db")):
    """Consumer quickstart: scaffold a demo causal graph, simulate, and show next steps."""
    engine = _engine(db, tenant)
    typer.echo(f"Tenant: {tenant}  DB: {db or str(Path(tempfile.gettempdir()) / f'causala-{tenant}.db')}")
    for cause, effect, conf, source in _DEMO_CLAIMS:
        cid = engine.ingest_claim(cause, effect, conf, source, tenant)
        typer.echo(f"  ingest {cause} -> {effect} {conf} cite {source} -> {cid[:8]}")
    typer.echo("")
    typer.echo("Simulate: price +3% ->")
    results = engine.simulate("price", 3.0, tenant)
    for r in results:
        flag = " CONTESTED" if r.contested else ""
        typer.echo(f"  {r.outcome}: {r.point}%  [{r.ci_low}, {r.ci_high}]  conf {r.confidence}{flag}  audit {r.audit_id[:8]}")
        typer.echo(f"    {r.honest_note}")
        typer.echo(f"    cites: {', '.join(r.citations)}  path: {' -> '.join([p['cause'] for p in r.path] + [r.outcome])}")
    typer.echo("")
    typer.echo("Next:")
    typer.echo("  causala tui                                         # open the dashboard")
    typer.echo('  causala simulate --lever price --delta 3            # re-run the what-if')
    typer.echo('  causala agent claude "price +3% should we do it?"   # connect any agent')
    typer.echo("  causala audit --id <audit_id>                       # hand regulators the receipt")
    typer.echo("  causala skill list                                  # see grounded skills")


@app.command()
def init(tenant: str = "acme", db: str = typer.Option(None, "--db")):
    """Alias for quickstart (like git init)."""
    quickstart(tenant=tenant, db=db)


# ---- TUI ---------------------------------------------------------------------------

@app.command()
def tui():
    """Open the terminal dashboard. Watch graph, simulate, audit live."""
    try:
        from .tui.app import run_tui
    except ImportError as e:
        typer.echo(f"TUI requires textual: pip install textual rich -- error: {e}")
        raise typer.Exit(code=1)
    run_tui()


@app.command()
def watch(tenant: str = "acme", db: str = typer.Option(None, "--db")):
    """Live tail of the audit flow without TUI (plain logs)."""
    import time as _t
    engine = _engine(db, tenant)
    typer.echo(f"Tailing audits for tenant {tenant} (Ctrl+C to stop) -- run causala simulate in another terminal")
    seen = set()
    try:
        while True:
            for rec in engine.recent_audits(tenant, 10):
                aid = rec.get("audit_id")
                if aid not in seen:
                    seen.add(aid)
                    typer.echo(json.dumps({k: rec[k] for k in ("audit_id", "lever", "outcome", "point", "ci_low", "ci_high", "citations")}, indent=0))
            _t.sleep(1.5)
    except KeyboardInterrupt:
        typer.echo("stopped")


@app.command()
def serve(
    host: str = typer.Option("127.0.0.1", "--host", help="bind host"),
    port: int = typer.Option(8000, "--port", help="bind port"),
    tenant: str = typer.Option("acme", "--tenant", help="default tenant for the browser twin"),
    db: str = typer.Option(None, "--db", help="sqlite path (default temp/causala-<tenant>.db)"),
    secret: str = typer.Option(None, "--secret", help="JWT secret, min 32 bytes, or set CAUSALA_SECRET"),
):
    """Serve the browser twin. Open the printed URL in any browser, no build step."""
    import os

    sec = secret or os.environ.get("CAUSALA_SECRET") or "dev-secret-change-me-32chars-minimum-length!!"
    db_path = db or str(Path(tempfile.gettempdir()) / f"causala-{tenant}.db")
    try:
        import uvicorn

        from .server import get_app
    except ImportError as e:
        typer.echo(f"serve requires fastapi + uvicorn: pip install -e ./causala -- error: {e}")
        raise typer.Exit(code=1) from e
    typer.echo(f"CAUSALA browser twin on http://{host}:{port}  tenant {tenant}  db {db_path}")
    typer.echo("Try: ingest a claim in the left pane, then Simulate price +3%. Every result has a receipt.")
    uvicorn.run(get_app(db_path, sec), host=host, port=port, log_level="info")


# ---- any-agent connector -----------------------------------------------------------

@agent_app.command("list")
def agent_list():
    """List agents you can connect to the same causal ledger."""
    import json as _j

    from .agents import list_agents
    typer.echo(_j.dumps(list_agents(), indent=2))


@agent_app.command("claude")
def agent_claude(task: str = typer.Argument(..., help="task for claude"),
                 tenant: str = "acme", db: str = typer.Option(None, "--db")):
    from .agents import run_agent
    res = run_agent("claude", task, tenant=tenant, db_path=db)
    typer.echo(json.dumps({"agent": res.agent, "command": res.command, "exit_code": res.exit_code,
                           "output": res.output[:800], "simulations": res.simulations}, indent=2))


@agent_app.command("codex")
def agent_codex(task: str = typer.Argument(..., help="task for codex"),
                tenant: str = "acme", db: str = typer.Option(None, "--db")):
    from .agents import run_agent
    res = run_agent("codex", task, tenant=tenant, db_path=db)
    typer.echo(json.dumps({"agent": res.agent, "command": res.command, "exit_code": res.exit_code,
                           "output": res.output[:800], "simulations": res.simulations}, indent=2))


@agent_app.command("hermes")
def agent_hermes(task: str = typer.Argument(..., help="task for hermes"),
                 tenant: str = "acme", db: str = typer.Option(None, "--db")):
    from .agents import run_agent
    res = run_agent("hermes", task, tenant=tenant, db_path=db)
    typer.echo(json.dumps({"agent": res.agent, "command": res.command, "exit_code": res.exit_code,
                           "output": res.output[:800], "simulations": res.simulations}, indent=2))


@agent_app.command("openclaw")
def agent_openclaw(task: str = typer.Argument(..., help="task for openclaw"),
                   tenant: str = "acme", db: str = typer.Option(None, "--db")):
    from .agents import run_agent
    res = run_agent("openclaw", task, tenant=tenant, db_path=db)
    typer.echo(json.dumps({"agent": res.agent, "command": res.command, "exit_code": res.exit_code,
                           "output": res.output[:800], "simulations": res.simulations}, indent=2))


@agent_app.command("generic")
def agent_generic(task: str = typer.Argument(..., help="task"),
                  cmd: str = typer.Option(..., "--cmd", help="your CLI, e.g. 'my-agent --flag'"),
                  tenant: str = "acme", db: str = typer.Option(None, "--db")):
    from .agents import run_agent
    res = run_agent("generic", task, tenant=tenant, db_path=db, generic_cmd=cmd)
    typer.echo(json.dumps({"agent": res.agent, "command": res.command, "exit_code": res.exit_code,
                           "output": res.output[:800], "simulations": res.simulations}, indent=2))


# ---- skills -----------------------------------------------------------------------

@skill_app.command("list")
def skill_list():
    """List installed skills and whether they are grounded to the flow."""
    import json as _j

    from .skills import list_skills
    rows = [{"name": s.name, "description": s.description, "objective": s.objective,
             "required": s.required, "enabled": s.enabled, "path": s.path} for s in list_skills()]
    typer.echo(_j.dumps(rows, indent=2))


@skill_app.command("install")
def skill_install(name: str = typer.Argument(..., help="skill name from hub"),
                  source: str = typer.Option(None, "--source", help="local dir to install from")):
    from pathlib import Path as _P

    from .skills import install_skill
    res = install_skill(name, _P(source) if source else None)
    typer.echo(json.dumps(res, indent=2))
    if not res.get("ok"):
        raise typer.Exit(code=1)


@skill_app.command("add")
def skill_add(source: str = typer.Argument(..., help="local skill dir")):
    from pathlib import Path as _P

    from .skills import install_skill
    res = install_skill(_P(source).name, _P(source))
    typer.echo(json.dumps(res, indent=2))


@skill_app.command("verify")
def skill_verify(name: str = typer.Argument(..., help="skill name")):
    from .skills import verify_skill
    typer.echo(json.dumps(verify_skill(name), indent=2))


if __name__ == "__main__":
    app()
