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
