"""A chained, append-only audit log kept as a Markdown table.

Two commands, and no others:
  python3 auditlog.py append LOG --kind ... --action ... --target ... --actor ...
                                 --confirmed ... --outcome ... [--ref N]
  python3 auditlog.py check LOG [--anchor-git-ref REF]

There is no edit or delete command. The format is described in
participant/context/audit-log-format.md.

How edits are caught:
  - The file must be exactly the tool's fixed heading followed by rows written exactly as
    the tool writes them. Anything added above, between or below the rows fails the check.
  - Every row ends with a chain value: the first 16 hex characters of
    sha256(previous chain + "\n" + the row's nine other cells joined with "|").
    Changing, removing or moving a row breaks its chain or the next row's.
  - An anchor file beside the log (same name, ".anchor") holds the row count and the
    last chain value. Cutting rows off the end, or recomputing every chain after an
    edit, no longer matches the anchor.
  - The anchor on disk can be rewritten too, so `check --anchor-git-ref REF` compares
    against the anchor as it was committed at REF.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import subprocess
import sys
import tempfile
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

KINDS = ("read", "preview", "confirmed write", "failure", "recovery")
COLUMNS = ("Seq", "Time (UTC)", "Kind", "Action", "Target", "Actor", "Confirmed", "Outcome",
           "Ref", "Chain")
REQUIRED = {3: "action", 4: "target", 5: "actor", 6: "confirmed", 7: "outcome"}
GENESIS = "GENESIS"
TIME_FORMAT = "%Y-%m-%d %H:%M:%S"

HEADER = (
    "# Audit log (chained)\n"
    "\n"
    "Written only by `auditlog.py append`. New rows go at the bottom. Earlier rows are never\n"
    "edited or removed; a correction is a new row. The fields, the five kinds and the chain\n"
    "are explained in `participant/context/audit-log-format.md`.\n"
    "\n"
    "| " + " | ".join(COLUMNS) + " |\n"
    "|" + "---|" * len(COLUMNS) + "\n"
)

# A short list of credential shapes. It is not a complete secret scanner.
SECRET_RULES = (
    ("bearer token", re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._\-]{8,}")),
    ("named secret with a value",
     re.compile(r"(?i)\b(password|passwd|pwd|secret|token|api[_-]?key)\b\s*[=:]\s*\S+")),
    ("known token prefix",
     re.compile(r"\b(ATATT|AKIA|gh[pousr]_|sk-|xox[abprs]-)[A-Za-z0-9*_\-]{4,}")),
    ("private key block", re.compile(r"-----BEGIN")),
    ("partly masked value", re.compile(r"[A-Za-z0-9]{2,}\*{3,}|\*{3,}[A-Za-z0-9]{2,}")),
    ("long opaque value", re.compile(r"\b(?=[A-Za-z0-9+_=]*[0-9])(?=[A-Za-z0-9+_=]*[A-Za-z])"
                                     r"[A-Za-z0-9+_=]{32,}\b")),
)


class AuditError(Exception):
    """The log refused something. The message never repeats the refused value."""


def chain_of(prev: str, cells9: list[str]) -> str:
    return hashlib.sha256((prev + "\n" + "|".join(cells9)).encode("utf-8")).hexdigest()[:16]


def secret_rule(text: str) -> str | None:
    for name, pattern in SECRET_RULES:
        if pattern.search(text):
            return name
    return None


def unsafe_character(text: str) -> bool:
    """True for a |, or any control, format or line/paragraph separator character
    (line breaks, tabs, U+2028, zero-width and direction-override characters)."""
    return any(c == "|" or unicodedata.category(c) in ("Cc", "Cf", "Zl", "Zp") for c in text)


def earlier_row(ref: str, i: int) -> int | None:
    """Ref as a row number, if it is plain digits naming a row before row i."""
    if ref.isascii() and ref.isdigit() and 1 <= int(ref) < i:
        return int(ref)
    return None


def split_row(line: str) -> list[str]:
    return [c.strip() for c in line.strip().strip("|").split("|")]


def format_row(cells: list[str]) -> str:
    return "| " + " | ".join(cells) + " |\n"


def anchor_path(log: Path) -> Path:
    return log.with_suffix(".anchor")


def read_rows(log: Path) -> tuple[list[list[str]], list[str]]:
    """Return (rows, problems). The file must be the fixed heading, then nothing but rows,
    each byte-for-byte as format_row writes it."""
    try:
        text = log.read_bytes().decode("utf-8")
    except UnicodeDecodeError:
        return [], ["the file is not valid UTF-8 text"]
    if not text.startswith(HEADER):
        return [], ["the text above the rows is not the tool's fixed heading (it was changed, "
                    "or something was put above the table)"]
    problems: list[str] = []
    rows: list[list[str]] = []
    body = text[len(HEADER):]
    if body and not body.endswith("\n"):
        problems.append("the last line does not end with a line break")
    lines = body.split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    for number, line in enumerate(lines, start=1):
        cells = split_row(line)
        if len(cells) != len(COLUMNS):
            problems.append(f"line {number} after the heading is not a log row with "
                            f"{len(COLUMNS)} cells")
            continue
        if format_row(cells) != line + "\n":
            problems.append(f"line {number} after the heading is not written exactly as the "
                            "tool writes a row (spacing or line ending was changed)")
        rows.append(cells)
    return rows, problems


def parse_anchor(text: str) -> tuple[int, str] | None:
    found = dict(re.findall(r"(?m)^(rows|head):\s*(\S+)\s*$", text))
    if "rows" not in found or "head" not in found or not found["rows"].isdigit():
        return None
    return int(found["rows"]), found["head"]


def verify_rows(rows: list[list[str]]) -> list[str]:
    problems: list[str] = []
    prev_chain = GENESIS
    prev_time: datetime | None = None
    for i, cells in enumerate(rows, start=1):
        seq, when, kind, _action, target, _actor, _confirmed, _outcome, ref, chain = cells
        where = f"row {i}"
        if seq != str(i):
            problems.append(f"{where}: sequence number is {seq!r}, expected {i} "
                            "(a row was removed, added or moved)")
        if chain != chain_of(prev_chain, cells[:9]):
            problems.append(f"{where}: chain value does not match its contents and the row "
                            "before it (this row was changed, or a row before it was removed "
                            "or moved)")
        prev_chain = chain
        try:
            this_time = datetime.strptime(when, TIME_FORMAT)
        except ValueError:
            problems.append(f"{where}: time is missing or not in the form YYYY-MM-DD HH:MM:SS")
        else:
            if prev_time is not None and this_time < prev_time:
                problems.append(f"{where}: time is earlier than the row before it")
            prev_time = this_time
        if kind not in KINDS:
            problems.append(f"{where}: kind is not one of {', '.join(KINDS)}")
        for col, name in REQUIRED.items():
            if not cells[col]:
                problems.append(f"{where}: {name} is empty")
        needs = {"confirmed write": "preview", "recovery": "failure"}.get(kind)
        if needs:
            named = earlier_row(ref, i)
            earlier = rows[named - 1] if named else None
            if earlier is None or earlier[2] != needs:
                problems.append(f"{where}: a {kind} must name an earlier {needs} row in Ref")
            elif kind == "confirmed write" and earlier[4] != target:
                problems.append(f"{where}: the preview in Ref is for a different target")
        elif ref and earlier_row(ref, i) is None:
            problems.append(f"{where}: Ref does not name an earlier row")
        for col in range(1, 9):
            if unsafe_character(cells[col]):
                problems.append(f"{where}: {COLUMNS[col]} holds a control or hidden character")
            rule = secret_rule(cells[col])
            if rule:
                problems.append(f"{where}: {COLUMNS[col]} looks like it holds a credential "
                                f"({rule})")
    return problems


def verify_anchor(rows: list[list[str]], anchor: tuple[int, str] | None, label: str,
                  exact: bool) -> list[str]:
    if anchor is None:
        return [f"{label} is missing or unreadable"]
    count, head = anchor
    if len(rows) < count:
        return [f"{label} records {count} rows but the log has {len(rows)} "
                "(rows were removed from the end)"]
    if exact and len(rows) > count:
        return [f"{label} records {count} rows but the log has {len(rows)} "
                "(rows were added without the tool)"]
    actual = rows[count - 1][9] if count else GENESIS
    if actual != head:
        return [f"{label} does not match row {count}'s chain value "
                "(earlier rows were rewritten)"]
    return []


def verify(log: Path, git_ref: str | None = None) -> tuple[list[list[str]], list[str]]:
    if not log.exists():
        return [], [f"no log at {log}"]
    rows, problems = read_rows(log)
    problems += verify_rows(rows)
    anchor_file = anchor_path(log)
    local = parse_anchor(anchor_file.read_text(encoding="utf-8")) if anchor_file.exists() else None
    problems += verify_anchor(rows, local, "anchor file", exact=True)
    if git_ref:
        shown = subprocess.run(["git", "show", f"{git_ref}:./{anchor_file.name}"],
                               cwd=log.resolve().parent, capture_output=True, text=True)
        committed = parse_anchor(shown.stdout) if shown.returncode == 0 else None
        problems += verify_anchor(rows, committed, f"anchor committed at {git_ref}", exact=False)
    return rows, problems


def append(log: Path, *, kind: str, action: str, target: str, actor: str, confirmed: str,
           outcome: str, ref: str = "", now: datetime | None = None) -> int:
    """Add one row at the bottom and update the anchor. Returns the new row's number.
    Raises AuditError, leaving both files untouched, if anything is wrong."""
    fields = {"kind": kind, "action": action, "target": target, "actor": actor,
              "confirmed": confirmed, "outcome": outcome, "ref": ref}
    fields = {k: v.strip() for k, v in fields.items()}
    if fields["kind"] not in KINDS:
        raise AuditError(f"kind must be one of: {', '.join(KINDS)}")
    for name, value in fields.items():
        if not value and name != "ref":
            raise AuditError(f"{name} is empty")
        if unsafe_character(value):
            raise AuditError(f"{name} contains a |, a line break or a control or hidden "
                             "character")
        rule = secret_rule(value)
        if rule:
            raise AuditError(f"{name} looks like it holds a credential ({rule}); "
                             "log the target's identifier instead")

    if log.exists():
        rows, problems = verify(log)
        if problems:
            raise AuditError("the existing log does not pass its check, so nothing was added: "
                             + problems[0])
    else:
        rows = []

    when = (now or datetime.now(timezone.utc)).strftime(TIME_FORMAT)
    seq = len(rows) + 1
    cells = [str(seq), when, fields["kind"], fields["action"], fields["target"],
             fields["actor"], fields["confirmed"], fields["outcome"], fields["ref"]]
    prev = rows[-1][9] if rows else GENESIS
    cells.append(chain_of(prev, cells))
    problems = verify_rows(rows + [cells])
    if problems:
        raise AuditError(problems[0])

    if not log.exists():
        log.parent.mkdir(parents=True, exist_ok=True)
        with log.open("x", encoding="utf-8") as f:
            f.write(HEADER)
    with log.open("a", encoding="utf-8") as f:  # append mode: earlier bytes are not rewritten
        f.write(format_row(cells))
        f.flush()
        os.fsync(f.fileno())
    anchor = anchor_path(log)
    fd, tmp = tempfile.mkstemp(dir=anchor.parent, prefix=".anchor-", suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(f"rows: {seq}\nhead: {cells[9]}\n")
    os.replace(tmp, anchor)
    return seq


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Chained, append-only audit log.")
    sub = parser.add_subparsers(dest="command", required=True)
    p_append = sub.add_parser("append", help="add one row at the bottom")
    p_append.add_argument("log", type=Path)
    for name in ("kind", "action", "target", "actor", "confirmed", "outcome"):
        p_append.add_argument(f"--{name}", required=True)
    p_append.add_argument("--ref", default="")
    p_check = sub.add_parser("check", help="verify the chain, the rows and the anchor")
    p_check.add_argument("log", type=Path)
    p_check.add_argument("--anchor-git-ref", default=None,
                         help="also compare with the anchor file as committed at this Git ref")
    args = parser.parse_args(argv)

    if args.command == "append":
        try:
            seq = append(args.log, kind=args.kind, action=args.action, target=args.target,
                         actor=args.actor, confirmed=args.confirmed, outcome=args.outcome,
                         ref=args.ref)
        except AuditError as refused:
            print(f"REFUSED: {refused}. Nothing was written.", flush=True)
            return 2
        print(f"Appended row {seq}.", flush=True)
        return 0

    rows, problems = verify(args.log, args.anchor_git_ref)
    for problem in problems:
        print(f"PROBLEM: {problem}", flush=True)
    if problems:
        print(f"CHECK FAILED: {len(problems)} problem(s) in {len(rows)} row(s).", flush=True)
        return 1
    extra = f" and the anchor committed at {args.anchor_git_ref}" if args.anchor_git_ref else ""
    print(f"CHECK PASSED: {len(rows)} row(s), chain intact, matches the anchor file{extra}.",
          flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
