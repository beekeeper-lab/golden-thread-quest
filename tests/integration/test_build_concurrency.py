"""One build at a time per output directory.

Every build stages into `generated.building` and publishes it by rename. That directory's
name is fixed, so two builds in one repository share it, and the second one's first act is
to delete it while the first is still writing into it.

Round 5 reproduced this three times out of three from two concurrent `quest-app build`
calls. The crash was the good case: twice, both processes exited zero and published a site
holding 3 and 20 of its 53 pages, with nothing anywhere saying the site was incomplete.

Round 4 locked `participant/progress.yaml`, which serialises action against action. Build
took no lock at all, and the service rebuilds on every action.
"""

from __future__ import annotations

import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path


def build(repo: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "quest_app.cli", "build", "--repo-root", str(repo)],
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
    )


def pages(repo: Path) -> int:
    return len(list((repo / "generated").rglob("*.html")))


def test_two_builds_at_once_publish_one_whole_site(content_repo: Path) -> None:
    """Both builds succeed, and what lands is a complete site rather than a fragment."""
    first = build(content_repo)
    assert first.returncode == 0, first.stderr
    whole = pages(content_repo)
    assert whole > 1, "a site of one page would make the assertion below vacuous"

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: build(content_repo), range(2)))

    for result in results:
        assert result.returncode == 0, result.stderr
    assert pages(content_repo) == whole, (
        f"two concurrent builds published {pages(content_repo)} of {whole} pages"
    )
    assert not (content_repo / "generated.building").exists(), "staging left behind"


def test_the_published_site_is_never_a_half_built_one(content_repo: Path) -> None:
    """Four at once, because a race that reproduces in three runs of six is still a race."""
    assert build(content_repo).returncode == 0
    whole = pages(content_repo)

    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda _: build(content_repo), range(4)))

    assert all(r.returncode == 0 for r in results), "\n".join(
        r.stderr for r in results if r.returncode != 0
    )
    assert pages(content_repo) == whole
