#!/usr/bin/env python3
"""A fake bug tracker, standing in for something like Jira, to show safe agent writes.

Part of the base-camp-repository-safety quest (see participant/context/repository-ownership.md).
Standard library only. Run from the repository root:

    .venv/bin/python participant/tools/fake-bug-tracker.py list
    .venv/bin/python participant/tools/fake-bug-tracker.py file --key BUG-101 --severity High \
        --title "Firefox warns about a typed password nobody typed (Account page)"

The "outside system" is a file, local-data/fake-bug-tracker/defects.json, which Git ignores. Nothing
real is touched. Every run follows the rules a real integration must:

  1. Credentials come only from the environment: FAKE_BUG_TRACKER_TOKEN must be set. It is never
     printed, logged or stored.
  2. A write is previewed first and only happens after the person types exactly "yes" at a
     terminal. An answer piped or redirected in is refused. (A program that fakes a terminal could
     still answer; this stops the simple case, not a determined one.)
  3. Each defect has a key; if that key already exists, nothing is filed (no duplicates).
  4. Before writing, the intended write is noted in local-data/fake-bug-tracker/pending.json. A run
     that is cut off part way is settled by the next run: if the defect was written, it is not
     written again; if it wasn't, nothing half-done is left behind.
  5. Every read, preview, write, skip, cancellation and refusal is added to
     participant/context/audit-log.md with the time, action, target, actor, outcome and
     whether a write was confirmed.

For the recovery demonstration only: FAKE_BUG_TRACKER_SIMULATE_CRASH=after-write stops the run
the instant the defect is written, before the run can record that it finished.
"""

from __future__ import annotations

import argparse
import datetime as dt
import getpass
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

TOOL = "participant/tools/fake-bug-tracker.py"
VERSION = "1.2.0"
STORE_DIR = Path("local-data/fake-bug-tracker")
STORE = STORE_DIR / "defects.json"
PENDING = STORE_DIR / "pending.json"
AUDIT = Path("participant/context/audit-log.md")
KEY = re.compile(r"^[A-Z][A-Z0-9]{1,9}-[0-9]{1,6}$")
CRASH_EXIT = 75
SEVERITIES = ("Critical", "High", "Medium", "Low")

AUDIT_HEADER = """# Audit log

Every action my tools take, newest last. Written by `participant/tools/fake-bug-tracker.py`; never
edited by hand. Times are UTC. "Write confirmed" says whether a person typed `yes` before a
write: `yes`, `no` (asked and declined), `asked` (a preview, waiting for the answer), `not asked` (nothing to write, or refused before asking) or `n/a (read)`.

| Time (UTC) | Action | Target | Actor | Outcome | Write confirmed |
|---|---|---|---|---|---|
"""


class Refused(Exception):
    """The run stops without writing; the message says why."""


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def actor() -> str:
    try:
        name = subprocess.run(["git", "config", "user.name"], capture_output=True, text=True, timeout=5).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        name = ""
    return f"{name or getpass.getuser()} via fake-bug-tracker.py"


def cell(value: str) -> str:
    """One Markdown table cell, kept on one line and unable to add a column."""
    return " ".join(str(value).split()).replace("\\", "\\\\").replace("|", "\\|")


def write_atomically(path: Path, text: str) -> None:
    """Writes the whole file or nothing; the temporary file is always removed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    temp = Path(name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        os.chmod(temp, 0o644)
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)


def audit(action: str, target: str, outcome: str, confirmed: str) -> None:
    existing = AUDIT.read_text(encoding="utf-8") if AUDIT.exists() else AUDIT_HEADER
    row = f"| {now()} | {cell(action)} | {cell(target)} | {cell(actor())} | {cell(outcome)} | {cell(confirmed)} |\n"
    write_atomically(AUDIT, existing + row)


def load_items() -> list[dict]:
    if not STORE.exists():
        return []
    try:
        data = json.loads(STORE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise Refused(f"{STORE} is not valid JSON; it was left as it is") from None
    if not isinstance(data, list):
        raise Refused(f"{STORE} is not a list of defects; it was left as it is")
    # Every entry must be a whole defect, so a damaged file is refused clearly instead of crashing.
    for n, d in enumerate(data, start=1):
        if not (
            isinstance(d, dict)
            and isinstance(d.get("key"), str) and KEY.fullmatch(d["key"])
            and d.get("severity") in SEVERITIES
            and all(isinstance(d.get(f), str) and d[f] for f in ("title", "filed_at", "filed_by"))
        ):
            raise Refused(f"{STORE} entry {n} is not a complete defect; the file was left as it is for a person to check")
    return data


def find(items: list[dict], key: str) -> dict | None:
    return next((item for item in items if item.get("key") == key), None)


def require_token() -> None:
    if not os.environ.get("FAKE_BUG_TRACKER_TOKEN", "").strip():
        raise Refused(
            "FAKE_BUG_TRACKER_TOKEN is not set. Set it for this terminal only, without it showing on "
            "screen:  read -rs FAKE_BUG_TRACKER_TOKEN && export FAKE_BUG_TRACKER_TOKEN"
        )


def settle_pending(defects: list[dict]) -> None:
    """Finishes the bookkeeping of a run that was cut off, without repeating its write."""
    if not PENDING.exists():
        return
    try:
        pending = json.loads(PENDING.read_text(encoding="utf-8"))
        key = pending["key"]
        if not (isinstance(key, str) and KEY.fullmatch(key)):
            raise TypeError
    except (json.JSONDecodeError, UnicodeDecodeError, KeyError, TypeError):
        raise Refused(f"{PENDING} is unreadable; it was left as it is for a person to check") from None
    if find(defects, key):
        print(f"recovery: an earlier run was cut off after filing {key}; it is there, so it is not filed again")
        audit("recover", key, "earlier run was cut off after the write; defect exists, nothing repeated", "yes (earlier run)")
    else:
        print(f"recovery: an earlier run was cut off before filing {key}; nothing was filed")
        audit("recover", key, "earlier run was cut off before the write; nothing had been filed", "yes (earlier run)")
    PENDING.unlink()


def cmd_list() -> int:
    require_token()
    defects = load_items()
    settle_pending(defects)  # a list straight after a cut-off run settles it too
    print(f"read {len(defects)} defect(s) from the fake bug tracker")
    for d in defects:
        print(f"  {d['key']} [{d['severity']}]: {d['title']} (filed {d['filed_at']})")
    audit("read", "fake bug tracker: all defects", f"{len(defects)} defect(s) listed", "n/a (read)")
    return 0


def cmd_file(key: str, severity: str, title: str) -> int:
    if not KEY.fullmatch(key):
        raise Refused("the key must look like BUG-101: 2 to 10 capital letters or digits, a hyphen, then 1 to 6 digits")
    title = " ".join(title.split())
    if not title or len(title) > 200:
        raise Refused("the title must be 1 to 200 characters")
    require_token()
    defects = load_items()
    settle_pending(defects)

    existing = find(defects, key)
    if existing:
        print(f"{key} is already filed ({existing['filed_at']}): nothing to file, nothing written")
        audit("file defect", key, "skipped: already filed, no duplicate created", "not asked")
        return 0

    defect = {"key": key, "severity": severity, "title": title, "filed_at": now(), "filed_by": actor()}
    print("preview: this defect would be filed in the fake bug tracker:")
    print("  " + json.dumps({k: defect[k] for k in ("key", "severity", "title")}, ensure_ascii=False))
    audit("preview", key, f"would file [{severity}]: {title}", "asked")
    if not sys.stdin.isatty():
        # Confirmation has to come from a person at the keyboard, not from piped or redirected input.
        raise Refused("confirmation must be typed at a terminal; piped or redirected input can't confirm a write")
    try:
        answer = input('Type "yes" to file it, anything else to cancel: ')
    except EOFError:
        answer = ""
    except KeyboardInterrupt:
        # Ctrl-C at the prompt is a cancellation like any other, and is audited as one.
        print("\ncancelled with Ctrl-C: nothing written")
        audit("file defect", key, "cancelled by the person (Ctrl-C), nothing written", "no")
        return 1
    print(f"answer: {answer!r}")
    if answer.strip() != "yes":
        print("cancelled: nothing written")
        audit("file defect", key, "cancelled by the person, nothing written", "no")
        return 1

    # Note the write before doing it, so a run cut off from here on can be settled by the next one.
    write_atomically(PENDING, json.dumps({"key": key, "noted_at": now()}) + "\n")
    write_atomically(STORE, json.dumps(defects + [defect], indent=2, ensure_ascii=False) + "\n")
    if os.environ.get("FAKE_BUG_TRACKER_SIMULATE_CRASH") == "after-write":
        print(f"SIMULATED CRASH: stopped right after writing {key}, before recording that the run finished")
        sys.stdout.flush()
        os._exit(CRASH_EXIT)
    # Record the confirmed write before removing the note, so a run cut off in between is still settled.
    audit("file defect", key, f"filed [{severity}]: {title}", "yes")
    PENDING.unlink()
    print(f"filed {key}")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="A fake bug tracker for showing safe, audited writes.")
    sub = ap.add_subparsers(dest="command", required=True)
    sub.add_parser("list", help="read every defect (a read action)")
    file_cmd = sub.add_parser("file", help="preview, confirm and file one defect (a write action)")
    file_cmd.add_argument("--key", required=True, help="e.g. BUG-101")
    file_cmd.add_argument("--severity", required=True, choices=SEVERITIES)
    file_cmd.add_argument("--title", required=True)
    args = ap.parse_args(argv)

    shown = " ".join(json.dumps(a) if re.search(r"\s", a) else a for a in (argv if argv is not None else sys.argv[1:]))
    print(f"$ .venv/bin/python {TOOL} {shown}")
    print(f"# run at {now()} by {TOOL} {VERSION}")
    if not (Path("participant").is_dir() and Path(".gitignore").is_file()):
        print("REFUSED: run this from the root of the quest repository (the folder with participant/ in it)")
        return 1
    try:
        status = cmd_list() if args.command == "list" else cmd_file(args.key, args.severity, args.title)
    except Refused as e:
        print(f"REFUSED: {e}")
        target = getattr(args, "key", "fake bug tracker")
        try:
            audit("read" if args.command == "list" else "file defect", target, f"refused: {e}", "not asked")
        except OSError:
            pass
        status = 1
    print(f"exit status {status}")
    return status


if __name__ == "__main__":
    sys.exit(main())
