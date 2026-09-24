"""The Makefile declares no variable it does not use.

`PYTHON ?= python3` sat unused beside `setup`, which called `uv venv` with no `--python` at
all (T2). A variable nobody reads is not configuration, it is a promise the Makefile does not
keep, and the next person to set `PYTHON=3.12` on the command line would have gotten no
change and no warning.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
MAKEFILE = REPO_ROOT / "Makefile"

# `NAME ?= value`, `NAME := value` or `NAME = value` at the start of a line.
DECLARATION = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)\s*(?:\?=|:=|=)", re.MULTILINE)


def test_every_declared_variable_is_referenced() -> None:
    text = MAKEFILE.read_text(encoding="utf-8")
    declared = DECLARATION.findall(text)
    assert declared, "the pattern matched nothing; the Makefile's variable syntax changed"
    unused = [name for name in declared if f"$({name})" not in text]
    assert not unused, f"Makefile declares variable(s) nothing reads: {unused}"
