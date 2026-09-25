#!/usr/bin/env bash
# Render the system design PDF from its HTML, so the two match page for page.
#
#   scripts/build_design_pdf.sh
#
# Reads the version from docs/design/VERSION, renders
# artifacts/html/design/golden-thread-system-design-v<version>.html with headless Chromium,
# and writes artifacts/pdf/design/golden-thread-system-design-v<version>.pdf.
# Build the HTML first: .venv/bin/python scripts/build_design_html.py
# Set CHROMIUM to use a browser binary other than `chromium`.
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
version="$(tr -d '[:space:]' < "$root/docs/design/VERSION")"
if [[ ! "$version" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
  echo "docs/design/VERSION holds '$version', not MAJOR.MINOR.PATCH" >&2
  exit 1
fi

html="$root/artifacts/html/design/golden-thread-system-design-v$version.html"
pdf="$root/artifacts/pdf/design/golden-thread-system-design-v$version.pdf"
browser="${CHROMIUM:-chromium}"

if [[ ! -f "$html" ]]; then
  echo "missing $html; run .venv/bin/python scripts/build_design_html.py first" >&2
  exit 1
fi
if ! command -v "$browser" >/dev/null 2>&1; then
  echo "cannot find '$browser'; install Chromium or set CHROMIUM" >&2
  exit 1
fi

mkdir -p "$(dirname "$pdf")"
profile="$(mktemp -d)"
trap 'rm -rf "$profile"' EXIT

"$browser" --headless --disable-gpu --no-sandbox --user-data-dir="$profile" \
  --no-pdf-header-footer --print-to-pdf="$pdf" "file://$html" >/dev/null 2>&1

if [[ ! -s "$pdf" ]]; then
  echo "Chromium produced no PDF" >&2
  exit 1
fi
if command -v pdfinfo >/dev/null 2>&1; then
  pages="$(pdfinfo "$pdf" | awk '/^Pages:/ {print $2}')"
  echo "wrote ${pdf#"$root"/} ($pages pages)"
else
  echo "wrote ${pdf#"$root"/}"
fi
