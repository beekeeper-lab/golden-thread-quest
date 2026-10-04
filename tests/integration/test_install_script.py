"""`install.sh` from a clean home folder to a working `gtq` command (Phase 2A.1).

The script's test hooks replace the GitHub parts (sign-in, fork) with a clone of a local
repository, so this runs anywhere Git and uv are installed. The Git and uv installs
themselves, and the GitHub CLI download, were run in a clean Ubuntu container when the
script was written (`docs/pilot/PILOT-LOG.md`). They need the network and a fresh machine,
which this suite does not assume.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]

pytestmark = [
    pytest.mark.slow,
    pytest.mark.skipif(shutil.which("uv") is None, reason="install.sh needs uv here"),
]


def _run(command: list[str], cwd: Path, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command, cwd=cwd, env=env, capture_output=True, text=True, check=False, timeout=600
    )


@pytest.fixture()
def installed(tmp_path: Path) -> dict[str, object]:
    source = tmp_path / "source.git"
    subprocess.run(
        ["git", "clone", "--quiet", "--bare", "--no-local", str(ROOT), str(source)], check=True
    )
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout.strip()
    subprocess.run(["git", "-C", str(source), "tag", "v-test", head], check=True)

    home = tmp_path / "home"
    home.mkdir()
    (home / ".bashrc").write_text("# a participant's own settings\n")
    env = {
        "HOME": str(home),
        "PATH": os.environ["PATH"],
        "UV_CACHE_DIR": os.environ.get("UV_CACHE_DIR", str(Path.home() / ".cache" / "uv")),
        "GIT_CONFIG_NOSYSTEM": "1",
        "GTQ_TEST_SOURCE": str(source),
        "GTQ_VERSION": "v-test",
        "GTQ_NAME": "Pat Tester",
        "GTQ_ASSUME_YES": "1",
        "GTQ_NO_START": "1",
    }
    first = _run(["bash", str(ROOT / "install.sh")], tmp_path, env)
    return {"home": home, "env": env, "first": first, "tmp": tmp_path}


def test_install_makes_a_working_copy_and_command(installed: dict[str, object]) -> None:
    first = installed["first"]
    assert isinstance(first, subprocess.CompletedProcess)
    assert first.returncode == 0, first.stdout + first.stderr
    home = Path(str(installed["home"]))
    env = dict(installed["env"])  # type: ignore[call-overload]
    copy = home / "golden-thread-quest"

    branch = _run(["git", "branch", "--show-current"], copy, env).stdout.strip()
    assert branch == "pilot/pat-tester"
    assert _run(["git", "config", "user.name"], copy, env).stdout.strip() == "Pat Tester"
    upstream = _run(["git", "config", "remote.upstream.url"], copy, env).stdout.strip()
    assert upstream == "https://github.com/beekeeper-lab/golden-thread-quest.git"

    gtq = home / ".local" / "bin" / "gtq"
    assert "gtq hand-in" in _run([str(gtq)], home, env).stdout
    validated = _run([str(gtq), "validate"], home, env)
    assert validated.returncode == 0, validated.stdout + validated.stderr
    assert (home / ".bashrc").read_text().count(".local/bin") == 1


def test_running_install_again_keeps_the_branch_whatever_name_is_typed(
    installed: dict[str, object],
) -> None:
    """Verify pass V2: a second run with the name typed differently made a new branch."""
    home = Path(str(installed["home"]))
    env = dict(installed["env"])  # type: ignore[call-overload]
    copy = home / "golden-thread-quest"
    marker = copy / "participant" / "kept.md"
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text("my work\n")
    _run(["git", "add", "participant"], copy, env)
    _run(["git", "commit", "--quiet", "-m", "handed in"], copy, env)
    _run(["git", "switch", "--quiet", "--detach"], copy, env)

    env["GTQ_NAME"] = "Pat"
    again = _run(["bash", str(ROOT / "install.sh")], Path(str(installed["tmp"])), env)

    assert again.returncode == 0, again.stdout + again.stderr
    assert "Found your copy" in again.stdout
    assert _run(["git", "branch", "--show-current"], copy, env).stdout.strip() == (
        "pilot/pat-tester"
    )
    assert _run(["git", "config", "user.name"], copy, env).stdout.strip() == "Pat Tester"
    assert marker.read_text() == "my work\n"
    assert (home / ".bashrc").read_text().count(".local/bin") == 1


STUB_CURL = """#!/bin/sh
# Records every URL, and answers the two the GitHub CLI download needs.
printf '%s\\n' "$*" >>"$CURL_LOG"
case "$*" in
  *api.github.com*) printf '{"tag_name": "v2.99.0"}\\n' ;;
  *releases/latest*) printf 'https://github.com/cli/cli/releases/tag/v2.99.0' ;;
  *gh_2.99.0_linux_*.tar.gz*) cat "$GH_TARBALL" ;;
  *) exit 22 ;;
esac
"""


def test_the_github_tool_download_makes_no_unsigned_api_call(
    installed: dict[str, object],
) -> None:
    """Phase 2A.2: the latest version came from api.github.com, before anything could be
    signed in. That allows 60 requests an hour per address, which a room of participants
    behind one office address could use up. The release page's redirect is used instead."""
    if os.uname().sysname != "Linux":
        pytest.skip("the stub serves the Linux archive")
    tmp = Path(str(installed["tmp"]))
    arch = {"x86_64": "amd64", "aarch64": "arm64", "arm64": "arm64"}[os.uname().machine]
    folder = tmp / "tarball" / f"gh_2.99.0_linux_{arch}" / "bin"
    folder.mkdir(parents=True)
    (folder / "gh").write_text("#!/bin/sh\necho stub gh\n")
    (folder / "gh").chmod(0o755)
    tarball = tmp / "gh.tar.gz"
    subprocess.run(
        ["tar", "-czf", str(tarball), "-C", str(tmp / "tarball"), f"gh_2.99.0_linux_{arch}"],
        check=True,
    )
    stubs = tmp / "stubs"
    stubs.mkdir()
    (stubs / "curl").write_text(STUB_CURL)
    (stubs / "curl").chmod(0o755)
    log = tmp / "curl.log"
    env = dict(installed["env"])  # type: ignore[call-overload]
    env.update(
        {
            "PATH": f"{stubs}:{env['PATH']}",
            "CURL_LOG": str(log),
            "GH_TARBALL": str(tarball),
            "GTQ_TEST_GH_DOWNLOAD": "1",
        }
    )

    result = _run(["bash", str(ROOT / "install.sh")], tmp, env)

    assert result.returncode == 0, result.stdout + result.stderr
    asked = log.read_text()
    assert "api.github.com" not in asked, asked
    assert "github.com/cli/cli/releases/latest" in asked
    home = Path(str(installed["home"]))
    assert (home / ".local" / "bin" / "gh").read_text().endswith("echo stub gh\n")


# A stand-in for the GitHub CLI that answers from GitHub's own recorded REST responses, so a
# field name the real API does not have reads empty here exactly as it does there.
STUB_GH = """#!/usr/bin/env python3
import json, os, sys

args = sys.argv[1:]
with open(os.environ["GH_LOG"], "a") as log:
    log.write(" ".join(args) + "\\n")


def answer(document, expression):
    expression = expression.split("//")[0].strip()
    value = document
    for key in [part for part in expression.split(".") if part]:
        value = value.get(key) if isinstance(value, dict) else None
    print("" if value is None else value)


if args[:2] in (["auth", "status"], ["auth", "setup-git"]) or args[:2] == ["repo", "fork"]:
    sys.exit(0)
if args[:2] == ["api", "user"]:
    answer({"login": "gdreed31", "id": 12345}, args[args.index("--jq") + 1])
    sys.exit(0)
if args[:2] == ["repo", "view"] and "parent" in args:
    # What `gh repo view --json parent` really prints (recorded): no `nameWithOwner`.
    with open(os.environ["GH_VIEW_RESPONSE"]) as handle:
        answer(json.load(handle), args[args.index("--jq") + 1])
    sys.exit(0)
if args[:2] == ["api", "repos/gdreed31/golden-thread-quest"]:
    with open(os.environ["GH_FORK_RESPONSE"]) as handle:
        answer(json.load(handle), args[args.index("--jq") + 1])
    sys.exit(0)
sys.exit(1)
"""


def test_setup_finds_the_fork_it_made_on_github(tmp_path: Path) -> None:
    """Phase 2A.2 demo: the fork was made, then reported as not made, for every participant.

    `install.sh` asked `gh repo view --json parent` for `nameWithOwner`, which that object
    does not have. Every other test takes the `GTQ_TEST_SOURCE` hook around this step, so
    none saw it. This one runs the GitHub path, with a stand-in `gh` answering from a
    recorded GitHub responses (`fixtures/github/`) and Git's
    `insteadOf` pointing the GitHub URLs at local repositories.
    """
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout.strip()
    upstream = tmp_path / "upstream.git"
    fork = tmp_path / "fork.git"
    for bare in (upstream, fork):
        subprocess.run(
            ["git", "clone", "--quiet", "--bare", "--no-local", str(ROOT), str(bare)], check=True
        )
    subprocess.run(["git", "-C", str(upstream), "tag", "v-test", head], check=True)

    stubs = tmp_path / "stubs"
    stubs.mkdir()
    (stubs / "gh").write_text(STUB_GH)
    (stubs / "gh").chmod(0o755)
    home = tmp_path / "home"
    home.mkdir()
    gitconfig = tmp_path / "gitconfig"
    gitconfig.write_text(
        f'[url "{fork}"]\n\tinsteadOf = https://github.com/gdreed31/golden-thread-quest.git\n'
        f'[url "{upstream}"]\n'
        "\tinsteadOf = https://github.com/beekeeper-lab/golden-thread-quest.git\n"
    )
    log = tmp_path / "gh.log"
    env = {
        "HOME": str(home),
        "PATH": f"{stubs}:{os.environ['PATH']}",
        "UV_CACHE_DIR": os.environ.get("UV_CACHE_DIR", str(Path.home() / ".cache" / "uv")),
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": str(gitconfig),
        "GH_LOG": str(log),
        "GH_FORK_RESPONSE": str(ROOT / "fixtures" / "github" / "fork-repository.json"),
        "GH_VIEW_RESPONSE": str(ROOT / "fixtures" / "github" / "fork-repo-view-parent.json"),
        "GTQ_VERSION": "v-test",
        "GTQ_NAME": "Gregg",
        "GTQ_ASSUME_YES": "1",
        "GTQ_NO_START": "1",
    }

    result = _run(["bash", str(ROOT / "install.sh")], tmp_path, env)

    assert result.returncode == 0, result.stdout + result.stderr
    assert "Signed in as gdreed31" in result.stdout
    copy = home / "golden-thread-quest"
    assert _run(["git", "branch", "--show-current"], copy, env).stdout.strip() == "pilot/gregg"
    assert "repo fork beekeeper-lab/golden-thread-quest" in log.read_text()


def test_setup_on_the_owners_account_says_so(tmp_path: Path) -> None:
    """The pilot lead's own account cannot fork its own repository, and was told to rename
    a repository instead."""
    stubs = tmp_path / "stubs"
    stubs.mkdir()
    (stubs / "gh").write_text(STUB_GH.replace('"gdreed31", "id"', '"beekeeper-lab", "id"'))
    (stubs / "gh").chmod(0o755)
    home = tmp_path / "home"
    home.mkdir()
    env = {
        "HOME": str(home),
        "PATH": f"{stubs}:{os.environ['PATH']}",
        "GIT_CONFIG_NOSYSTEM": "1",
        "GH_LOG": str(tmp_path / "gh.log"),
        "GH_FORK_RESPONSE": str(ROOT / "fixtures" / "github" / "fork-repository.json"),
        "GH_VIEW_RESPONSE": str(ROOT / "fixtures" / "github" / "fork-repo-view-parent.json"),
        "GTQ_ASSUME_YES": "1",
        "GTQ_NO_START": "1",
    }

    result = _run(["bash", str(ROOT / "install.sh")], tmp_path, env)

    assert result.returncode == 1
    assert "the account that owns the quest" in result.stderr
    assert "repo fork" not in (tmp_path / "gh.log").read_text()
