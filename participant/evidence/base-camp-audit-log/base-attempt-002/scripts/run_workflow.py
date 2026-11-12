"""Run one simulated piece of work and log every step in the chained audit log.

The work: change the assignee of a pretend ticket. The pretend tracker is a file in a
temporary folder that this run creates and removes. Nothing real is contacted.

The first attempt to write always fails (on purpose), so the log shows a failure and a
recovery as well as a read, a preview and a confirmed write.

Run from the repository folder and answer the two prompts yourself:
  python3 participant/evidence/base-camp-audit-log/base-attempt-002/scripts/run_workflow.py
"""

from __future__ import annotations

import argparse
import getpass
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import auditlog  # noqa: E402

REPO = Path(__file__).resolve().parents[5]
DEFAULT_LOG = REPO / "participant" / "context" / "audit-log-all-events.md"

TICKET_ID = "SIM-101"
OLD_ASSIGNEE = "user-a"
NEW_ASSIGNEE = "user-b"
# Made-up stand-ins for things a log must never hold. The tests look for them in the log.
SIM_PRIVATE_BODY = "Made-up private ticket text: the customer in unit 4 reported a leak."
SIM_PLANTED_LOGIN_VALUE = "made-up-not-a-real-credential-0000-sim-only"

# What the log may say about each error code. The error's own message is never logged,
# because a real system's error text can quote the record or the request.
REASONS = {"SIM_TIMEOUT": "the pretend tracker did not answer in time (code SIM_TIMEOUT)"}


class TrackerError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


class FakeTracker:
    """A pretend ticket system in one JSON file. Its first write fails, like a flaky service,
    and its error message carelessly quotes the ticket text and the credential."""

    def __init__(self, folder: Path):
        self.store = folder / "pretend-tracker.json"
        self.failures_left = 1
        self._save({TICKET_ID: {"assignee": OLD_ASSIGNEE, "body": SIM_PRIVATE_BODY}})

    def _load(self) -> dict:
        return json.loads(self.store.read_text(encoding="utf-8"))

    def _save(self, data: dict) -> None:
        self.store.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

    def assignee(self, ticket: str) -> str:
        return self._load()[ticket]["assignee"]

    def set_assignee(self, ticket: str, who: str) -> None:
        data = self._load()
        if self.failures_left:
            self.failures_left -= 1
            raise TrackerError("SIM_TIMEOUT",
                               f"timeout updating {ticket} (auth {SIM_PLANTED_LOGIN_VALUE}); "
                               f"record was: {data[ticket]['body']}")
        data[ticket]["assignee"] = who
        self._save(data)


def say(text: str = "") -> None:
    print(text, flush=True)


def shown(path: Path) -> str:
    """The path as printed: relative to the repository when it is inside it."""
    try:
        return str(path.resolve().relative_to(REPO))
    except ValueError:
        return str(path)


def ask(question: str) -> tuple[bool, str]:
    """Return (said yes, how the answer arrived)."""
    typed = sys.stdin.isatty()
    try:
        answer = input(question)
    except (KeyboardInterrupt, EOFError):
        say()
        return False, "No answer (stopped at the prompt)"
    say(f"Answer received: {answer!r}")
    if answer.strip().lower() != "yes":
        return False, "No"
    return True, ("Yes, typed at the prompt" if typed
                  else "Yes, but the answer was piped in, not typed by a person")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--log", type=Path, default=DEFAULT_LOG)
    args = parser.parse_args(argv)

    actor = f"{getpass.getuser()} (ran run_workflow.py)"
    target = f"pretend tracker, ticket {TICKET_ID}, field assignee"

    def log(kind: str, action: str, confirmed: str, outcome: str, ref: int | None = None) -> int:
        seq = auditlog.append(args.log, kind=kind, action=action, target=target, actor=actor,
                              confirmed=confirmed, outcome=outcome,
                              ref="" if ref is None else str(ref))
        say(f"  logged row {seq}: {kind}")
        return seq

    say(f"Audit log: {shown(args.log)}")
    with tempfile.TemporaryDirectory(prefix="pretend-tracker-") as folder:
        tracker = FakeTracker(Path(folder))
        say("Pretend tracker: a temporary file, removed when this run ends.")

        try:
            current = tracker.assignee(TICKET_ID)
            log("read", "Read the ticket's current assignee", "n/a",
                f"Done. Assignee is {current}. Nothing changed.")

            say()
            say("PREVIEW: this is the exact write that would happen:")
            say(f"  ticket {TICKET_ID}: assignee {current} -> {NEW_ASSIGNEE}")
            preview = log("preview",
                          f"Previewed changing the assignee from {current} to {NEW_ASSIGNEE}",
                          "Not yet. Asked at the prompt; the answer is in a later row.",
                          "Shown on screen. Nothing changed.")
            say()
            yes, how = ask("Type yes to make this change, anything else to cancel: ")
            if not yes:
                log("preview", "Closed the preview without writing", how,
                    "Cancelled. Nothing changed.", preview)
                say("Not confirmed. Nothing changed.")
                return 1

            change = f"Changed the assignee from {current} to {NEW_ASSIGNEE}"
            for attempt in (1, 2):
                try:
                    tracker.set_assignee(TICKET_ID, NEW_ASSIGNEE)
                except TrackerError as error:
                    reason = REASONS.get(error.code, "an error the tool does not recognise "
                                                     "(details withheld from the log)")
                    failure = log("failure",
                                  f"Tried to change the assignee from {current} to "
                                  f"{NEW_ASSIGNEE} (attempt {attempt})", how,
                                  f"Failed. Reason: {reason}. The tool does not yet know "
                                  "whether the change was applied.", preview)
                    say(f"The write failed: {reason}.")
                    found = tracker.assignee(TICKET_ID)
                    if found == NEW_ASSIGNEE:
                        log("recovery", "Read the ticket again after the failure", "n/a",
                            f"Assignee is already {found}. The change was applied despite "
                            "the error. No retry needed.", failure)
                        say("The change turned out to be applied. Nothing more to do.")
                        return 0
                    log("recovery", "Read the ticket again after the failure", "n/a",
                        f"Assignee is still {found}. The failed attempt changed nothing. "
                        "The same change can be tried again.", failure)
                    if attempt == 2:
                        say("Failed twice. Stopping. Nothing changed.")
                        return 1
                    say(f"The ticket is unchanged (assignee {found}).")
                    yes, how = ask("Type yes to try the same change again, "
                                   "anything else to stop: ")
                    if not yes:
                        log("preview", "Closed the preview without retrying", how,
                            "Stopped after the failure. Nothing changed.", preview)
                        say("Stopped. Nothing changed.")
                        return 1
                else:
                    log("confirmed write", change, how,
                        f"Done. Applied once, on attempt {attempt}.", preview)
                    break

            after = tracker.assignee(TICKET_ID)
            log("read", "Read the ticket back to confirm the change", "n/a",
                f"Done. Assignee is {after}.")
            say(f"Finished. Assignee is now {after}.")
            return 0
        except auditlog.AuditError as refused:
            say(f"STOPPED: the audit log refused a row ({refused}). "
                "No further action was taken.")
            return 3


if __name__ == "__main__":
    sys.exit(main())
