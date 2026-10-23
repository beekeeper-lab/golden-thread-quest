"""The shards of a run are disjoint and together cover exactly what one process would run."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
TARGET = "tests/unit/test_state_machine_table.py"


def collected(*extra: str) -> list[str]:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            TARGET,
            "--collect-only",
            "-p",
            "no:cacheprovider",
            *extra,
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    return [line for line in result.stdout.splitlines() if "::" in line]


def test_shards_partition_the_selection_exactly() -> None:
    whole = collected()
    assert len(whole) > 3, "the sample file must have enough tests to split"
    shards = [collected("--shard-count=3", f"--shard-index={i}") for i in range(3)]
    flat = [node for shard in shards for node in shard]
    assert sorted(flat) == sorted(whole), "the shards must cover every test exactly once"
    assert len(flat) == len(set(flat)), "no test may run in two shards"
    assert all(shards), "every shard must receive work"


def test_a_shard_index_outside_the_count_is_refused() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            TARGET,
            "--collect-only",
            "-p",
            "no:cacheprovider",
            "--shard-count=2",
            "--shard-index=2",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0
    assert "--shard-index must be in" in (result.stdout + result.stderr)
