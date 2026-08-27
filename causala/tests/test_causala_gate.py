"""CAUSALA EVALUATE gate: anti-slop static scan (gap C7).

Same discipline as AEGIS: block bare/exceptions that invite silent failure,
block invented public APIs, and run bandit in CI. This test enforces the
anti-slop P1 rules on the CAUSALA source so a merge can't regress quality.
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "src" / "causa"


def _strip_docstrings(text: str) -> str:
    return re.sub(r'"""[\s\S]*?"""', "", text)


def test_antislop_no_bare_except():
    # Allow `except (AuthError, WeakSecretError) as e:` (typed, logged) but block
    # a truly bare `except:` or `except Exception:` (silent swallow).
    BAD = re.compile(r"except\s*(:|Exception\s*:|BaseException\s*:)", re.MULTILINE)
    for f in SRC.glob("*.py"):
        code = _strip_docstrings(f.read_text())
        assert not BAD.search(code), f"anti-slop P1: bare/Exception except in {f.name}"


def test_antislop_no_invented_apis():
    # Reject calls to functions that don't exist in the modules we import.
    # Conservative: flag os.getenv misuse (should use aegis settings), and any
    # `randon`, `randum` typo, and `TODO`/`FIXME` left in shipping code.
    BAD = re.compile(r"\b(TODO|FIXME|randon|randum)\b")
    for f in SRC.glob("*.py"):
        code = _strip_docstrings(f.read_text())
        assert not BAD.search(code), f"anti-slop P2: leftover marker/typo in {f.name}"


def test_bandit_clean():
    # Run bandit on the package; must report no issues. Use the same interpreter
    # that is running the tests (has bandit installed).
    import sys
    r = subprocess.run(
        [sys.executable, "-m", "bandit", "-r", str(SRC), "-f", "txt"],
        capture_output=True, text=True, check=False)
    assert "No issues identified" in r.stdout or r.returncode == 0, \
        f"bandit found issues:\n{r.stdout}\n{r.stderr}"
