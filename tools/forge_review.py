"""Run the automatic reviewer on a machine of the owner's, from a timer (ADR-047).

This does what .github/workflows/pilot-ai-review.yml does, with the machine's own logins
instead of repository secrets: the `claude` command is the model, the `gh` login is the push
access. Stdlib only. Each run:

  1. clones the program repository's main branch fresh, so what runs is reviewed code and never
     the working checkout, and never anything a participant wrote;
  2. selects the open pilot pull requests that are ready and have no verdict;
  3. for each one: fetches the participant's files as data, runs `ai_review.py review` (the model,
     no GitHub token in its environment), then `ai_review.py apply` (the push access, no model).

The two halves are separate processes with different environments, as the two jobs are in the
workflow: the model never sees the GitHub token, and the apply step reads only the validated plan.

Settings come from the environment (the unit's EnvironmentFile): PILOT_AI_REVIEW_MODE (off,
shadow by default, or live), PILOT_AI_SAMPLE_EVERY, PILOT_AI_MODEL, PILOT_AI_SAMPLE_SALT and the
optional NTFY_URL.
"""

from __future__ import annotations

import argparse
import fcntl
import json
import os
import secrets
import shutil
import signal
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = "beekeeper-lab/golden-thread-quest"
PLAIN = ("PATH", "HOME", "LANG", "USER", "XDG_CONFIG_HOME", "XDG_STATE_HOME")
# Lets `git fetch` in the clone use the machine's GitHub login, so a private repository works.
GIT_AUTH = {
    "GIT_CONFIG_COUNT": "1",
    "GIT_CONFIG_KEY_0": "credential.helper",
    "GIT_CONFIG_VALUE_0": "!gh auth git-credential",
}


def _salt(state: Path) -> str:
    """The sample salt: the owner's, else one made once and kept (so a re-run samples the same)."""
    if os.environ.get("PILOT_AI_SAMPLE_SALT"):
        return os.environ["PILOT_AI_SAMPLE_SALT"]
    path = state / "sample-salt"
    if not path.is_file():
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w") as handle:
            handle.write(secrets.token_hex(32))
    return path.read_text(encoding="utf-8").strip()


def _env(*extra: str, add: dict[str, str] | None = None) -> dict[str, str]:
    env = {k: v for k, v in os.environ.items() if k in (*PLAIN, *extra)}
    return {**env, **(add or {})}


def _run(
    cmd: list[str], *, cwd: Path, env: dict[str, str], timeout: int
) -> subprocess.CompletedProcess[str]:
    """Run to completion; on a timeout kill the whole process group, not just the first child."""
    proc = subprocess.Popen(  # noqa: S603
        cmd, cwd=cwd, env=env, text=True, start_new_session=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )  # fmt: skip
    try:
        out, err = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        os.killpg(proc.pid, signal.SIGKILL)
        proc.communicate()
        raise
    return subprocess.CompletedProcess(cmd, proc.returncode, out, err)


def _show(result: subprocess.CompletedProcess[str]) -> None:
    for line in (result.stdout + result.stderr).strip().splitlines():
        print(f"    {line}")


def _python(base: Path, script: str, *args: str) -> list[str]:
    return ["uv", "run", "--quiet", "--project", str(base), "python", str(base / script), *args]


def review_one(number: int, base: Path, work: Path, mode: str, repo: str, salt: str = "") -> bool:
    """One pull request through fetch, review and apply. True if every step ran."""
    out = work / f"pr-{number}"
    outputs = work / f"fetch-{number}.out"
    fetch_env = _env(add={**GIT_AUTH, "REPO": repo, "GITHUB_OUTPUT": str(outputs)})
    fetched = _run(
        ["tools/fetch_pr_data.sh", str(number), str(out)], cwd=base, env=fetch_env, timeout=300
    )
    if fetched.returncode != 0 or not outputs.is_file():
        _show(fetched)
        return False
    sha = next(
        (
            line.removeprefix("sha=")
            for line in outputs.read_text(encoding="utf-8").splitlines()
            if line.startswith("sha=")
        ),
        "",
    )
    if not sha:
        return False
    plan = work / f"plan-{number}.json"

    reviewed = _run(
        _python(
            base,
            "tools/ai_review.py",
            "review",
            "--participant-root",
            str(out / "participant"),
            "--files-json",
            str(out / "files.json"),
            "--labels-json",
            str(out / "labels.json"),
            "--head-sha",
            sha,
            "--mode",
            mode,
            "--backend",
            "cli",
            "--sample-every",
            os.environ.get("PILOT_AI_SAMPLE_EVERY", "5"),
            "--model",
            os.environ.get("PILOT_AI_MODEL", "claude-opus-5-5"),
            "--out",
            str(plan),
        ),
        cwd=base,
        env=_env(add={"PILOT_AI_SAMPLE_SALT": salt} if salt else {}),
        timeout=1200,
    )
    _show(reviewed)
    if reviewed.returncode != 0 or not plan.is_file():
        return False

    token = os.environ.get("PILOT_BOT_TOKEN", "")
    if not token:  # the machine's own login: broader than a token scoped to the one repository
        got = _run(["gh", "auth", "token"], cwd=base, env=_env(), timeout=30)
        token = got.stdout.strip() if got.returncode == 0 else ""
    if not token:
        print("    no GitHub token for the apply step")
        return False
    applied = _run(
        _python(
            base,
            "tools/ai_review.py",
            "apply",
            "--plan",
            str(plan),
            "--pr",
            str(number),
            "--repo",
            repo,
            "--mode",
            mode,
            "--fetched-sha",
            sha,
            "--data-root",
            str(out),
        ),
        cwd=base,
        env=_env("NTFY_URL", add={"PILOT_BOT_TOKEN": token}),
        timeout=900,
    )
    _show(applied)
    return applied.returncode == 0


def _alert_once(state: Path, failed: list[int]) -> None:
    """Ping once per pull request that a run could not complete, not every ten minutes."""
    path = state / "alerted.json"
    try:
        seen = set(json.loads(path.read_text(encoding="utf-8")))
    except (OSError, ValueError):
        seen = set()
    new = [n for n in failed if n not in seen]
    url = os.environ.get("NTFY_URL")
    if new and url:
        _run(
            ["curl", "-fsS", "-H", "Title: Pilot review", "-d",
             f"The reviewer could not complete {new}; see journalctl --user -u gtq-reviewer", url],
            cwd=state, env=_env(), timeout=30,
        )  # fmt: skip
    path.write_text(json.dumps(sorted(seen | set(failed))), encoding="utf-8")


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--repo", default=REPO)
    parser.add_argument("--ref", help="branch of the program repository to run (default: main)")
    parser.add_argument("--pr", type=int, help="review this pull request only (default: sweep)")
    args = parser.parse_args(argv[1:])

    mode = os.environ.get("PILOT_AI_REVIEW_MODE") or "shadow"
    if mode not in {"off", "shadow", "live"}:
        print(f"PILOT_AI_REVIEW_MODE is {mode!r}; it must be off, shadow or live")
        return 2
    if mode == "off":
        print("the automatic reviewer is turned off")
        return 0

    state = Path(os.environ.get("XDG_STATE_HOME") or Path.home() / ".local/state") / "gtq-reviewer"
    state.mkdir(parents=True, exist_ok=True)
    with (state / "lock").open("w") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print("another run is in progress; nothing done")
            return 75
        signal.signal(signal.SIGTERM, lambda *_: sys.exit(143))  # so `finally` cleans up
        salt = _salt(state)
        work = Path(tempfile.mkdtemp(prefix="run-", dir=state))
        try:
            base = work / "base"
            cloned = _run(
                [
                    "gh",
                    "repo",
                    "clone",
                    args.repo,
                    str(base),
                    "--",
                    "--depth",
                    "1",
                    *(["--branch", args.ref] if args.ref else []),
                ],
                cwd=work,
                env=_env(),
                timeout=300,
            )
            if cloned.returncode != 0:
                _show(cloned)
                return 1
            if args.pr:
                numbers = [args.pr]
            else:
                chosen = _run(
                    _python(base, "tools/ai_review.py", "select", "--repo", args.repo),
                    cwd=base,
                    env=_env(),
                    timeout=300,
                )
                if chosen.returncode != 0:
                    _show(chosen)
                    return 1
                numbers = json.loads(chosen.stdout.strip().splitlines()[-1])
            print(f"mode {mode}; reviewing {numbers}")
            failed = []
            for number in numbers:
                print(f"  #{number}")
                try:
                    ok = review_one(number, base, work, mode, args.repo, salt)
                except Exception as exc:  # one bad pull request must not stop the others
                    print(f"    {type(exc).__name__}: {exc}")
                    ok = False
                if not ok:
                    failed.append(number)
            if failed:
                print(f"did not complete: {failed}")
                _alert_once(state, failed)
            return 1 if failed else 0
        finally:
            shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
