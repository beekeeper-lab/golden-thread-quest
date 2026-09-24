#!/usr/bin/env python3
"""Build the HTML review surface for the system design document in docs/design/.

The Markdown in docs/design/ is the source of truth. This script renders it into one
self-contained HTML file: inline CSS, every Mermaid block turned into inline SVG by the
Mermaid CLI, no scripts, no remote resources. The version comes from docs/design/VERSION and
appears in the file name and on the title page.

    .venv/bin/python scripts/build_design_html.py

Needs `markdown-it-py` (a project dependency, so the project's virtual environment has it)
and the Mermaid CLI `mmdc` on PATH (`npm install -g @mermaid-js/mermaid-cli`). Set
`GTQ_MMDC` to use another command, for example `npx -y @mermaid-js/mermaid-cli`.
See docs/design/REGENERATING.md.
"""

from __future__ import annotations

import hashlib
import html
import json
import os
import re
import shlex
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DESIGN = ROOT / "docs" / "design"
OUT_DIR = ROOT / "artifacts" / "html" / "design"
PARTS = (
    "01-purpose-and-users.md",
    "02-architecture.md",
    "03-data-and-state.md",
    "04-activity-flows.md",
    "05-security.md",
    "06-decisions.md",
    "07-status-and-remaining-work.md",
    "08-glossary.md",
)
PART_LINK = re.compile(r"^(\d\d)-[a-z0-9-]+\.md(?:#.*)?$")

# Mermaid renders plain SVG text (no foreignObject), so the figures print and scale cleanly.
MERMAID_CONFIG = {
    # ELK keeps edges attached to nodes inside swimlanes; the default layout does not.
    "layout": "elk",
    "theme": "neutral",
    "fontFamily": "system-ui, -apple-system, Segoe UI, Roboto, sans-serif",
    "htmlLabels": False,
    "flowchart": {
        "htmlLabels": False,
        "curve": "basis",
        "padding": 10,
        "nodeSpacing": 30,
        "rankSpacing": 30,
        "wrappingWidth": 260,
    },
    "sequence": {
        "useMaxWidth": False,
        "mirrorActors": False,
        "actorMargin": 30,
        "width": 110,
        "messageMargin": 28,
    },
    "state": {"useMaxWidth": False},
    "er": {"useMaxWidth": False},
}

CSS = """
:root {
  --bg: #f4f1e9; --panel: #fdfcf8; --ink: #172433; --muted: #5f6b78;
  --border: #ddd6c6; --border-strong: #b5a98f; --accent: #1d4ed8; --accent-soft: #e7ecf1;
  --accent-ink: #0d1721; --warning: #7c3a06; --warning-soft: #fbf0d9;
  --danger: #8f1d1d; --danger-soft: #f9e3e3; --code-bg: #111827; --code-ink: #e5e7eb;
  --th-bg: #ece7da; --chip-bg: #ece7da; --chip-ink: #172433; --chip-border: #ddd6c6;
  --mount-bg: #ffffff; --radius: 10px; --radius-sm: 4px;
  --shadow: 0 1px 2px rgba(0,0,0,.04), 0 1px 3px rgba(0,0,0,.06);
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --bg: #141b23; --panel: #1b242e; --ink: #e8ecf1; --muted: #9fadba; --border: #2e3a46;
    --border-strong: #46566a; --accent: #9cc3ff; --accent-soft: #24303c; --accent-ink: #f0f4f8;
    --warning: #edc77f; --warning-soft: #322611; --danger: #f3aaaa; --danger-soft: #3a1c1c;
    --code-bg: #0d141b; --th-bg: #24303c; --chip-bg: #24303c; --chip-ink: #e8ecf1;
    --chip-border: #35424f;
  }
}
* { box-sizing: border-box; }
html { -webkit-text-size-adjust: 100%; }
body { margin: 0; background: var(--bg); color: var(--ink);
  font: 16px/1.6 system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial,
  sans-serif; }
a { color: var(--accent); text-underline-offset: 2px; }
a:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; border-radius: 2px; }
.page { max-width: 64rem; margin: 0 auto; padding: 2rem 1.25rem 4rem; }
@media (min-width: 56rem) { .page { padding: 3rem 2rem 5rem; } }
@media (max-width: 640px) { .page { padding-left: 16px; padding-right: 16px; } }
.hero { background: var(--panel); border: 1px solid var(--border); border-radius: var(--radius);
  padding: 1.75rem; margin-bottom: 1.5rem; box-shadow: var(--shadow); }
.hero .eyebrow { margin: 0 0 .35rem; color: var(--muted); font-size: .75rem; font-weight: 600;
  letter-spacing: .14em; text-transform: uppercase; }
.hero h1 { margin: 0 0 .5rem; font-size: 2rem; line-height: 1.2; letter-spacing: -.02em; }
.hero .subtitle { margin: 0 0 1rem; font-size: 1.0625rem; max-width: 48rem; }
.kv { display: grid; grid-template-columns: max-content 1fr; gap: .3rem 1rem; margin: 0;
  font-size: .9375rem; border-top: 1px dashed var(--border); padding-top: .9rem; }
.kv dt { color: var(--muted); font-weight: 600; }
.kv dd { margin: 0; }
.version { font-size: 1.125rem; font-weight: 700; }
.toc { background: var(--panel); border: 1px solid var(--border); border-radius: var(--radius);
  padding: 1rem 1.25rem; margin-bottom: 1.5rem; font-size: .9375rem; }
.toc h2 { margin: 0 0 .5rem; font-size: .75rem; letter-spacing: .08em; text-transform: uppercase;
  color: var(--muted); border: 0; padding: 0; }
.toc > ol { margin: 0; padding-left: 1.25rem; columns: 2; column-gap: 2rem; }
.toc > ol > li { break-inside: avoid; margin-bottom: .5rem; }
.toc ol ol { padding-left: 1rem; margin: .15rem 0 0; font-size: .875rem; list-style: none; }
.toc a { color: var(--ink); text-decoration: none; }
.toc a:hover { color: var(--accent); text-decoration: underline; }
@media (max-width: 640px) { .toc > ol { columns: 1; } }
main { display: grid; gap: 1.25rem; }
section.card { background: var(--panel); border: 1px solid var(--border);
  border-radius: var(--radius); padding: 1.5rem; box-shadow: var(--shadow); min-width: 0; }
section.card > h2:first-child { margin-top: 0; }
h2 { margin: 1.5rem 0 .75rem; font-size: 1.5rem; line-height: 1.3;
  border-bottom: 1px solid var(--border); padding-bottom: .4rem; }
h3 { margin: 1.75rem 0 .5rem; font-size: 1.1875rem; }
h4 { margin: 1.25rem 0 .35rem; font-size: 1rem; }
p, ul, ol { margin: .5rem 0 .75rem; }
ul, ol { padding-left: 1.25rem; }
li + li { margin-top: .15rem; }
blockquote { margin: .75rem 0; padding: .5rem 1rem; border-left: 4px solid var(--border-strong);
  background: var(--accent-soft); border-radius: 0 var(--radius-sm) var(--radius-sm) 0; }
blockquote p { margin: .25rem 0; }
.table-wrap { overflow-x: auto; margin: .75rem 0 1rem; }
table { width: 100%; border-collapse: collapse; font-size: .9rem; }
th, td { text-align: left; padding: .45rem .65rem; border-bottom: 1px solid var(--border);
  vertical-align: top; }
th { background: var(--th-bg); font-weight: 600; border-bottom: 2px solid var(--border-strong); }
code, pre { font: .875rem/1.55 ui-monospace, "SF Mono", Menlo, Consolas, "Liberation Mono",
  monospace; }
p code, li code, td code, th code, figcaption code {
  background: var(--chip-bg); color: var(--chip-ink);
  border: 1px solid var(--chip-border); border-radius: var(--radius-sm); padding: .05rem .3rem;
  font-size: .85em; overflow-wrap: anywhere; }
.code-block { background: var(--code-bg); color: var(--code-ink); border-radius: var(--radius);
  overflow: hidden; margin: .75rem 0; border: 1px solid #0b1220; }
.code-block-header { padding: .35rem .75rem; background: #0b1220; color: #9ca3af;
  font: .75rem/1 ui-monospace, monospace; letter-spacing: .04em; text-transform: uppercase; }
.code-block pre { margin: 0; padding: .875rem 1rem; overflow-x: auto; }
figure.diagram { margin: 1.25rem 0; }
figure.diagram .mount { background: var(--mount-bg); border: 1px solid var(--border);
  border-radius: var(--radius); padding: .75rem; overflow-x: auto; }
figure.diagram svg { display: block; width: 100%; height: auto; margin: 0 auto; }
figcaption { font-size: .875rem; color: var(--muted); margin-top: .6rem; line-height: 1.5; }
figcaption em { font-style: normal; }
.page-footer { margin-top: 2rem; padding-top: 1rem; border-top: 1px solid var(--border);
  color: var(--muted); font-size: .875rem; text-align: center; }
@media print {
  @page { size: A4; margin: 14mm 12mm; }
  :root { --bg: #fff; --panel: #fff; --ink: #000; --muted: #333; --border: #999; }
  body { background: #fff; color: #000; font-size: 10pt; line-height: 1.45; }
  .page { max-width: 100%; padding: 0; }
  .hero, section.card { box-shadow: none; border: 0; border-radius: 0; padding: 0; }
  .hero { border-bottom: 2px solid #000; padding-bottom: .75rem; margin-bottom: 1rem; }
  .toc { border: 1px solid #999; break-after: page; }
  .toc > ol { columns: 2; }
  main { display: block; }
  section.card { break-before: page; margin: 0; }
  h2, h3, h4 { break-after: avoid; }
  h2 { border-bottom: 1px solid #000; }
  figure.diagram, .code-block, blockquote, tr { break-inside: avoid; }
  figure.diagram .mount { border: 1px solid #999; padding: 4px; }
  figure.diagram svg { max-width: 100% !important; max-height: 235mm; }
  table { font-size: 8.5pt; }
  thead { display: table-header-group; }
  .code-block { background: #fff; color: #000; border: 1px solid #999; }
  .code-block pre { white-space: pre-wrap; overflow-wrap: anywhere; }
  .code-block-header { background: #f0f0f0; color: #000; }
  p code, li code, td code, th code, figcaption code { background: #f3f3f3; border-color: #ccc; }
  a { color: #000; text-decoration: none; }
}
"""


def read_metadata() -> dict[str, str]:
    """Version from VERSION; date and described commit from the README's table."""
    version = (DESIGN / "VERSION").read_text(encoding="utf-8").strip()
    if not re.fullmatch(r"\d+\.\d+\.\d+", version):
        raise SystemExit(f"docs/design/VERSION holds {version!r}, not MAJOR.MINOR.PATCH")
    rows = dict(
        re.findall(
            r"^\| ([A-Za-z ]+) \| (.+?) \|$", (DESIGN / "README.md").read_text("utf-8"), re.M
        )
    )
    if rows.get("Version") != version:
        raise SystemExit(
            f"docs/design/README.md says version {rows.get('Version')!r}; VERSION says "
            f"{version!r}. Make them agree."
        )
    for key in ("Date", "Describes", "Audit status from"):
        if key not in rows:
            raise SystemExit(f"docs/design/README.md has no {key!r} row in its table")
    return {"version": version, **rows}


def mmdc_command() -> list[str]:
    return shlex.split(os.environ.get("GTQ_MMDC", "mmdc"))


def render_mermaid(source: str, figure_id: str, workdir: Path) -> str:
    """One Mermaid block as an inline SVG element with ids unique to this figure."""
    digest = hashlib.sha256(source.encode("utf-8")).hexdigest()[:12]
    source_path = workdir / f"{digest}.mmd"
    svg_path = workdir / f"{digest}.svg"
    config_path = workdir / "config.json"
    source_path.write_text(source, encoding="utf-8")
    config_path.write_text(json.dumps(MERMAID_CONFIG), encoding="utf-8")
    command = [
        *mmdc_command(),
        "--quiet",
        "-i", str(source_path),
        "-o", str(svg_path),
        "-c", str(config_path),
        "-b", "white",
        "--svgId", figure_id,
    ]  # fmt: skip
    try:
        subprocess.run(command, check=True, capture_output=True, text=True)  # noqa: S603
    except FileNotFoundError:
        raise SystemExit(
            f"cannot run {command[0]!r}. Install the Mermaid CLI "
            "(npm install -g @mermaid-js/mermaid-cli) or set GTQ_MMDC."
        ) from None
    except subprocess.CalledProcessError as error:
        raise SystemExit(f"Mermaid failed on {figure_id}:\n{error.stderr}") from None
    svg = svg_path.read_text(encoding="utf-8")
    svg = re.sub(r"^<\?xml[^>]*>\s*", "", svg)
    # The ELK layout writes this placeholder as the id of every swimlane; drop it.
    svg = svg.replace(' id="[object Object]"', "")
    # Let CSS size the figure from its viewBox instead of the fixed size Mermaid writes.
    svg = re.sub(r"<svg([^>]*?)\swidth=\"[^\"]*\"", r"<svg\1", svg, count=1)
    svg = re.sub(r"<svg([^>]*?)\sheight=\"[^\"]*\"", r"<svg\1", svg, count=1)
    svg = re.sub(r"<svg([^>]*?)\sstyle=\"[^\"]*\"", r"<svg\1", svg, count=1)
    # On screen a figure is never drawn larger than its natural size.
    view_box = re.search(r'viewBox="[-\d.]+ [-\d.]+ ([\d.]+) ([\d.]+)"', svg)
    if view_box:
        width = round(float(view_box.group(1)))
        svg = svg.replace("<svg", f'<svg style="max-width:{width}px"', 1)
    return svg


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def rewrite_href(href: str) -> str:
    if href.startswith(("#", "http://", "https://", "mailto:")):
        return href
    match = PART_LINK.match(href)
    if match:
        return f"#part-{match.group(1)}"
    return os.path.relpath(DESIGN / href, OUT_DIR)


def render_part(md, text: str, number: str, workdir: Path, figures: list[int]):  # type: ignore[no-untyped-def]
    """Render one part. Returns (title, [(anchor, heading)], html)."""
    nodes = md.parse(text)
    output = []
    title = ""
    sections: list[tuple[str, str]] = []
    index = 0
    while index < len(nodes):
        node = nodes[index]
        if node.type == "heading_open":
            level = int(node.tag[1])
            inline = nodes[index + 1]
            anchor = f"part-{number}" if level == 1 else f"p{number}-{slug(inline.content)}"
            node.attrSet("id", anchor)
            node.tag = f"h{min(level + 1, 6)}"
            nodes[index + 2].tag = node.tag
            if level == 1:
                title = inline.content
            elif level == 2:
                sections.append((anchor, inline.content))
        elif node.type == "link_open":
            node.attrSet("href", rewrite_href(node.attrGet("href") or ""))
        elif node.type == "inline" and node.children:
            for child in node.children:
                if child.type == "link_open":
                    child.attrSet("href", rewrite_href(child.attrGet("href") or ""))
        if node.type == "fence" and node.info.strip() == "mermaid":
            figures[0] += 1
            figure_id = f"figure-{figures[0]}"
            svg = render_mermaid(node.content, figure_id, workdir)
            caption_html = ""
            following = nodes[index + 1 : index + 4]
            if (
                len(following) == 3
                and following[0].type == "paragraph_open"
                and following[1].content.lstrip("*_").startswith("Figure")
            ):
                caption_html = md.renderInline(following[1].content)
                index += 3
            caption_id = f"{figure_id}-caption"
            svg = svg.replace("<svg", f'<svg role="img" aria-labelledby="{caption_id}"', 1)
            figure = (
                f'<figure class="diagram" id="{figure_id}-figure">\n'
                f'<div class="mount">{svg}</div>\n'
                f'<figcaption id="{caption_id}">{caption_html}</figcaption>\n</figure>\n'
            )
            output.append(figure)
            index += 1
            continue
        if node.type == "fence":
            label = node.info.strip() or "text"
            output.append(
                f'<div class="code-block"><div class="code-block-header">{html.escape(label)}</div>'
                f"<pre><code>{html.escape(node.content)}</code></pre></div>\n"
            )
            index += 1
            continue
        output.append(md.renderer.render([node], md.options, {}))
        index += 1
    body = "".join(output)
    body = body.replace("<table>", '<div class="table-wrap"><table>').replace(
        "</table>", "</table></div>"
    )
    return title, sections, body


def readme_intro(md) -> str:  # type: ignore[no-untyped-def]
    """The README's prose sections, without the metadata table and the Contents list."""
    text = (DESIGN / "README.md").read_text(encoding="utf-8")
    kept = []
    for chunk in re.split(r"(?m)^(?=## )", text):
        if not chunk.startswith("## ") or chunk.startswith("## Contents"):
            continue
        kept.append(chunk.replace("## ", "### ", 1))
    return md.render("\n".join(kept))


def main() -> int:
    try:
        from markdown_it import MarkdownIt
    except ImportError:
        print(
            "markdown-it-py is missing. Run this with the project's virtual environment: "
            ".venv/bin/python scripts/build_design_html.py",
            file=sys.stderr,
        )
        return 2

    meta = read_metadata()
    version = meta["version"]
    md = MarkdownIt("commonmark", {"html": False, "typographer": False}).enable("table")

    parts = []
    figures = [0]
    with tempfile.TemporaryDirectory(prefix="gtq-design-") as scratch:
        workdir = Path(scratch)
        for name in PARTS:
            number = name[:2]
            text = (DESIGN / name).read_text(encoding="utf-8")
            parts.append((number, *render_part(md, text, number, workdir, figures)))

    toc = ['<nav class="toc" aria-labelledby="toc-heading">', '<h2 id="toc-heading">Contents</h2>']
    toc.append('<ol><li><a href="#about">About this document</a></li>')
    for number, title, sections, _ in parts:
        toc.append(f'<li><a href="#part-{number}">{html.escape(title)}</a>')
        if sections:
            toc.append("<ol>")
            toc.extend(
                f'<li><a href="#{anchor}">{html.escape(heading)}</a></li>'
                for anchor, heading in sections
            )
            toc.append("</ol>")
        toc.append("</li>")
    toc.append("</ol></nav>")

    inline = md.renderInline
    hero = f"""<header class="hero">
<p class="eyebrow">System design document</p>
<h1>Golden Thread Quest: System Design</h1>
<p class="subtitle">How the local-first Golden Thread Quest application is designed and why,
what is finished, and what remains. Written for a developer or technical stakeholder new to
the system.</p>
<dl class="kv">
<dt>Version</dt><dd class="version">{html.escape(version)}</dd>
<dt>Date</dt><dd>{inline(meta["Date"])}</dd>
<dt>Describes</dt><dd>{inline(meta["Describes"])}</dd>
<dt>Audit status from</dt><dd>{inline(meta["Audit status from"])}</dd>
<dt>Source</dt><dd><code>docs/design/</code> (Markdown is the source of truth)</dd>
</dl>
</header>"""

    sections_html = [
        f'<section class="card" id="about"><h2>About this document</h2>{readme_intro(md)}</section>'
    ]
    sections_html.extend(
        f'<section class="card" aria-labelledby="part-{number}">{body}</section>'
        for number, _, _, body in parts
    )

    document = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="description" content="Golden Thread Quest system design, version {version}:
purpose, architecture, data and state, flows, security, decisions and status.">
<title>Golden Thread Quest System Design v{version}</title>
<style>{CSS}</style>
</head>
<body>
<div class="page">
{hero}
{"".join(toc)}
<main>
{"".join(sections_html)}
</main>
<footer class="page-footer">Golden Thread Quest system design, version {version}.
Rendered from <code>docs/design/</code> by <code>scripts/build_design_html.py</code>.</footer>
</div>
</body>
</html>
"""
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / f"golden-thread-system-design-v{version}.html"
    out.write_text(document, encoding="utf-8")
    print(f"wrote {out.relative_to(ROOT)} ({out.stat().st_size // 1024} KB, {figures[0]} figures)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
