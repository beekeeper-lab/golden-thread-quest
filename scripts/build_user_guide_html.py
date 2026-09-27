#!/usr/bin/env python3
"""Build the self-contained HTML review surface for docs/USER-GUIDE.md.

Markdown stays the source of truth. This assembles the body fragment, the
canonical artifact CSS, the project palette and the diagrams (inlined as WebP
data URIs) into one file that opens offline with no remote resources.

    python3 scripts/build_user_guide_html.py
"""

from __future__ import annotations

import base64
import io
import os
import pathlib
import sys


ROOT = pathlib.Path(__file__).resolve().parent.parent
# The two stylesheets this guide is built with. They are not in this repository and are not
# a package dependency: they come from the authoring tool the maintainer uses. A fallback to
# a path in the maintainer's own home directory here meant the script "worked" only on that
# one machine and silently used whatever happened to be there, contrary to CONTRIBUTING's
# promise that without them the script says so and stops. There is no fallback: point
# `GTQ_HTML_SNIPPETS` at a directory holding `base.css` and `print.css`, or the script stops
# with the message below.
SKILL = pathlib.Path(os.environ["GTQ_HTML_SNIPPETS"]) if "GTQ_HTML_SNIPPETS" in os.environ else None
BODY = ROOT / "artifacts/html/guides/_user-guide-body.html"
OUT = ROOT / "artifacts/html/guides/user-guide.html"
IMAGES = ROOT / "docs/media/images"

DIAGRAMS = [
    "01-first-hour-flow-v3",
    "02-state-authority-v2",
    "03-ownership-zones-v4",
    "04-evidence-package",
    "05-passport-outcome-v2",
]

# Project palette over the canonical tokens, plus the dark mode the canonical
# sheet does not ship. Amber is reserved for verified, exactly as the product
# reserves it, and never carries text on parchment.
OVERRIDES = """
/* ---- Golden Thread palette, layered over the canonical tokens ---- */
:root {
  --bg: #f4f1e9;
  --panel: #fdfcf8;
  --ink: #172433;
  --muted: #5f6b78;
  --border: #ddd6c6;
  --border-strong: #b5a98f;
  --accent: #172433;
  --accent-soft: #e7ecf1;
  --accent-ink: #0d1721;
  --gold: #8a6414;
  --th-bg: #ece7da;
  --row-hover: #f7f4ec;
  --chip-bg: #ece7da;
  --chip-ink: #172433;
  --chip-border: #ddd6c6;
  --mount-bg: #f7f4ec;
  --radius: 10px;
}

/* The canonical sheet is light-only. These are the surfaces that carry a
   literal light value there; without them, light text lands on light fills. */
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --bg: #141b23;
    --panel: #1b242e;
    --ink: #e8ecf1;
    --muted: #9fadba;
    --border: #2e3a46;
    --border-strong: #46566a;
    --accent: #cdd8e3;
    --accent-soft: #24303c;
    --accent-ink: #f0f4f8;
    --gold: #d9a63f;
    --th-bg: #24303c;
    --row-hover: #202b36;
    --chip-bg: #24303c;
    --chip-ink: #e8ecf1;
    --chip-border: #35424f;
    --control-bg: #1b242e;
    --control-tick: #141b23;
    --mount-bg: #f7f4ec;
    --code-bg: #0d141b;
    --success: #8fe3b0; --success-soft: #16301f;
    --warning: #edc77f; --warning-soft: #322611;
    --danger:  #f3aaaa; --danger-soft:  #3a1c1c;
  }
  :root:not([data-theme="light"]) .btn--primary { color: var(--bg); }
}

html, body { background: var(--bg); color: var(--ink); }

/* ---- guide-specific ---- */
.eyebrow { text-transform: uppercase; letter-spacing: .14em; font-size: .75rem;
  font-weight: 600; color: var(--muted); margin: 0 0 .35rem; }
.lede { font-size: 1.12rem; line-height: 1.65; max-width: 62ch; color: var(--ink); }
.hero h1 { letter-spacing: -0.02em; }
.grid--2 { display: grid; gap: 1rem; grid-template-columns: repeat(auto-fit, minmax(19rem, 1fr)); }
.grid--2 > * { margin: 0; }
/* The parchment mount belongs to the image alone. If the figure carried it,
   the caption's muted ink would sit on parchment and fail contrast in dark mode. */
figure.diagram { margin: 1.75rem 0; padding: 0; border: 0; background: none; }
figure.diagram img { width: 100%; height: auto; display: block; box-sizing: border-box;
  padding: .75rem; background: var(--mount-bg); border: 1px solid var(--border);
  border-radius: var(--radius); }
.diagram-caption { font-size: .875rem; color: var(--muted); line-height: 1.5;
  margin-top: .7rem; max-width: 70ch; }
.diagram-caption .badge { margin-right: .4rem; vertical-align: baseline; }
ol.steps { padding-left: 1.3rem; }
ol.steps > li { margin-bottom: .85rem; line-height: 1.6; }
ol.steps ul { margin: .45rem 0 0; }
th[scope="row"] { font-weight: 600; white-space: normal; background: var(--th-bg); }
.page-footer { margin: 2.5rem 0 1rem; padding-top: 1rem; border-top: 1px solid var(--border); }
.toc ol { columns: 2; column-gap: 2rem; }
@media (max-width: 640px) {
  .page { padding-left: 16px; padding-right: 16px; }
  .toc ol { columns: 1; }
  .lede { font-size: 1.02rem; }
  figure.diagram img { padding: .4rem; }
}
"""


def webp_data_uri(png: pathlib.Path, max_px: int = 1200, quality: int = 90) -> str:
    """Flat vector art: WebP at doc resolution is ~6% of the PNG."""
    # Imported here, not at the top: the script has to be able to say what it needs before
    # it needs it, and `.[docs]` is an extra a contributor may not have installed.
    from PIL import Image

    image = Image.open(png).convert("RGB")
    image.thumbnail((max_px, max_px), Image.LANCZOS)
    buffer = io.BytesIO()
    image.save(buffer, "WEBP", quality=quality, method=6)
    encoded = base64.b64encode(buffer.getvalue()).decode()
    return f"data:image/webp;base64,{encoded}"


def main() -> int:
    if SKILL is None:
        print(
            "cannot build the guide: GTQ_HTML_SNIPPETS is not set.\n"
            "Set it to a directory holding base.css and print.css. "
            "The built guide is committed at artifacts/html/guides/user-guide.html, so "
            "rebuilding it is a maintainer step and not one a contributor has to take.",
            file=sys.stderr,
        )
        return 2

    missing = [name for name in ("base.css", "print.css") if not (SKILL / name).is_file()]
    if missing:
        print(
            f"cannot build the guide: {', '.join(missing)} not found in {SKILL}.\n"
            "Set GTQ_HTML_SNIPPETS to a directory holding base.css and print.css. "
            "The built guide is committed at artifacts/html/guides/user-guide.html, so "
            "rebuilding it is a maintainer step and not one a contributor has to take.",
            file=sys.stderr,
        )
        return 2

    body = BODY.read_text()
    for index, stem in enumerate(DIAGRAMS, start=1):
        png = IMAGES / f"{stem}.png"
        if not png.exists():
            print(f"missing diagram: {png}", file=sys.stderr)
            return 1
        body = body.replace("{{IMG_%02d}}" % index, webp_data_uri(png))

    if "{{" in body:
        print("unsubstituted placeholder remains in body", file=sys.stderr)
        return 1

    base_css = (SKILL / "base.css").read_text()
    print_css = (SKILL / "print.css").read_text()

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(
        "<!DOCTYPE html>\n"
        '<html lang="en">\n<head>\n'
        '<meta charset="utf-8" />\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1" />\n'
        "<title>Golden Thread Quest</title>\n"
        '<meta name="description" content="Participant user guide for the Golden '
        "Thread Quest: install it, work through a quest, assemble evidence, and get "
        'it reviewed." />\n'
        f"<style>\n{base_css}\n{OVERRIDES}\n@media print {{\n{print_css}\n}}\n</style>\n"
        f"</head>\n<body>\n{body}\n</body>\n</html>\n"
    )
    print(f"wrote {OUT.relative_to(ROOT)} — {OUT.stat().st_size / 1024:.0f} KB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
