"""Consumer-journey tests for the CAUSALA CLI (closes 0% CLI coverage)."""
from __future__ import annotations

from typer.testing import CliRunner

from causa.cli import app

runner = CliRunner()


def test_cli_ingest_explain_whatif(tmp_path):
    db = str(tmp_path / "causala.db")
    r = runner.invoke(app, ["ingest", "--cause", "flag_on", "--effect", "hotspot",
                            "--conf", "0.8", "--source", "i1", "--tenant", "acme",
                            "--db", db])
    assert r.exit_code == 0, r.output
    assert "claim_id" in r.output
    e = runner.invoke(app, ["explain", "--effect", "hotspot", "--tenant", "acme", "--db", db])
    assert e.exit_code == 0
    assert '"cause": "flag_on"' in e.output
    w = runner.invoke(app, ["whatif", "--cause", "flag_on", "--tenant", "acme", "--db", db])
    assert w.exit_code == 0
    assert '"effect": "hotspot"' in w.output


def test_cli_ancestors_and_conflicts(tmp_path):
    db = str(tmp_path / "causala.db")
    runner.invoke(app, ["ingest", "--cause", "a", "--effect", "b", "--conf", "0.8",
                        "--source", "s1", "--tenant", "acme", "--db", db])
    runner.invoke(app, ["ingest", "--cause", "b", "--effect", "c", "--conf", "0.7",
                        "--source", "s2", "--tenant", "acme", "--db", db])
    a = runner.invoke(app, ["ancestors", "--effect", "c", "--tenant", "acme", "--db", db])
    assert a.exit_code == 0
    assert "a" in a.output and "b" in a.output
    cf = runner.invoke(app, ["conflicts", "--tenant", "acme", "--db", db])
    assert cf.exit_code == 0
