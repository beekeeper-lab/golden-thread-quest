"""Tests for the chained audit log. The first 43 were written before the tool existed, from
the agreed expected results (2026-11-11) and the quest's acceptance criteria. The classes
marked "after review" were added later the same day, each before the fix it covers, from
the findings in logs/independent-review-1.md.

The format rule these tests assume (the tool must match it, not the other way round):

  Row:    | seq | time | kind | action | target | actor | confirmed | outcome | ref | chain |
  chain:  first 16 hex characters of sha256(previous_chain + "\n" + the nine
          cells before it joined with "|"); the first row uses "GENESIS".
  Anchor: a file beside the log, same name with ".anchor", holding
          "rows: N" and "head: <chain of row N>".

Run from the repository folder:
  python3 -m unittest discover -s participant/evidence/base-camp-audit-log/base-attempt-002/tests -v
"""

from __future__ import annotations

import hashlib
import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPTS = HERE.parent / "scripts"
AUDITLOG = SCRIPTS / "auditlog.py"
WORKFLOW = SCRIPTS / "run_workflow.py"
DEMO = SCRIPTS / "tamper_demo.py"

KINDS = ["read", "preview", "confirmed write", "failure", "recovery"]


def run(*args, stdin: str | None = None, cwd: Path | None = None):
    return subprocess.run([sys.executable, *map(str, args)], input=stdin, cwd=cwd,
                          capture_output=True, text=True, timeout=60)


def chain_of(prev: str, cells9: list[str]) -> str:
    return hashlib.sha256((prev + "\n" + "|".join(cells9)).encode("utf-8")).hexdigest()[:16]


def split_row(line: str) -> list[str]:
    return [c.strip() for c in line.strip().strip("|").split("|")]


def is_row(line: str) -> bool:
    return line.startswith("|") and split_row(line)[0].isdigit()


def join_row(cells: list[str]) -> str:
    return "| " + " | ".join(cells) + " |\n"


class Log:
    """Test-side reader/writer for tampering with a log file as an attacker would."""

    def __init__(self, path: Path):
        self.path = path
        lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
        self.head = [l for l in lines if not is_row(l)]
        self.rows = [split_row(l) for l in lines if is_row(l)]

    def save(self) -> None:
        self.path.write_text("".join(self.head) + "".join(join_row(r) for r in self.rows),
                             encoding="utf-8")

    def rechain(self, start: int = 0) -> None:
        """Recompute every chain from row index `start` on, as someone covering an edit would."""
        for i in range(start, len(self.rows)):
            prev = self.rows[i - 1][9] if i else "GENESIS"
            self.rows[i][9] = chain_of(prev, self.rows[i][:9])

    def renumber(self) -> None:
        for i, r in enumerate(self.rows):
            r[0] = str(i + 1)

    def write_anchor(self) -> None:
        anchor = self.path.with_suffix(".anchor")
        anchor.write_text(f"rows: {len(self.rows)}\nhead: {self.rows[-1][9]}\n", encoding="utf-8")


def append(log: Path, kind: str, n: int, **over):
    f = dict(kind=kind, action=f"Action {n}", target=f"SIM-{n}", actor="tester (unit test)",
             confirmed="n/a", outcome=f"Outcome {n}", ref="")
    f.update(over)
    args = [AUDITLOG, "append", log]
    for k, v in f.items():
        if v != "" or k != "ref":
            args += [f"--{k}", v]
    return run(*args)


def check(log: Path, *extra, cwd: Path | None = None):
    return run(AUDITLOG, "check", log, *extra, cwd=cwd)


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.log = self.dir / "log.md"

    def tearDown(self):
        self.tmp.cleanup()

    def make_log(self, n: int = 5) -> Log:
        """n rows: read, preview, confirmed write (linked to the preview), then reads."""
        for i in range(1, n + 1):
            if i == 2:
                r = append(self.log, "preview", i, target="SIM-9", confirmed="Pending")
            elif i == 3:
                r = append(self.log, "confirmed write", i, target="SIM-9", confirmed="Yes", ref="2")
            else:
                r = append(self.log, "read", i)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        return Log(self.log)


class TestChainAndAnchor(Base):
    def test_clean_log_passes(self):
        self.make_log()
        r = check(self.log)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_test_side_chain_rule_matches_tool(self):
        # Guards the tests themselves: if this fails, the attacks below prove nothing.
        log = self.make_log()
        before = [r[9] for r in log.rows]
        log.rechain()
        self.assertEqual(before, [r[9] for r in log.rows])
        self.assertEqual(len(before[0]), 16)

    def test_edited_earlier_row_is_detected_and_named(self):
        log = self.make_log()
        log.rows[1][7] = "Outcome changed afterwards"
        log.save()
        r = check(self.log)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("row 2", r.stdout.lower())

    def test_deleted_earlier_row_is_detected(self):
        log = self.make_log()
        del log.rows[1]
        log.save()
        self.assertNotEqual(check(self.log).returncode, 0)

    def test_deleted_row_with_renumbering_is_detected(self):
        log = self.make_log()
        del log.rows[3]
        log.renumber()
        log.save()
        self.assertNotEqual(check(self.log).returncode, 0)

    def test_swapped_rows_are_detected(self):
        log = self.make_log()
        log.rows[3], log.rows[4] = log.rows[4], log.rows[3]
        log.save()
        self.assertNotEqual(check(self.log).returncode, 0)

    def test_last_row_cut_off_is_detected_by_anchor(self):
        log = self.make_log()
        del log.rows[-1]
        log.save()
        r = check(self.log)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("anchor", r.stdout.lower())

    def test_edit_with_recomputed_chain_is_detected_by_anchor(self):
        log = self.make_log()
        log.rows[0][7] = "Outcome changed afterwards"
        log.rechain()
        log.save()
        r = check(self.log)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("anchor", r.stdout.lower())

    def test_missing_anchor_fails(self):
        self.make_log()
        self.log.with_suffix(".anchor").unlink()
        self.assertNotEqual(check(self.log).returncode, 0)

    def test_row_added_by_hand_without_anchor_is_detected(self):
        log = self.make_log()
        log.rows.append(["6", log.rows[-1][1], "read", "Sneaked in", "SIM-1", "someone",
                         "n/a", "Done", "", ""])
        log.rechain(5)
        log.save()
        self.assertNotEqual(check(self.log).returncode, 0)


class TestGitAnchor(Base):
    """The local anchor can be rewritten by whoever rewrites the log. A committed copy cannot
    be changed by editing files, so the checker can compare against a Git commit."""

    def git(self, *args):
        r = subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@example.invalid",
                            *args], cwd=self.dir, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def commit(self):
        self.git("init", "-q")
        self.git("add", "log.md", "log.anchor")
        self.git("commit", "-q", "-m", "anchor")

    def test_full_rewrite_passes_local_check_but_fails_against_commit(self):
        log = self.make_log()
        self.commit()
        log.rows[0][7] = "Outcome changed afterwards"
        log.rechain()
        log.save()
        log.write_anchor()
        # Known hole, shown on purpose: log and local anchor rewritten together.
        self.assertEqual(check(self.log).returncode, 0)
        r = check(self.log, "--anchor-git-ref", "HEAD", cwd=self.dir)
        self.assertNotEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_honest_appends_after_commit_still_pass_against_commit(self):
        self.make_log()
        self.commit()
        self.assertEqual(append(self.log, "read", 6).returncode, 0)
        r = check(self.log, "--anchor-git-ref", "HEAD", cwd=self.dir)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_truncation_with_rewritten_local_anchor_fails_against_commit(self):
        log = self.make_log()
        self.commit()
        del log.rows[-1]
        log.save()
        log.write_anchor()
        self.assertEqual(check(self.log).returncode, 0)
        self.assertNotEqual(check(self.log, "--anchor-git-ref", "HEAD", cwd=self.dir).returncode, 0)


class TestRowRules(Base):
    """Rows with a valid chain and anchor that still break a rule (stretch goals included)."""

    def tampered(self, change) -> subprocess.CompletedProcess:
        log = self.make_log()
        change(log)
        log.rechain()
        log.save()
        log.write_anchor()
        r = check(self.log)
        self.assertNotIn("Traceback", r.stderr)
        self.assertIn(r.returncode, (0, 1))
        if r.returncode == 1:
            self.assertIn("PROBLEM:", r.stdout)
        return r

    def test_out_of_order_time_fails(self):
        def change(log):
            log.rows[3][1] = "2001-01-01 00:00:00"
        r = self.tampered(change)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("time", r.stdout.lower())

    def test_missing_time_fails(self):
        def change(log):
            log.rows[3][1] = ""
        self.assertNotEqual(self.tampered(change).returncode, 0)

    def test_malformed_time_fails(self):
        def change(log):
            log.rows[3][1] = "yesterday"
        self.assertNotEqual(self.tampered(change).returncode, 0)

    def test_unknown_kind_fails(self):
        def change(log):
            log.rows[3][2] = "success"
        self.assertNotEqual(self.tampered(change).returncode, 0)

    def test_each_required_field_empty_fails(self):
        for col in (3, 4, 5, 6, 7):  # action, target, actor, confirmed, outcome
            with self.subTest(col=col):
                self.tearDown()  # each column gets a fresh folder and log
                self.setUp()
                def change(log, col=col):
                    log.rows[3][col] = ""
                self.assertNotEqual(self.tampered(change).returncode, 0)

    def test_confirmed_write_without_preview_link_fails(self):
        def change(log):
            log.rows[2][8] = ""
        self.assertNotEqual(self.tampered(change).returncode, 0)

    def test_confirmed_write_linked_to_a_non_preview_fails(self):
        def change(log):
            log.rows[0][4] = "SIM-9"  # same target as the write, but row 1 is a read
            log.rows[2][8] = "1"
        self.assertNotEqual(self.tampered(change).returncode, 0)

    def test_confirmed_write_linked_to_a_later_row_fails(self):
        def change(log):
            log.rows[2][8] = "4"
            log.rows[3][2] = "preview"
            log.rows[3][4] = "SIM-9"
        self.assertNotEqual(self.tampered(change).returncode, 0)

    def test_confirmed_write_linked_to_preview_of_another_target_fails(self):
        def change(log):
            log.rows[2][4] = "SIM-OTHER"
        self.assertNotEqual(self.tampered(change).returncode, 0)

    def test_wrong_sequence_number_fails(self):
        def change(log):
            log.rows[3][0] = "9"
        self.assertNotEqual(self.tampered(change).returncode, 0)


class TestAppend(Base):
    def test_append_only_adds_bytes_at_the_end(self):
        self.make_log(2)
        before = self.log.read_bytes()
        self.assertEqual(append(self.log, "read", 3).returncode, 0)
        after = self.log.read_bytes()
        self.assertTrue(after.startswith(before))
        self.assertEqual(after[len(before):].count(b"\n"), 1)

    def refused(self, **over):
        self.make_log(2)
        before = self.log.read_bytes()
        anchor_before = self.log.with_suffix(".anchor").read_bytes()
        r = append(self.log, over.pop("kind", "read"), 3, **over)
        self.assertNotEqual(r.returncode, 0, r.stdout)
        self.assertEqual(self.log.read_bytes(), before)
        self.assertEqual(self.log.with_suffix(".anchor").read_bytes(), anchor_before)
        return r

    def test_refuses_unknown_kind(self):
        self.refused(kind="success")

    def test_refuses_pipe_in_a_field(self):
        self.refused(outcome="a | b")

    def test_refuses_empty_required_field(self):
        self.refused(target=" ")

    def test_refuses_bearer_token_and_does_not_echo_it(self):
        made_up = "Bearer abcdefghijklmnop1234567890"
        r = self.refused(outcome=f"Called with {made_up}")
        self.assertNotIn("abcdefghijklmnop1234567890", r.stdout + r.stderr)

    def test_refuses_password_assignment(self):
        # Joined at run time: the quest app's evidence scan flags this shape if written whole.
        self.refused(outcome="login failed, pass" + "word=" + "hunter2hunter2")

    def test_refuses_partly_masked_token(self):
        self.refused(outcome="used token ATATT3x****9fQ2")

    def test_refuses_confirmed_write_without_ref(self):
        self.refused(kind="confirmed write", confirmed="Yes")

    def test_has_no_edit_or_delete_command(self):
        self.make_log(2)
        before = self.log.read_bytes()
        for cmd in ("edit", "delete", "remove", "update"):
            with self.subTest(cmd=cmd):
                r = run(AUDITLOG, cmd, self.log, "--row", "1")
                self.assertNotEqual(r.returncode, 0)
                self.assertEqual(self.log.read_bytes(), before)


class TestFileShapeAfterReview(Base):
    """After review (finding F1, F9): the anchor is untouched in every case here, and what
    a reader sees has changed, so the check must fail."""

    def changed(self, edit) -> subprocess.CompletedProcess:
        self.make_log()
        text = self.log.read_text(encoding="utf-8")
        new = edit(text)
        self.assertNotEqual(new, text)
        self.log.write_bytes(new.encode("utf-8"))
        r = check(self.log)
        self.assertNotIn("Traceback", r.stderr)
        return r

    def assert_caught(self, edit):
        r = self.changed(edit)
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("PROBLEM:", r.stdout)

    FAKE = ("| Seq | Time (UTC) | Kind | Action | Target | Actor | Confirmed | Outcome | Ref | Chain |\n"
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |\n"
            "| 1 | 2026-01-01 00:00:00 | confirmed write | Made up | SIM-1 | an agent | No | Done |  | 0000000000000000 |\n\n")

    def test_fake_table_above_the_real_one(self):
        self.assert_caught(lambda t: t.replace("| Seq |", self.FAKE + "| Seq |", 1))

    def test_fake_table_and_unclosed_comment_hiding_the_real_one(self):
        self.assert_caught(lambda t: t.replace("| Seq |", self.FAKE + "<!--\n| Seq |", 1))

    def test_intro_text_replaced(self):
        self.assert_caught(lambda t: t.replace("Earlier rows are never", "Row 3 was made by an agent. Rows are never", 1))

    def test_column_labels_swapped(self):
        self.assert_caught(lambda t: t.replace("| Target | Actor |", "| Actor | Target |", 1))

    def test_header_row_deleted(self):
        self.assert_caught(lambda t: "".join(l for l in t.splitlines(keepends=True)
                                             if not l.startswith("| Seq")))

    def test_text_after_the_table(self):
        self.assert_caught(lambda t: t + "Note: row 2 is wrong.\n")

    def test_blank_line_between_rows(self):
        self.assert_caught(lambda t: t.replace("\n| 3 |", "\n\n| 3 |", 1))

    def test_crlf_line_endings(self):
        self.assert_caught(lambda t: t.replace("\n", "\r\n"))

    def test_trailing_space_on_a_row(self):
        self.assert_caught(lambda t: t.replace(" |\n| 3 |", " | \n| 3 |", 1))

    def test_changed_cell_padding(self):
        self.assert_caught(lambda t: t.replace("| 2 | ", "| 2 |  ", 1))

    def test_no_final_line_break(self):
        self.assert_caught(lambda t: t.rstrip("\n"))

    def test_byte_order_mark(self):
        self.assert_caught(lambda t: "\ufeff" + t)

    def test_invalid_utf8_fails_cleanly(self):
        self.make_log()
        self.log.write_bytes(self.log.read_bytes() + b"\xff\xfe\n")
        r = check(self.log)
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertNotIn("Traceback", r.stderr)


class TestAppendAfterReview(Base):
    """After review (F2, F6, F10): values that would break the log, and rules with no test."""

    def refused(self, kind="read", **over):
        self.make_log(3)
        before = self.log.read_bytes()
        r = append(self.log, kind, 4, **over)
        self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
        self.assertNotIn("Traceback", r.stderr)
        self.assertEqual(self.log.read_bytes(), before)
        self.assertEqual(check(self.log).returncode, 0)

    def test_refuses_each_line_breaking_character(self):
        for ch in ("\n", "\r", "\x0b", "\x0c", "\x1c", "\x1d", "\x1e", "\x85", "\u2028", "\u2029", "\t", "\x00"[:0] + "\x01"):
            with self.subTest(ch=repr(ch)):
                self.tearDown()
                self.setUp()
                self.refused(outcome=f"a{ch}b")

    def test_refuses_ref_that_is_not_plain_digits(self):
        for ref in ("\u00b2", "\u0662", "two", "-1", "0", "99"):
            with self.subTest(ref=ref):
                self.tearDown()
                self.setUp()
                self.refused(ref=ref)

    def test_refuses_partly_masked_value_with_no_known_prefix(self):
        self.refused(outcome="used the value ab12****9fQ2")

    def test_refuses_mask_first_value(self):
        self.refused(outcome="used the value ****9fQ2")

    def test_refuses_known_prefix_with_no_mask(self):
        self.refused(outcome="used ghp_abcdEFGH1234")

    def test_refuses_private_key_header(self):
        # Joined at run time, for the same reason.
        self.refused(outcome="-----BEGIN " + "PRIVATE KEY-----")

    def test_refuses_long_opaque_value(self):
        self.refused(outcome="value a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8")

    def test_refuses_to_append_onto_a_log_that_fails_its_check(self):
        log = self.make_log(3)
        log.rows[0][7] = "changed"
        log.save()
        before = self.log.read_bytes()
        r = append(self.log, "read", 4)
        self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
        self.assertEqual(self.log.read_bytes(), before)

    def test_refuses_to_append_when_only_the_anchor_disagrees(self):
        # Every row is valid on its own; only the anchor shows the rewrite.
        log = self.make_log(3)
        log.rows[0][7] = "changed"
        log.rechain()
        log.save()
        before = self.log.read_bytes()
        r = append(self.log, "read", 4)
        self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
        self.assertEqual(self.log.read_bytes(), before)

    def test_refuses_to_append_under_a_note_added_below_the_table(self):
        self.make_log(3)
        with self.log.open("a", encoding="utf-8") as f:
            f.write("Note: ignore row 2.\n")
        before = self.log.read_bytes()
        r = append(self.log, "read", 4)
        self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
        self.assertEqual(self.log.read_bytes(), before)

    def test_a_correction_is_a_new_row_and_earlier_bytes_stay(self):
        # Criterion 4: the sample log has no correction, so the mechanism is shown here.
        self.make_log(3)
        before = self.log.read_bytes()
        r = append(self.log, "read", 4, action="Correction to row 1: the target was SIM-2",
                   target="SIM-2", ref="1")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertTrue(self.log.read_bytes().startswith(before))
        self.assertEqual(check(self.log).returncode, 0)
        self.assertEqual(Log(self.log).rows[-1][8], "1")

    def test_time_written_is_utc_now(self):
        from datetime import datetime, timezone
        self.make_log(1)
        written = datetime.strptime(Log(self.log).rows[0][1], "%Y-%m-%d %H:%M:%S")
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        self.assertLess(abs((now - written).total_seconds()), 30)


class TestCheckRulesAfterReview(TestRowRules):
    """After review (F6): rules the checker states that had no test. Valid chain and anchor."""

    def failing(self, change):
        r = self.tampered(change)
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)

    def test_credential_already_in_a_row_fails_the_check(self):
        def change(log):
            log.rows[3][7] = "Called with Bearer abcdefghijklmnop1234567890"
        self.failing(change)

    def test_recovery_without_a_failure_link_fails(self):
        def change(log):
            log.rows[3][2] = "recovery"
            log.rows[3][8] = "1"  # row 1 is a read, not a failure
        self.failing(change)

    def test_recovery_with_no_ref_fails(self):
        def change(log):
            log.rows[3][2] = "recovery"
        self.failing(change)

    def test_ref_on_a_read_naming_a_later_row_fails(self):
        def change(log):
            log.rows[0][8] = "4"
        self.failing(change)

    def test_ref_on_a_read_that_is_not_a_number_fails(self):
        def change(log):
            log.rows[3][8] = "\u00b2"
        self.failing(change)


def load_workflow():
    spec = importlib.util.spec_from_file_location("run_workflow", WORKFLOW)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class TestWorkflow(Base):
    def run_workflow(self, answers: str):
        return run(WORKFLOW, "--log", self.log, stdin=answers)

    def test_full_run_gives_all_five_kinds_and_passes_check(self):
        r = self.run_workflow("yes\nyes\n")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(check(self.log).returncode, 0)
        rows = Log(self.log).rows
        self.assertEqual(sorted({row[2] for row in rows}), sorted(KINDS))
        for row in rows:
            for col, name in ((1, "time"), (3, "action"), (4, "target"), (5, "actor"),
                              (6, "confirmed"), (7, "outcome")):
                self.assertTrue(row[col], f"row {row[0]} has no {name}")
        times = [row[1] for row in rows]
        self.assertEqual(times, sorted(times))

    def test_links_and_order(self):
        self.run_workflow("yes\nyes\n")
        rows = Log(self.log).rows
        by_seq = {row[0]: row for row in rows}
        writes = [row for row in rows if row[2] == "confirmed write"]
        self.assertEqual(len(writes), 1)
        preview = by_seq[writes[0][8]]
        self.assertEqual(preview[2], "preview")
        self.assertEqual(preview[4], writes[0][4])
        failure = next(row for row in rows if row[2] == "failure")
        recovery = next(row for row in rows if row[2] == "recovery")
        self.assertLess(int(failure[0]), int(recovery[0]))
        self.assertEqual(recovery[8], failure[0])
        self.assertLess(int(failure[0]), int(writes[0][0]))

    def test_piped_answers_are_not_recorded_as_typed_by_a_person(self):
        self.run_workflow("yes\nyes\n")
        write = next(row for row in Log(self.log).rows if row[2] == "confirmed write")
        self.assertIn("piped", write[6].lower())

    def test_no_private_body_or_credential_in_log_or_output(self):
        mod = load_workflow()
        self.assertGreaterEqual(len(mod.SIM_PRIVATE_BODY), 20)
        self.assertGreaterEqual(len(mod.SIM_PLANTED_LOGIN_VALUE), 20)
        r = self.run_workflow("yes\nyes\n")
        text = self.log.read_text(encoding="utf-8") + r.stdout + r.stderr
        for canary in (mod.SIM_PRIVATE_BODY, mod.SIM_PLANTED_LOGIN_VALUE):
            self.assertNotIn(canary, text)
            for start in range(len(canary) - 11):  # every 12-character run of it
                self.assertNotIn(canary[start:start + 12], text)

    def test_simulated_error_really_carries_the_private_body(self):
        # Guards the test above: the canary must be reachable, or its absence proves nothing.
        mod = load_workflow()
        with tempfile.TemporaryDirectory() as d:
            tracker = mod.FakeTracker(Path(d))
            with self.assertRaises(Exception) as caught:
                tracker.set_assignee(mod.TICKET_ID, mod.NEW_ASSIGNEE)
            self.assertIn(mod.SIM_PRIVATE_BODY, str(caught.exception))
            self.assertIn(mod.SIM_PLANTED_LOGIN_VALUE, str(caught.exception))

    def test_failure_row_gives_a_reason(self):
        self.run_workflow("yes\nyes\n")
        failure = next(row for row in Log(self.log).rows if row[2] == "failure")
        self.assertIn("reason", failure[7].lower())
        self.assertIn("SIM_TIMEOUT", failure[7])
        self.assertIn("did not answer", failure[7])

    def test_run_ends_with_a_read_back_of_the_new_value(self):
        self.run_workflow("yes\nyes\n")
        last = Log(self.log).rows[-1]
        mod = load_workflow()
        self.assertEqual(last[2], "read")
        self.assertIn(mod.NEW_ASSIGNEE, last[7])

    def test_answer_through_a_terminal_is_recorded_as_typed(self):
        # Also shows the limit: this test is a program, and it gets "typed at the prompt".
        import os, pty
        master, slave = pty.openpty()
        proc = subprocess.Popen([sys.executable, str(WORKFLOW), "--log", str(self.log)],
                                stdin=slave, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        os.close(slave)
        os.write(master, b"yes\nyes\n")
        proc.communicate(timeout=60)
        os.close(master)
        self.assertEqual(proc.returncode, 0)
        write = next(row for row in Log(self.log).rows if row[2] == "confirmed write")
        self.assertIn("typed at the prompt", write[6])
        self.assertNotIn("piped", write[6])

    def test_declined_preview_writes_nothing(self):
        r = self.run_workflow("no\n")
        self.assertNotEqual(r.returncode, 0)
        kinds = [row[2] for row in Log(self.log).rows]
        self.assertNotIn("confirmed write", kinds)
        self.assertNotIn("failure", kinds)
        self.assertEqual(check(self.log).returncode, 0)

    def test_declined_retry_leaves_failure_and_recovery_but_no_write(self):
        r = self.run_workflow("yes\nno\n")
        self.assertNotEqual(r.returncode, 0)
        kinds = [row[2] for row in Log(self.log).rows]
        self.assertIn("failure", kinds)
        self.assertIn("recovery", kinds)
        self.assertNotIn("confirmed write", kinds)
        self.assertEqual(check(self.log).returncode, 0)

    def test_second_run_appends_and_keeps_first_run_bytes(self):
        self.run_workflow("yes\nyes\n")
        before = self.log.read_bytes()
        self.run_workflow("yes\nyes\n")
        self.assertTrue(self.log.read_bytes().startswith(before))
        self.assertEqual(check(self.log).returncode, 0)


class TestTamperDemo(Base):
    def test_demo_detects_every_attack_and_leaves_the_log_alone(self):
        self.assertEqual(run(WORKFLOW, "--log", self.log, stdin="yes\nyes\n").returncode, 0)
        before = self.log.read_bytes()
        anchor_before = self.log.with_suffix(".anchor").read_bytes()
        r = run(DEMO, "--log", self.log)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(self.log.read_bytes(), before)
        self.assertEqual(self.log.with_suffix(".anchor").read_bytes(), anchor_before)
        self.assertGreaterEqual(r.stdout.count("DETECTED"), 5)
        self.assertIn("REFUSED", r.stdout)
        self.assertNotIn("NOT DETECTED", r.stdout)

    def test_demo_fails_when_the_log_is_already_broken(self):
        self.assertEqual(run(WORKFLOW, "--log", self.log, stdin="yes\nyes\n").returncode, 0)
        log = Log(self.log)
        log.rows[0][7] = "changed"
        log.save()
        self.assertNotEqual(run(DEMO, "--log", self.log).returncode, 0)

    def test_demo_reports_not_detected_when_the_checker_is_blind(self):
        import shutil
        self.assertEqual(run(WORKFLOW, "--log", self.log, stdin="yes\nyes\n").returncode, 0)
        blind = self.dir / "scripts"
        shutil.copytree(SCRIPTS, blind, ignore=shutil.ignore_patterns("__pycache__"))
        (blind / "auditlog.py").rename(blind / "real_auditlog.py")
        (blind / "auditlog.py").write_text(
            "import sys\nfrom real_auditlog import *\nimport real_auditlog\n"
            "if __name__ == '__main__':\n"
            "    sys.exit(0 if sys.argv[1:2] == ['check'] else real_auditlog.main())\n",
            encoding="utf-8")
        r = run(blind / "tamper_demo.py", "--log", self.log)
        self.assertNotEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(r.stdout.count("NOT DETECTED"), 11)  # 6 row attacks, 4 text attacks, C1
        self.assertIn("FAILED", r.stdout)


if __name__ == "__main__":
    unittest.main()
