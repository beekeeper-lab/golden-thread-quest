"""The one documented command that reached outside the repository for its inputs.

`CONTRIBUTING.md` told a contributor to run this script as though it worked anywhere. It
read two stylesheets from a directory on the maintainer's machine and died on a
`FileNotFoundError` for `base.css` on every other one.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parent.parent.parent / "scripts" / "build_user_guide_html.py"


def load(monkeypatch: pytest.MonkeyPatch, snippets: Path) -> object:
    monkeypatch.setenv("GTQ_HTML_SNIPPETS", str(snippets))
    spec = importlib.util.spec_from_file_location("build_user_guide_html", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_without_env(monkeypatch: pytest.MonkeyPatch) -> object:
    monkeypatch.delenv("GTQ_HTML_SNIPPETS", raising=False)
    spec = importlib.util.spec_from_file_location("build_user_guide_html_no_env", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_it_says_what_is_missing_instead_of_raising(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    module = load(monkeypatch, tmp_path / "nowhere")
    assert module.main() == 2  # type: ignore[attr-defined]
    message = capsys.readouterr().err
    assert "base.css" in message and "print.css" in message
    assert "GTQ_HTML_SNIPPETS" in message


def test_the_snippet_directory_is_configurable(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Hard-coded, it named a path that exists on one machine in the world."""
    snippets = tmp_path / "snippets"
    snippets.mkdir()
    (snippets / "base.css").write_text("/* base */\n")
    (snippets / "print.css").write_text("/* print */\n")
    module = load(monkeypatch, snippets)
    assert snippets == module.SKILL  # type: ignore[attr-defined]


def test_there_is_no_fallback_to_a_maintainers_home_directory(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """T2 (round 13): a `pathlib.Path.home() / ".claude/skills/..."` fallback let this script
    "work" only on the one machine that path happens to exist on, and silently — contrary to
    CONTRIBUTING's promise that without the two stylesheets the script says so and stops.
    With `GTQ_HTML_SNIPPETS` unset, `SKILL` must be `None` regardless of what is on the
    machine running the test, and `main()` must stop with its documented message.
    """
    module = load_without_env(monkeypatch)
    assert module.SKILL is None  # type: ignore[attr-defined]
    assert module.main() == 2  # type: ignore[attr-defined]
    message = capsys.readouterr().err
    assert "GTQ_HTML_SNIPPETS" in message
    assert "not set" in message
