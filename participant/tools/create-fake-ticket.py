"""Create one fake ticket in a pretend outside system, safely.

This stands in for a real integration (Jira, Trello, GitHub) without touching one.
The "outside system" is a local file in local-data/, which Git ignores.

What it shows:
  1. A write is previewed and only happens after a person types "yes".
  2. Running it again creates no duplicate: the ticket is matched by its key.
  3. Every run is recorded in participant/context/audit-log.md.
  4. Stopping it part way (Ctrl-C, or answering anything but "yes") changes nothing.

Run from the repository folder:
  python3 participant/tools/create-fake-ticket.py
"""

from __future__ import annotations

import getpass
import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

# Narrow, explicit paths, worked out from where this file lives, never from an
# environment variable. participant/tools/ -> repository root is two folders up.
REPO = Path(__file__).resolve().parents[2]
STORE = REPO / "local-data" / "fake-tracker.json"
AUDIT_LOG = REPO / "participant" / "context" / "audit-log.md"

TICKET = {
    "key": "GTQ-DEMO-1",
    "title": "Fake ticket for the Base Camp rerun test",
    "system": "fake tracker (local file, not a real service)",
}


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def say(text: str = "") -> None:
    # Flush every line so output saved with `tee` shows up in order.
    print(text, flush=True)


def audit(kind: str, action: str, confirmed: str, outcome: str) -> None:
    """Add one row to the bottom of the audit log table. Old rows are never touched."""
    actor = f"{getpass.getuser()} (ran create-fake-ticket.py)"
    target = f"`local-data/fake-tracker.json`, key `{TICKET['key']}`"
    row = f"| {now()} | {kind} | {action} | {target} | {actor} | {confirmed} | {outcome} |\n"
    with AUDIT_LOG.open("a", encoding="utf-8") as log:
        log.write(row)


def load_store() -> list[dict]:
    if not STORE.exists():
        return []
    return json.loads(STORE.read_text(encoding="utf-8"))


def save_store(items: list[dict]) -> None:
    """Write to a temporary file, then swap it in, so an interruption mid-write
    leaves either the old file or the new one, never half of one."""
    STORE.parent.mkdir(exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=STORE.parent, prefix=".fake-tracker-", suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(items, f, indent=2)
        f.write("\n")
    os.replace(tmp, STORE)


def main() -> int:
    say(f"Run started {now()} UTC")
    say(f"Fake outside system: {STORE.relative_to(REPO)}")

    items = load_store()
    existing = [item for item in items if item.get("key") == TICKET["key"]]
    say(f"Read: {len(items)} item(s) in the fake system; {len(existing)} with key {TICKET['key']}")

    if existing:
        say(f"{TICKET['key']} already exists (matched by key). Nothing created.")
        audit("read", "Checked for the fake ticket before creating it", "n/a",
              "Already exists. Nothing created (no duplicate).")
        return 0

    say()
    say("PREVIEW: this is the exact write that would happen:")
    say(json.dumps(TICKET, indent=2))
    say()
    try:
        answer = input("Type yes to create it, anything else to cancel: ")
    except (KeyboardInterrupt, EOFError):
        say()
        say("Stopped before confirming. Nothing created.")
        audit("external write (preview only)", "Previewed creating the fake ticket", "No",
              "Interrupted at the prompt. Nothing created.")
        return 1

    say(f"You typed: {answer!r}")
    if answer.strip().lower() != "yes":
        say("Not confirmed. Nothing created.")
        audit("external write (preview only)", "Previewed creating the fake ticket", "No",
              "Cancelled. Nothing created.")
        return 1

    created = dict(TICKET, created_at=f"{now()} UTC")
    save_store(items + [created])
    say(f"Created {TICKET['key']}.")
    audit("external write (simulated)", "Created the fake ticket after preview", "Yes",
          "Created.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
