"""The Forge runner keeps the model and push access apart; the CLI model is boxed in (ADR-047)."""

from __future__ import annotations

import json
import stat
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
from test_cli_actions import ROOT

sys.path.insert(0, str(ROOT / "tools"))

import ai_review as ai
import forge_review as forge


def _fake_claude(bin_dir: Path, body: str) -> Path:
    """A `claude` that records how it was called and prints `body`."""
    bin_dir.mkdir(exist_ok=True)
    script = bin_dir / "claude"
    script.write_text(
        "#!/bin/sh\n"
        f'printf "%s\\n" "$@" > "{bin_dir}/args"\n'
        f'env > "{bin_dir}/env"\n'
        f'pwd > "{bin_dir}/cwd"\n'
        "cat > /dev/null\n"
        f"cat <<'EOF'\n{body}\nEOF\n",
        encoding="utf-8",
    )
    script.chmod(script.stat().st_mode | stat.S_IEXEC)
    return script


def test_the_cli_model_has_no_tools_no_settings_and_no_github_token(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    bin_dir = tmp_path / "bin"
    verdict = {"decision": "uncertain"}
    _fake_claude(bin_dir, json.dumps({"is_error": False, "structured_output": verdict}))
    monkeypatch.setenv("PATH", f"{bin_dir}:/usr/bin:/bin")
    monkeypatch.setenv("GH_TOKEN", "ghp_not_for_the_model")
    monkeypatch.setenv("PILOT_BOT_TOKEN", "bot_not_for_the_model")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "key")

    assert ai.call_model_cli("system", "user", "m") == verdict

    args = (bin_dir / "args").read_text().splitlines()
    assert args[args.index("--tools") + 1] == ""
    assert args[args.index("--setting-sources") + 1] == ""
    assert "--strict-mcp-config" in args
    assert "--no-session-persistence" in args
    seen = (bin_dir / "env").read_text()
    assert "GH_TOKEN" not in seen and "PILOT_BOT_TOKEN" not in seen
    assert Path((bin_dir / "cwd").read_text().strip()).name.startswith("gtq-model-")


@pytest.mark.parametrize(
    "body",
    [
        "not json",
        json.dumps({"is_error": True, "structured_output": {}}),
        json.dumps({"is_error": False}),
    ],
)
def test_a_cli_model_that_returns_no_verdict_is_a_model_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, body: str
) -> None:
    _fake_claude(tmp_path / "bin", body)
    monkeypatch.setenv("PATH", f"{tmp_path / 'bin'}:/usr/bin:/bin")
    with pytest.raises(ai.ModelError):
        ai.call_model_cli("s", "u", "m")


def test_a_missing_claude_command_is_a_model_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PATH", str(tmp_path))
    with pytest.raises(ai.ModelError):
        ai.call_model_cli("s", "u", "m")


def test_the_runner_keeps_the_model_and_the_push_access_in_separate_environments(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PILOT_AI_SAMPLE_SALT", "salt")
    monkeypatch.setenv("NTFY_URL", "https://ntfy.example/topic")
    monkeypatch.setenv("GH_TOKEN", "ambient")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "ambient-key")
    calls: list[tuple[list[str], dict[str, str]]] = []

    def fake_run(cmd: list[str], *, cwd: Path, env: dict[str, str], timeout: int) -> Any:
        calls.append((cmd, env))
        if cmd[0].endswith("fetch_pr_data.sh"):
            Path(env["GITHUB_OUTPUT"]).write_text("sha=abc123\n")
        if "review" in cmd:
            Path(cmd[cmd.index("--out") + 1]).write_text("{}")
        out = "tok" if cmd[:3] == ["gh", "auth", "token"] else ""
        return subprocess.CompletedProcess(cmd, 0, out, "")

    monkeypatch.setattr(forge, "_run", fake_run)
    assert forge.review_one(7, tmp_path, tmp_path, "shadow", "o/r", "salt") is True

    review_env = next(env for cmd, env in calls if "review" in cmd)
    apply_env = next(env for cmd, env in calls if "apply" in cmd)
    assert "--backend" in next(cmd for cmd, _ in calls if "review" in cmd)
    assert "GH_TOKEN" not in review_env and "PILOT_BOT_TOKEN" not in review_env
    assert review_env["PILOT_AI_SAMPLE_SALT"] == "salt"
    assert apply_env["PILOT_BOT_TOKEN"] == "tok"
    assert not {k for k in apply_env if "ANTHROPIC" in k or "SALT" in k}
    apply_cmd = next(cmd for cmd, _ in calls if "apply" in cmd)
    assert apply_cmd[apply_cmd.index("--fetched-sha") + 1] == "abc123"


def test_one_failed_step_does_not_reach_apply(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    seen: list[list[str]] = []

    def fake_run(cmd: list[str], *, cwd: Path, env: dict[str, str], timeout: int) -> Any:
        seen.append(cmd)
        if cmd[0].endswith("fetch_pr_data.sh"):
            Path(env["GITHUB_OUTPUT"]).write_text("sha=abc\n")
        return subprocess.CompletedProcess(cmd, 1 if "review" in cmd else 0, "", "boom")

    monkeypatch.setattr(forge, "_run", fake_run)
    assert forge.review_one(7, tmp_path, tmp_path, "shadow", "o/r") is False
    assert not any("apply" in cmd for cmd in seen)


def test_mode_off_does_nothing_and_a_bad_mode_is_refused(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("PILOT_AI_REVIEW_MODE", "off")
    assert forge.main(["forge_review.py"]) == 0
    monkeypatch.setenv("PILOT_AI_REVIEW_MODE", "yolo")
    assert forge.main(["forge_review.py"]) == 2


def test_the_sample_salt_is_made_once_and_kept_when_the_owner_gives_none(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("PILOT_AI_SAMPLE_SALT", raising=False)
    first = forge._salt(tmp_path)
    assert len(first) >= 32 and forge._salt(tmp_path) == first
    assert (tmp_path / "sample-salt").stat().st_mode & 0o077 == 0
    monkeypatch.setenv("PILOT_AI_SAMPLE_SALT", "mine")
    assert forge._salt(tmp_path) == "mine"


def test_no_github_token_means_no_apply(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("PILOT_BOT_TOKEN", raising=False)
    seen: list[list[str]] = []

    def fake_run(cmd: list[str], *, cwd: Path, env: dict[str, str], timeout: int) -> Any:
        seen.append(cmd)
        if cmd[0].endswith("fetch_pr_data.sh"):
            Path(env["GITHUB_OUTPUT"]).write_text("sha=abc\n")
        if "review" in cmd:
            Path(cmd[cmd.index("--out") + 1]).write_text("{}")
        return subprocess.CompletedProcess(cmd, 1 if cmd[0] == "gh" else 0, "", "")

    monkeypatch.setattr(forge, "_run", fake_run)
    assert forge.review_one(7, tmp_path, tmp_path, "shadow", "o/r") is False
    assert not any("apply" in cmd for cmd in seen)


def test_a_failure_is_announced_once_not_every_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("NTFY_URL", "https://ntfy.example/t")
    pings: list[list[str]] = []
    monkeypatch.setattr(
        forge, "_run", lambda cmd, **kw: pings.append(cmd) or subprocess.CompletedProcess(cmd, 0)
    )
    forge._alert_once(tmp_path, [4])
    forge._alert_once(tmp_path, [4])
    forge._alert_once(tmp_path, [4, 9])
    assert len(pings) == 2
