"""The ignore rules actually cover what the security policy requires.

The traceability document pointed this row at the cleanup tests, which only ever *copied*
`.gitignore`. Nothing read it.
"""

from __future__ import annotations

from pathlib import Path

import pytest

REQUIRED = {
    "generated output": ("/generated/",),
    "local runtime data": ("/local-data/",),
    "environment files": (".env",),
    "python caches": ("__pycache__/",),
    "virtual environments": (".venv/",),
    "private keys": ("*.pem", "*.key"),
    "credential files": ("credentials.json",),
    "secret directories": ("**/secrets/",),
}


@pytest.fixture(scope="module")
def rules(repo_root: Path) -> list[str]:
    return [
        line.strip()
        for line in (repo_root / ".gitignore").read_text().splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]


@pytest.mark.parametrize("category", sorted(REQUIRED))
def test_every_required_category_is_ignored(rules: list[str], category: str) -> None:
    patterns = REQUIRED[category]
    assert any(pattern in rules for pattern in patterns), (
        f"nothing ignores {category}; expected one of {patterns}"
    )


def test_the_example_environment_file_is_not_ignored(rules: list[str]) -> None:
    """`.env.*` would otherwise swallow the one file a participant needs to see."""
    assert "!.env.example" in rules
    assert rules.index(".env.*") < rules.index("!.env.example"), "the negation must come after"


def test_generated_output_is_actually_untracked(repo_root: Path) -> None:
    import subprocess

    result = subprocess.run(
        ["git", "-C", str(repo_root), "check-ignore", "-q", "generated/index.html"],
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, "generated/ is not ignored by the working rules"


def test_local_data_is_actually_untracked(repo_root: Path) -> None:
    import subprocess

    result = subprocess.run(
        ["git", "-C", str(repo_root), "check-ignore", "-q", "local-data/cache/x.json"],
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, "local-data/ is not ignored by the working rules"
