"""CAUSALA TUI - decision twin dashboard that feels like Claude Code terminal.

One screen to watch the causal graph, run simulations, and inspect audits.
No browser, just:  causala tui
"""

from __future__ import annotations

from datetime import UTC, datetime

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, DataTable, Header, Log, Static, TabbedContent, TabPane


def _now() -> str:
    return datetime.now(UTC).strftime("%H:%M:%S")


def _demo_events() -> list[dict[str, str]]:
    n = _now()
    return [
        {"time": n, "subsystem": "Graph", "kind": "INGEST", "msg": "price -> demand 0.82 (finance-q3) tenant acme"},
        {"time": n, "subsystem": "Simulate", "kind": "SIM", "msg": "price +3% -> demand -2.4% [-3.1, -1.7] audit 9f3c"},
        {"time": n, "subsystem": "Audit", "kind": "SIGNED", "msg": "audit 9f3c hash-chained prev 0... -> a1b2"},
        {"time": n, "subsystem": "Agent", "kind": "WHATIF", "msg": "claude: cache_miss -> cost_up 0.8 cite finops-3"},
    ]


def _demo_simulations() -> list[dict[str, str]]:
    return [
        {"lever": "price", "delta": "+3%", "outcome": "demand", "point": "-2.4%", "ci": "[-3.1, -1.7]", "audit": "9f3c1a"},
        {"lever": "price", "delta": "+3%", "outcome": "margin", "point": "+0.7%", "ci": "[0.2, 1.2]", "audit": "9f3c1b"},
        {"lever": "headcount", "delta": "+5", "outcome": "burn", "point": "+4.1%", "ci": "[2.8, 5.4]", "audit": "7b2e4d"},
    ]


def _demo_agents() -> list[dict[str, str]]:
    return [
        {"name": "claude", "cmd": "claude --print", "status": "ready", "last": "simulated price +3%"},
        {"name": "codex", "cmd": "codex exec", "status": "ready", "last": "idle"},
        {"name": "hermes", "cmd": "hermes agent", "status": "ready", "last": "connected"},
        {"name": "openclaw", "cmd": "openclaw run", "status": "ready", "last": "idle"},
        {"name": "generic", "cmd": "my-agent --flag", "status": "custom", "last": "use: causala agent generic --cmd '...'"},
    ]


def _demo_skills() -> list[dict[str, str]]:
    return [
        {"name": "causala-simulate", "desc": "Run lever simulation with CI", "status": "enabled *"},
        {"name": "causala-audit", "desc": "Signed audit trail", "status": "enabled *"},
        {"name": "causala-ingest", "desc": "Warehouse CSV ingest", "status": "enabled *"},
        {"name": "causala-explain", "desc": "Why did X happen with citations", "status": "enabled *"},
        {"name": "causala-whatif", "desc": "What if we do X", "status": "enabled"},
        {"name": "causala-ancestors", "desc": "Root cause walk", "status": "enabled"},
    ]


class FlowLog(Log):
    def on_mount(self) -> None:
        self.write_line("[bold cyan]CAUSALA flow - live[/]  [dim]q quit  r refresh  s simulate  a agents[/]")
        for e in _demo_events():
            self.write_line(f"[dim]{e['time']}[/] [cyan]{e['subsystem']}[/] {e['kind']:8} {e['msg']}")
        self.write_line("[dim]-- waiting for next simulate (causala agent ... will appear here) --[/]")


class CausalaTUI(App):
    """Premium TUI: dashboard, graph, simulate, audit, agents, skills."""

    CSS = """
    Header { background: #0a0a0a; color: #f59e0b; }
    #nav { width: 22; background: #111111; }
    #main { background: #0a0a0a; }
    #detail { width: 32; background: #111111; }
    DataTable { height: 1fr; }
    Log { height: 1fr; background: #0a0a0a; }
    Button { margin: 1; }
    """

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Horizontal():
            with Vertical(id="nav"):
                yield Static("[bold]CAUSALA[/]\n[dim]decision twin[/]", id="title")
                yield Button("1 Dashboard", id="b1", variant="primary")
                yield Button("2 Graph", id="b2")
                yield Button("3 Simulate", id="b3")
                yield Button("4 Audit", id="b4")
                yield Button("5 Agents", id="b5")
                yield Button("6 Skills", id="b6")
                yield Static("[dim]c simulate  q quit[/]", id="hint")
            with TabbedContent(id="main", initial="dashboard"):
                with TabPane("Dashboard", id="dashboard"):
                    yield Static("[bold]Board-ready decision twin[/]\n[dim]Lever -> outcome + 90% CI + audit[/]", id="dash-title")
                    dt = DataTable(id="dash-table")
                    dt.add_columns("lever", "delta", "outcome", "point", "CI", "audit")
                    for r in _demo_simulations():
                        dt.add_row(r["lever"], r["delta"], r["outcome"], r["point"], r["ci"], r["audit"])
                    yield dt
                with TabPane("Flow", id="flow"):
                    yield FlowLog(id="flow-log")
                with TabPane("Simulate", id="simulate"):
                    yield Static("[bold]Simulate a lever[/]\n[dim]causala simulate --lever price --delta 3[/]\nResult is point + 90% CI with honest widening on thin data.", id="sim-title")
                    sim = DataTable(id="sim-table")
                    sim.add_columns("outcome", "point", "CI", "confidence", "audit")
                    for r in _demo_simulations():
                        sim.add_row(r["outcome"], r["point"], r["ci"], "0.78", r["audit"])
                    yield sim
                with TabPane("Audit", id="audit"):
                    yield Static("[bold]Audit trail[/]\n[dim]Hash-chained, signed, tenant scoped. Every simulate writes here.[/]", id="audit-title")
                    alog = Log(id="audit-log")
                    yield alog
                with TabPane("Agents", id="agents"):
                    at = DataTable(id="agents-table")
                    at.add_columns("agent", "command", "status", "last")
                    for a in _demo_agents():
                        at.add_row(a["name"], a["cmd"], a["status"], a["last"])
                    yield at
                with TabPane("Skills", id="skills"):
                    st = DataTable(id="skills-table")
                    st.add_columns("skill", "description", "status")
                    for s in _demo_skills():
                        st.add_row(s["name"], s["desc"], s["status"])
                    yield st
            with Vertical(id="detail"):
                yield Static("[bold]Honesty[/]\n[dim]Thin data widens CI.\n<5 claims -> 1.8x\nContested -> 1.2x\nEvery number cites.[/]", id="detail-honesty")
                yield Static("[bold]Graph[/]\n[dim]price -> demand -> margin\ncache_miss -> cost_up\ntenant acme: 4 claims[/]", id="detail-graph")

    def on_mount(self) -> None:
        try:
            alog = self.query_one("#audit-log", Log)
            alog.write_line("[green]audit 9f3c1a[/] price +3% -> demand -2.4% [-3.1,-1.7] prev 0...")
            alog.write_line("[green]audit 9f3c1b[/] price +3% -> margin +0.7% [0.2,1.2] prev a1...")
            alog.write_line("[dim]verify: causala audit --id 9f3c1a[/]")
        except (LookupError, OSError) as exc:
            import logging

            logging.getLogger("causala.tui").debug("audit log init failed: %s", exc)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        mapping = {"b1": "dashboard", "b2": "flow", "b3": "simulate", "b4": "audit", "b5": "agents", "b6": "skills"}
        target = mapping.get(event.button.id or "")
        if target:
            self.query_one("#main", TabbedContent).active = target

    def on_key(self, event) -> None:
        if event.key == "q":
            self.exit()
        elif event.key == "1":
            self.query_one("#main", TabbedContent).active = "dashboard"
        elif event.key == "2":
            self.query_one("#main", TabbedContent).active = "flow"
        elif event.key == "3":
            self.query_one("#main", TabbedContent).active = "simulate"
        elif event.key == "4":
            self.query_one("#main", TabbedContent).active = "audit"
        elif event.key == "5":
            self.query_one("#main", TabbedContent).active = "agents"
        elif event.key == "6":
            self.query_one("#main", TabbedContent).active = "skills"
        elif event.key == "c":
            self.notify("Run: causala simulate --lever price --delta 3", timeout=3)
        elif event.key == "r":
            self.notify("Refreshed", timeout=1)


def run_tui() -> None:
    app = CausalaTUI()
    app.run()
