# Regenerating the System Design

The Markdown files in `docs/design/` are the source of truth. The HTML and PDF are rendered
from them and are never edited by hand.

## The version rule

The version is `MAJOR.MINOR.PATCH`, held in `docs/design/VERSION`.

| Change | Bump | Example |
|---|---|---|
| Restructure: parts added, removed, merged or reordered | Major | 1.4.2 to 2.0.0 |
| New content, or the status of a new audit round | Minor | 1.0.0 to 1.1.0 |
| Corrections that change no structure and add no content | Patch | 1.1.0 to 1.1.1 |

The HTML and the PDF carry the same version in their file names
(`golden-thread-system-design-v<version>.html` and `.pdf`) and on their title page. The
README's metadata table carries it too, and the build refuses to run if the README and
`VERSION` disagree.

## Requirements

- The project's virtual environment (`make setup`), which provides `markdown-it-py`.
- The Mermaid CLI, `mmdc`, on `PATH`: `npm install -g @mermaid-js/mermaid-cli`. To use
  another command, set `GTQ_MMDC`, for example `GTQ_MMDC="npx -y @mermaid-js/mermaid-cli"`.
- Chromium for the PDF. The script runs `chromium`; set `CHROMIUM` to use another binary.
- Optional: `pdfinfo` and `pdftoppm` (poppler) to check the result.

## Steps

1. Edit the Markdown parts. Keep every diagram based on the code, and keep every printed
   `quest-app action` command runnable as printed, with `--confirm` on the actions that
   need it (`start-quest`, `submit-for-review`, `record-review`).
2. Choose the new version by the rule above. Write it to `docs/design/VERSION`. In
   `docs/design/README.md`, update the Version, Date and Describes rows (and the Audit status
   row if the audit status came from a branch) and the two file names in the Rendered copies
   row.
3. Add an entry at the top of `docs/design/CHANGELOG.md`.
4. Remove the previous version's rendered files. Git history keeps them:

   ```bash
   git rm artifacts/html/design/golden-thread-system-design-v*.html artifacts/pdf/design/golden-thread-system-design-v*.pdf
   ```

5. Render the HTML, then the PDF from it:

   ```bash
   .venv/bin/python scripts/build_design_html.py
   scripts/build_design_pdf.sh
   ```

6. Check the result. Open the HTML in a browser. In the PDF, confirm the title page shows
   the new version and that no figure is split or cut off; figures never break across pages,
   so a figure too tall for one page is scaled down and should be redrawn smaller:

   ```bash
   pdfinfo artifacts/pdf/design/golden-thread-system-design-v$(cat docs/design/VERSION).pdf
   pdftoppm -r 50 -png artifacts/pdf/design/golden-thread-system-design-v$(cat docs/design/VERSION).pdf /tmp/design-page
   ```

7. Run the repository gates, which include the secret scan and the documentation tests:

   ```bash
   make check
   ```

8. Commit the Markdown, `VERSION`, `CHANGELOG.md` and both rendered files together.

## How the rendering works

`scripts/build_design_html.py` reads the eight parts in order, renders the Markdown with
`markdown-it-py`, turns each Mermaid block into inline SVG with `mmdc` (plain SVG text, ELK
layout unless a block's own front matter chooses another), takes an italic paragraph starting
with "Figure" right after a diagram as its caption, and writes one self-contained file: inline
CSS, no script, no remote resource. `scripts/build_design_pdf.sh` prints that file with
headless Chromium, so the PDF matches the HTML's print layout.
