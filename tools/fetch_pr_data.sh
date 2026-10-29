#!/usr/bin/env bash
# Fetch a pull request's participant/ folder as DATA, for the pilot workflows.
#
# Usage: tools/fetch_pr_data.sh <pull-request-number> <output-folder>
# Needs REPO (owner/name) and GH_TOKEN, and must run in a checkout of the BASE repository.
# Writes <output-folder>/participant/, files.json (GitHub's changed-file list) and labels.json.
# Prints `sha=<commit>` to $GITHUB_OUTPUT when set. Nothing fetched is executed, and links are
# deleted, because a link in a pull request could point at the runner.
set -euo pipefail

number="${1:?pull request number}"
out="${2:?output folder}"
repo="${REPO:?REPO is required}"

mkdir -p "$out"
git fetch --no-tags --depth=1 origin "refs/pull/${number}/head"
sha=$(git rev-parse FETCH_HEAD)

if git cat-file -e FETCH_HEAD:participant 2>/dev/null; then
  git archive FETCH_HEAD participant | tar -x --no-same-owner --no-same-permissions -C "$out"
else
  mkdir -p "$out/participant"
fi
find "$out" -type l -delete

gh api --paginate --slurp "repos/${repo}/pulls/${number}/files?per_page=100" \
  | python3 -c 'import json,sys; print(json.dumps([r for page in json.load(sys.stdin) for r in page]))' \
  > "$out/files.json"
gh pr view "$number" --repo "$repo" --json labels --jq '[.labels[].name]' > "$out/labels.json"

if [ -n "${GITHUB_OUTPUT:-}" ]; then echo "sha=${sha}" >> "$GITHUB_OUTPUT"; fi
echo "fetched ${repo}#${number} at ${sha}"
