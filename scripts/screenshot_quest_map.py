#!/usr/bin/env python3
"""Take the Quest Map picture the user guide shows.

The map is drawn by the application, so the guide's picture is a screenshot of it rather than
a generated image, and it goes stale whenever the map changes. This rebuilds nothing: run
`make build` first, then

    .venv/bin/python scripts/screenshot_quest_map.py

It serves `generated/` on a loopback port, opens the Quest Map in headless Chromium (the same
browser `make test-ui` uses) and writes `docs/media/images/06-quest-map.png`. Needs the `ui`
extra (`make setup-ui`).
"""

from __future__ import annotations

import functools
import http.server
import socketserver
import sys
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "docs" / "media" / "images" / "06-quest-map.png"


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:  # noqa: A002
        return


def main() -> int:
    generated = ROOT / "generated"
    if not (generated / "map" / "index.html").exists():
        print("No built site. Run `make build` first.", file=sys.stderr)
        return 1
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("Playwright is not installed. Run `make setup-ui`.", file=sys.stderr)
        return 1

    handler = functools.partial(QuietHandler, directory=str(generated))
    with socketserver.TCPServer(("127.0.0.1", 0), handler) as server:
        port = server.server_address[1]
        threading.Thread(target=server.serve_forever, daemon=True).start()
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            page = browser.new_page(viewport={"width": 1280, "height": 900}, device_scale_factor=1.25)
            page.goto(f"http://127.0.0.1:{port}/map/", wait_until="load")
            page.wait_for_timeout(400)
            page.locator(".map-scroll").screenshot(path=str(OUTPUT))
            browser.close()
        server.shutdown()
    print(f"wrote {OUTPUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
