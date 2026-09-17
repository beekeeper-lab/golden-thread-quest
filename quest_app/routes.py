"""Every URL in the generated site, derived from stable IDs.

Content files never store output paths (`docs/ARCHITECTURE.md`): a quest knows its ID, and
the route helper turns that into a URL. Moving the site under a subdirectory, or renaming a
page, is then one change here rather than a search through content.

Routes end in a slash and map to `<route>index.html` on disk, so the same paths work when
the site is opened from the filesystem and when it is served.
"""

from __future__ import annotations

from pathlib import PurePosixPath

HOME = "/"
MAP = "/map/"
CATALOG = "/catalog/"
PASSPORT = "/passport/"
HEALTH = "/health/"
REVIEW_INDEX = "/review/"
EVIDENCE_INDEX = "/evidence/"
ERRORS = "/errors/"


def action(action_id: str, quest_id: str, validator_id: str | None = None) -> str:
    """Where a form posts to perform one allowed action.

    The path carries only IDs the server resolves against loaded content, never a path or a
    command, so a form is exactly as constrained as a JSON request.
    """
    route = f"/api/action/{action_id}/{quest_id}/"
    return f"{route}{validator_id}/" if validator_id else route


def tag(tag_id: str) -> str:
    return f"/tags/{tag_id}/"


def region(region_id: str) -> str:
    return f"/regions/{region_id}/"


def quest(quest_id: str) -> str:
    return f"/quests/{quest_id}/"


def evidence(quest_id: str) -> str:
    return f"/evidence/{quest_id}/"


def review(quest_id: str) -> str:
    return f"/review/{quest_id}/"


def validation(quest_id: str, run_id: str) -> str:
    return f"/evidence/{quest_id}/validation/{run_id}/"


def catalog_filtered(**filters: str) -> str:
    """The catalog with filters pre-applied, for a tag chip or a region link.

    Filters live in the query string so a filtered view is shareable and reloadable, and so
    the no-JavaScript form submits to a URL that means the same thing.
    """
    pairs = sorted((key, value) for key, value in filters.items() if value)
    if not pairs:
        return CATALOG
    from urllib.parse import urlencode

    return f"{CATALOG}?{urlencode(pairs)}"


def output_path(route: str) -> PurePosixPath:
    """Where a route is written inside the output directory.

    A route is trusted input — it comes from these helpers, never from content or a request
    — but it is still checked, because a route that escaped the output directory would write
    a file anywhere the process can reach.
    """
    if not route.startswith("/") or ".." in route:
        raise ValueError(f"unsafe route: {route!r}")
    relative = route.strip("/")
    return PurePosixPath(relative) / "index.html" if relative else PurePosixPath("index.html")


def asset(path: str, *, fingerprint: str | None = None) -> str:
    """A static asset URL, with a cache-busting query when the build supplies a fingerprint."""
    url = f"/assets/{path.lstrip('/')}"
    return f"{url}?v={fingerprint}" if fingerprint else url


def relative_to(target: str, current: str) -> str:
    """`target` expressed relative to the page at `current`.

    A generated page has to work in two contexts: served by the local service, where a
    leading slash is the site root, and opened straight from `generated/`, where a leading
    slash is the filesystem root. Relative links are the only form that works in both.

    A route ending in `/` is a page directory and keeps its slash; anything else — a
    stylesheet, a script — is a file and must not gain one. Appending a slash to every
    target turned every asset link into a directory that does not exist.
    """
    if not target.startswith("/"):
        return target

    path, _, fragment = target.partition("#")
    is_directory = path.endswith("/")
    target_parts = [part for part in path.split("/") if part]
    # `current` is a page route, so the page lives at <current>index.html and its directory
    # depth is the number of segments in the route.
    depth = len([part for part in current.split("/") if part])

    prefix = "../" * depth if depth else "./"
    tail = "/".join(target_parts)
    if tail and is_directory:
        tail += "/"
    result = f"{prefix}{tail}" or "./"
    return f"{result}#{fragment}" if fragment else result
