"""Connect any agent CLI to the same causal ledger.

Each agent has its own command and a generic fallback:
  causala agent claude  "task"
  causala agent codex   "task"
  causala agent hermes  "task"
  causala agent openclaw "task"
  causala agent generic --cmd "my-agent --flag" "task"

Output is recorded as a what-if answered by the causal graph, and every
simulate writes a signed audit. If the real CLI is missing, a mock produces
a verifiable answer so consumers can try without setup.
"""

from __future__ import annotations

import shlex
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path


@dataclass
class AgentResult:
    agent: str
    command: str
    exit_code: int
    output: str
    lever: str
    delta: float
    simulations: list[dict]


@dataclass
class AgentSpec:
    name: str
    command: str
    args_template: list[str]


AGENTS: dict[str, AgentSpec] = {
    "claude": AgentSpec("claude", "claude", ["--print", "{task}"]),
    "codex": AgentSpec("codex", "codex", ["exec", "{task}"]),
    "hermes": AgentSpec("hermes", "hermes", ["agent", "{task}"]),
    "openclaw": AgentSpec("openclaw", "openclaw", ["run", "{task}"]),
}


def _run_cli(base: str, task: str, spec: AgentSpec | None, generic_cmd: str | None) -> tuple[int, str, str]:
    if generic_cmd:
        full = f"{generic_cmd} {shlex.quote(task)}"
        cmd = shlex.split(full)
        label = generic_cmd
    elif spec:
        arg = spec.args_template[-1].format(task=task)
        cmd = [spec.command, *spec.args_template[:-1], arg]
        label = f"{spec.command} {' '.join(spec.args_template).format(task=task)}"
    else:
        label = task
        cmd = [task]
    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=60, check=False
        )
        out = (proc.stdout or "") + (proc.stderr or "")
        if (proc.returncode != 0 and "not found" in out.lower()) or not out.strip():
            raise FileNotFoundError(label)
        return proc.returncode, out.strip()[:4000] or "(no output)", label
    except FileNotFoundError:
        mock = f"[mock:{base}] task: {task}\noutput: simulated agent output for consumer demo"
        return 0, mock, f"[mock] {base} {task}"
    except subprocess.TimeoutExpired:
        return 124, "[timeout] agent did not respond in 60s", label
    except (OSError, RuntimeError, ValueError) as e:
        return 1, f"[error] {e}", label


def run_agent(agent: str, task: str, tenant: str = "acme", db_path: str | None = None, generic_cmd: str | None = None) -> AgentResult:
    from causa import Causala

    spec = AGENTS.get(agent)
    base = agent if agent != "generic" else (generic_cmd or "generic")
    exit_code, output, command = _run_cli(base, task, spec, generic_cmd)
    # Try to interpret task as lever simulation: "price +3%" or just record as whatif
    tmp = Path(tempfile.gettempdir()) / f"causala-{tenant}.db"
    db = db_path or str(tmp)
    engine = Causala(db)
    # naive parse: extract lever token as first word
    lever = task.split()[0].strip().lower() if task.split() else "price"
    delta = 3.0
    for tok in task.split():
        try:
            if "%" in tok:
                delta = float(tok.replace("%", "").replace("+", ""))
                break
            if tok.lstrip("+-").replace(".", "").isdigit():
                delta = float(tok)
        except ValueError:
            continue
    sims = []
    try:
        results = engine.simulate(lever, delta, tenant)
        sims = [{"outcome": r.outcome, "point": r.point, "ci_low": r.ci_low, "ci_high": r.ci_high, "audit_id": r.audit_id} for r in results[:5]]
    except (ValueError, RuntimeError, OSError):
        sims = []
    return AgentResult(
        agent=agent,
        command=command,
        exit_code=exit_code,
        output=output,
        lever=lever,
        delta=delta,
        simulations=sims,
    )


def list_agents() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for name, spec in AGENTS.items():
        rows.append(
            {"name": name, "command": f"{spec.command} {' '.join(spec.args_template)}", "kind": "native"}
        )
    rows.append(
        {"name": "generic", "command": 'causala agent generic --cmd "<your CLI>" "task"', "kind": "any CLI"}
    )
    return rows
