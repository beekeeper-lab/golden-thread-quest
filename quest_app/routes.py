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


def relative_to(route: str, current: str) -> str:
    """`route` expressed relative to `current`, so the site works opened from a file path.

    A generated page has to work in two contexts: served from the local service, where a
    leading slash is the site root, and double-clicked from `generated/`, where it is the
    filesystem root. Relative links are the only form that works in both.
    """
    if not route.startswith("/"):
        return route
    target_parts = [p for p in route.split("/") if p]
    current_parts = [p for p in current.split("/") if p]
    # A page lives at <route>index.html, so its directory is the route itself.
    depth = len(current_parts)
    anchor = ""
    if "#" in route:
        target_parts[-1], _, anchor_text = target_parts[-1].partition("#")
        anchor = f"#{anchor_text}"
        if not target_parts[-1]:
            target_parts.pop()
    prefix = "../" * depth if depth else "./"
    tail = "/".join(target_parts)
    if tail:
        tail += "/"
    return f"{prefix}{tail}{anchor}" or "./"
