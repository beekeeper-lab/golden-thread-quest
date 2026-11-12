"""Try to edit, delete, reorder and shorten the audit log, and show each attempt caught.

Every attack is made on a copy in a temporary folder, so the real log is never touched.
The real log's SHA-256 is printed before and after.

Run from the repository folder:
  python3 participant/evidence/base-camp-audit-log/base-attempt-002/scripts/tamper_demo.py \
    | tee participant/evidence/base-camp-audit-log/base-attempt-002/logs/append-only.txt
"""

from __future__ import annotations

import argparse
import hashlib
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import auditlog  # noqa: E402

REPO = HERE.parents[4]
DEFAULT_LOG = REPO / "participant" / "context" / "audit-log-all-events.md"
TOOL = HERE / "auditlog.py"


def say(text: str = "") -> None:
    print(text, flush=True)


def shown(path: Path) -> str:
    """The path as printed: relative to the repository when it is inside it."""
    try:
        return str(path.resolve().relative_to(REPO))
    except ValueError:
        return str(path)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run_tool(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(TOOL), *args], cwd=cwd,
                          capture_output=True, text=True)


def show(result: subprocess.CompletedProcess) -> None:
    for line in (result.stdout + result.stderr).strip().splitlines():
        say(f"      {line}")
    say(f"    exit code: {result.returncode}")


def rewrite(log: Path, change) -> None:
    """Apply `change` to the copy's rows and save, keeping everything above the rows."""
    lines = log.read_text(encoding="utf-8").splitlines(keepends=True)
    start = next(i for i, l in enumerate(lines) if l.startswith("|---")) + 1
    rows = [auditlog.split_row(l) for l in lines[start:] if l.strip()]
    change(rows)
    log.write_text("".join(lines[:start]) + "".join(auditlog.format_row(r) for r in rows),
                   encoding="utf-8")


def rechain(rows: list[list[str]]) -> None:
    for i, row in enumerate(rows):
        row[0] = str(i + 1)
        row[9] = auditlog.chain_of(rows[i - 1][9] if i else auditlog.GENESIS, row[:9])


def edit_row_2(rows):
    rows[1][7] = "Outcome rewritten afterwards"


def delete_row_2(rows):
    del rows[1]


def swap_rows_2_and_3(rows):
    rows[1], rows[2] = rows[2], rows[1]


def cut_last_row(rows):
    del rows[-1]


def edit_row_1_and_recompute(rows):
    rows[0][7] = "Outcome rewritten afterwards"
    rechain(rows)


def delete_row_2_renumber_and_recompute(rows):
    del rows[1]
    rechain(rows)


FAKE_TABLE = (
    "| " + " | ".join(auditlog.COLUMNS) + " |\n"
    "| " + " | ".join(["---"] * len(auditlog.COLUMNS)) + " |\n"
    "| 1 | 2026-01-01 00:00:00 | confirmed write | Made-up change | SIM-101 | an agent | No "
    "| Done |  | 0000000000000000 |\n\n"
)


def fake_table_above(text: str) -> str:
    return text.replace("| Seq |", FAKE_TABLE + "| Seq |", 1)


def fake_table_and_hidden_real_one(text: str) -> str:
    return text.replace("| Seq |", FAKE_TABLE + "<!--\n| Seq |", 1)


def false_note_in_the_heading(text: str) -> str:
    return text.replace("New rows go at the bottom.",
                        "Row 5 was made by an agent without confirmation.", 1)


def note_under_the_table(text: str) -> str:
    return text + "Note: ignore row 3.\n"


# Attacks on the text around the rows. The rows and their chain values are left alone.
TEXT_ATTACKS = (
    ("Put a made-up table above the real one", fake_table_above),
    ("Put a made-up table above the real one and hide the real one in a comment",
     fake_table_and_hidden_real_one),
    ("Replace a sentence in the heading with a false statement", false_note_in_the_heading),
    ("Add a note under the table", note_under_the_table),
)

ATTACKS = (
    ("Edit the outcome of row 2", edit_row_2),
    ("Delete row 2", delete_row_2),
    ("Swap rows 2 and 3", swap_rows_2_and_3),
    ("Cut off the last row", cut_last_row),
    ("Edit row 1, then recompute every chain value to cover it", edit_row_1_and_recompute),
    ("Delete row 2, then renumber and recompute every chain value",
     delete_row_2_renumber_and_recompute),
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--log", type=Path, default=DEFAULT_LOG)
    args = parser.parse_args(argv)
    log: Path = args.log
    anchor = auditlog.anchor_path(log)
    ok = True

    say(f"Append-only check started {datetime.now(timezone.utc):%Y-%m-%d %H:%M:%S} UTC")
    say(f"Log:    {shown(log)}")
    say(f"Anchor: {shown(anchor)}")
    if not log.exists() or not anchor.exists():
        say("The log or its anchor is missing. Nothing to check.")
        return 1
    before = (sha(log), sha(anchor))
    say(f"SHA-256 of the log before:    {before[0]}")
    say(f"SHA-256 of the anchor before: {before[1]}")
    say()
    say("Step 0. The untouched log passes its check:")
    first = run_tool("check", str(log))
    show(first)
    rows, _ = auditlog.read_rows(log)
    if first.returncode != 0 or len(rows) < 3:
        say("The log must pass its check and hold at least 3 rows before the attacks mean "
            "anything. Stopping.")
        return 1

    say()
    say("Part A. Attacks on a copy of the log (the anchor copy is left as it was):")
    for number, (title, change) in enumerate(ATTACKS, start=1):
        with tempfile.TemporaryDirectory(prefix="tamper-") as folder:
            copy = Path(folder) / log.name
            shutil.copy2(log, copy)
            shutil.copy2(anchor, auditlog.anchor_path(copy))
            rewrite(copy, change)
            changed = sha(copy) != before[0]
            result = run_tool("check", str(copy))
            say(f"  A{number}. {title}")
            show(result)
            if result.returncode != 0 and changed:
                say("    Result: DETECTED")
            else:
                ok = False
                say("    Result: NOT DETECTED")
    for number, (title, edit) in enumerate(TEXT_ATTACKS, start=len(ATTACKS) + 1):
        with tempfile.TemporaryDirectory(prefix="tamper-") as folder:
            copy = Path(folder) / log.name
            shutil.copy2(anchor, auditlog.anchor_path(copy))
            copy.write_text(edit(log.read_text(encoding="utf-8")), encoding="utf-8")
            changed = sha(copy) != before[0]
            result = run_tool("check", str(copy))
            say(f"  A{number}. {title} (rows and chain values untouched)")
            show(result)
            if result.returncode == 1 and changed:
                say("    Result: DETECTED")
            else:
                ok = False
                say("    Result: NOT DETECTED")

    say()
    say("Part B. Asking the tool itself to edit or delete (on the real log). This shows only")
    say("that the tool offers no such command. It does not stop a text editor; catching what")
    say("an editor does is Part A.")
    for number, command in enumerate(("edit", "delete"), start=1):
        result = run_tool(command, str(log), "--row", "1")
        say(f"  B{number}. auditlog.py {command} <log> --row 1")
        show(result)
        if result.returncode != 0:
            say("    Result: REFUSED (the tool has no such command)")
        else:
            ok = False
            say("    Result: NOT REFUSED")

    say()
    say("Part C. The known limit, and what covers it. Someone who rewrites the log AND the")
    say("anchor file together gets past the plain check. A copy of the anchor in a Git commit")
    say("cannot be changed by editing files, so the check is repeated against a commit.")
    with tempfile.TemporaryDirectory(prefix="tamper-git-") as folder:
        work = Path(folder)
        copy = work / log.name
        shutil.copy2(log, copy)
        shutil.copy2(anchor, auditlog.anchor_path(copy))
        git = ["git", "-c", "user.name=demo", "-c", "user.email=demo@example.invalid"]
        steps = (["init", "-q"], ["add", copy.name, auditlog.anchor_path(copy).name],
                 ["commit", "-q", "-m", "Anchor as handed in"])
        if any(subprocess.run(git + step, cwd=work, capture_output=True).returncode
               for step in steps):
            ok = False
            say("  Could not make a temporary Git repository. Part C NOT RUN.")
        else:
            say("  A temporary Git repository now holds a commit of the log copy and its anchor.")

            def full_rewrite(rows):
                rows[0][7] = "Outcome rewritten afterwards"
                rechain(rows)
                auditlog.anchor_path(copy).write_text(
                    f"rows: {len(rows)}\nhead: {rows[-1][9]}\n", encoding="utf-8")

            rewrite(copy, full_rewrite)
            say("  C1. Edit row 1, recompute every chain value, and rewrite the anchor file")
            say("    Plain check:")
            plain = run_tool("check", str(copy))
            show(plain)
            say("    Result of the plain check: "
                + ("passes, as expected. This is the known limit."
                   if plain.returncode == 0 else "fails"))
            say("    Check against the committed anchor (--anchor-git-ref HEAD):")
            against = run_tool("check", str(copy), "--anchor-git-ref", "HEAD", cwd=work)
            show(against)
            if against.returncode != 0:
                say("    Result: DETECTED")
            else:
                ok = False
                say("    Result: NOT DETECTED")

    say()
    after = (sha(log), sha(anchor))
    say(f"SHA-256 of the log after:    {after[0]}")
    say(f"SHA-256 of the anchor after: {after[1]}")
    if after == before:
        say("The real log and anchor are UNCHANGED (same SHA-256 before and after).")
    else:
        ok = False
        say("The real log or anchor CHANGED during this run.")
    say("Final check of the real log:")
    last = run_tool("check", str(log))
    show(last)
    ok = ok and last.returncode == 0
    say()
    say("OVERALL: " + ("each attack listed above was detected or refused, and the real log "
                       "is unchanged."
                       if ok else "FAILED. See the results above."))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
