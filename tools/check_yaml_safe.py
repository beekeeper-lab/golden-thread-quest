"""Enforce ADR-025: YAML is parsed with `safe_load` only.

Ruff cannot express "this call is forbidden in this repository" without a custom plugin, and
the rule matters enough to be checked rather than trusted: authored content and participant
state both arrive through pull requests.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
FORBIDDEN = re.compile(
    r"\byaml\.(?:unsafe_load|full_load|load)\s*\(|\byaml\.Loader\b|\byaml\.UnsafeLoader\b"
)
# The single audited exception: quest_app/yaml_loader.py calls yaml.load with
# StrictSafeLoader, which is SafeLoader plus a duplicate-key check. Naming the file rather
# than pattern-matching the loader keeps the rule impossible to widen by accident.
ALLOWED_FILES = frozenset({"quest_app/yaml_loader.py"})
SEARCH_DIRS = ("quest_app", "validators", "tools", "tests")


def main() -> int:
    findings: list[str] = []
    for directory in SEARCH_DIRS:
        for path in sorted((REPO_ROOT / directory).rglob("*.py")):
            relative = path.relative_to(REPO_ROOT).as_posix()
            if path.name == "check_yaml_safe.py" or relative in ALLOWED_FILES:
                continue
            for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
                if FORBIDDEN.search(line):
                    where = f"{path.relative_to(REPO_ROOT)}:{number}"
                    findings.append(f"{where}: unsafe YAML call — use yaml.safe_load (ADR-025)")
    for finding in findings:
        print(finding, file=sys.stderr)
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
