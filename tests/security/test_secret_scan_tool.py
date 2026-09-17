"""The repository scanner itself.

The Stage 1 audit found that `make secret-scan` failed on this repository's own test
fixtures, which meant `make check` had never passed and CI had never been green. Nothing
tested the tool, only the patterns underneath it — so these tests cover the tool: what it
scans, what it skips, what the pragma does, and what it exits with.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))

import secret_scan

PLANTED = "ghp_abcdefghijklmnopqrstuvwxyz0123456789"  # secret-scan: allow


@pytest.fixture
def fake_repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(secret_scan, "REPO_ROOT", tmp_path)
    return tmp_path


def test_finds_a_planted_secret(fake_repo: Path) -> None:
    target = fake_repo / "config.py"
    target.write_text(f'TOKEN = "{PLANTED}"\n')
    (match,) = secret_scan.scan_path(target)
    assert match.pattern_id == "github-token"
    assert PLANTED not in match.excerpt


def test_allow_pragma_skips_only_its_own_line(fake_repo: Path) -> None:
    target = fake_repo / "fixtures.py"
    target.write_text(f'ALLOWED = "{PLANTED}"  {secret_scan.ALLOW_PRAGMA}\nLEAKED = "{PLANTED}"\n')
    matches = secret_scan.scan_path(target)
    assert [m.line for m in matches] == [2], "the unmarked line must still fail"


def test_pragma_is_not_honoured_by_the_pure_scanner(fake_repo: Path) -> None:
    """Evidence scanning calls `scan_text` directly, so a participant cannot switch it off.

    This is the reason the pragma lives in the tool and not in `quest_app.secret_patterns`.
    """
    from quest_app.secret_patterns import scan_text

    text = f'TOKEN = "{PLANTED}"  {secret_scan.ALLOW_PRAGMA}\n'
    assert len(scan_text(text)) == 1


def test_generated_and_private_directories_are_not_scanned(fake_repo: Path) -> None:
    for directory in ("generated", "local-data", "node_modules", ".git"):
        path = fake_repo / directory / "leak.txt"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"token={PLANTED}\n")
        assert not secret_scan.eligible(path), f"{directory} should be skipped"


def test_binary_and_oversized_files_are_not_scanned(fake_repo: Path) -> None:
    image = fake_repo / "shot.png"
    image.write_bytes(b"\x89PNG" + PLANTED.encode())
    assert not secret_scan.eligible(image)

    big = fake_repo / "big.log"
    big.write_text("x" * (secret_scan.MAX_BYTES + 1))
    assert not secret_scan.eligible(big)


def test_undecodable_file_is_ignored_rather_than_crashing(fake_repo: Path) -> None:
    target = fake_repo / "data.txt"
    target.write_bytes(b"\xff\xfe\x00binary")
    assert secret_scan.scan_path(target) == []


def test_path_outside_the_repository_does_not_crash(
    fake_repo: Path, tmp_path_factory: pytest.TempPathFactory
) -> None:
    """`secret_scan.py /tmp/x` used to raise ValueError from relative_to()."""
    outside = tmp_path_factory.mktemp("outside") / "note.txt"
    outside.write_text("nothing here\n")
    assert secret_scan.display_path(outside) == str(outside)


def test_exit_code_is_one_when_a_secret_is_found(
    fake_repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    target = fake_repo / "leak.py"
    target.write_text(f'TOKEN = "{PLANTED}"\n')
    assert secret_scan.main([str(target)]) == 1
    assert PLANTED not in capsys.readouterr().out


def test_exit_code_is_zero_for_clean_input(fake_repo: Path) -> None:
    target = fake_repo / "clean.py"
    target.write_text("PORT = 8765\n")
    assert secret_scan.main([str(target)]) == 0


def test_json_output_omits_the_excerpt(fake_repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Machine-readable output is the form most likely to be stored or forwarded."""
    target = fake_repo / "leak.py"
    target.write_text(f'TOKEN = "{PLANTED}"\n')
    secret_scan.main([str(target), "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert payload["findings"][0]["pattern"] == "github-token"
    assert "excerpt" not in payload["findings"][0]
    assert PLANTED not in json.dumps(payload)


@pytest.mark.slow
def test_the_repository_itself_is_clean() -> None:
    """`make check` must pass here, which is exactly what the Stage 1 audit found it did not."""
    repo = Path(__file__).resolve().parents[2]
    result = subprocess.run(
        [sys.executable, "tools/secret_scan.py"],
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout
