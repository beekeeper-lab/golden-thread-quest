"""The ADR-025 rule itself: `tools/check_yaml_safe.py`.

`make yaml-safe` is a pre-commit hook and a CI step, but nothing exercised the tool that
implements it — only the pattern it is built from was ever eyeballed. These tests run the
tool against a fake repository, the same way `tests/security/test_secret_scan_tool.py`
covers `secret_scan.py`.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))

import check_yaml_safe


def _call(method: str, *, extra: str = "") -> str:
    """A fixture line calling `yaml`'s given loader method.

    Built from parts rather than written whole, because this file lives under `tests/`,
    one of the scanner's own search directories, and a literal unsafe call here would flag
    this file too.
    """
    return f"data = yaml.{method}(stream{extra})\n"


def _loader(name: str) -> str:
    return f"loader = yaml.{name}\n"


@pytest.fixture
def fake_repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(check_yaml_safe, "REPO_ROOT", tmp_path)
    for directory in check_yaml_safe.SEARCH_DIRS:
        (tmp_path / directory).mkdir(parents=True, exist_ok=True)
    return tmp_path


def _write(fake_repo: Path, relative: str, text: str) -> Path:
    path = fake_repo / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


def test_safe_load_is_not_flagged(fake_repo: Path) -> None:
    _write(fake_repo, "quest_app/clean.py", _call("safe_load"))
    assert check_yaml_safe.main() == 0


def test_yaml_load_is_flagged(fake_repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    target = _write(fake_repo, "quest_app/bad.py", _call("load"))
    assert check_yaml_safe.main() == 1
    err = capsys.readouterr().err
    assert str(target.relative_to(fake_repo)) in err
    assert "ADR-025" in err


@pytest.mark.parametrize(
    "line",
    [
        _call("unsafe_load"),
        _call("full_load"),
        _loader("Loader"),
        _loader("UnsafeLoader"),
    ],
)
def test_every_unsafe_form_is_flagged(fake_repo: Path, line: str) -> None:
    _write(fake_repo, "validators/bad.py", line)
    assert check_yaml_safe.main() == 1


def test_directories_outside_search_dirs_are_not_scanned(fake_repo: Path) -> None:
    _write(fake_repo, "scripts/bad.py", _call("load"))
    assert check_yaml_safe.main() == 0


def test_the_allowed_file_is_exempt(fake_repo: Path) -> None:
    """`quest_app/yaml_loader.py` is the one audited call site (ADR-025)."""
    (allowed,) = check_yaml_safe.ALLOWED_FILES
    _write(fake_repo, allowed, _call("load", extra=", Loader=StrictSafeLoader"))
    assert check_yaml_safe.main() == 0


def test_the_exemption_is_by_filename_not_by_pattern(fake_repo: Path) -> None:
    """The same unsafe call in a file that is not the named exception still fails."""
    _write(fake_repo, "quest_app/other.py", _call("load", extra=", Loader=StrictSafeLoader"))
    assert check_yaml_safe.main() == 1
