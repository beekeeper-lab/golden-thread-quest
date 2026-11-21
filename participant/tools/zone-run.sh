#!/bin/bash
# Runs a command inside the operating-system lock for the base-camp-ownership-zones quest: a macOS
# sandbox that refuses every file write except into the zones where an agent may write, made by
# `zone-guard.mjs profile` from the Zones table in participant/context/zone-rules.md. Agent
# commands (and the guard itself) run inside it, so a write that skips the guard is still refused
# by the system.
#
#   bash participant/tools/zone-run.sh [--root <folder>] <command> [arguments...]
#
# --root is the repository (default: the current folder). The command's own exit code is returned;
# 2 means the lock couldn't be set up (and the command was not run). macOS only (sandbox-exec).
set -u
GUARD="$(cd -P -- "$(dirname -- "$0")" && pwd)/zone-guard.mjs"
ROOT=.
if [ "${1:-}" = "--root" ]; then
  [ $# -ge 2 ] || { echo "Usage: bash participant/tools/zone-run.sh [--root <folder>] <command> [arguments...]" >&2; exit 2; }
  ROOT=$2
  shift 2
fi
[ $# -ge 1 ] || { echo "Usage: bash participant/tools/zone-run.sh [--root <folder>] <command> [arguments...]" >&2; exit 2; }
command -v sandbox-exec > /dev/null || { echo "sandbox-exec isn't available (macOS only); the command was not run." >&2; exit 2; }
PROFILE=$(node "$GUARD" profile --root "$ROOT") || { echo "No lock could be made; the command was not run." >&2; exit 2; }
exec sandbox-exec -p "$PROFILE" "$@"
