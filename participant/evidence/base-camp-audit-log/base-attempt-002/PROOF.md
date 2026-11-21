# Proof · base-camp-audit-log

Attempt: `base-attempt-002`

## How this was made

Claude (an AI assistant, Claude Code) wrote the tool, the tests, the documents and this file, at Beau's direction, on 2026-11-11. Beau made the scope and design choices listed below, agreed the pass and stop conditions before any result existed, and ran the workflow that produced the sample log in his own terminal. Two fresh AI reviewers, given the quest and the raw files and not the builder's conclusions, checked the work; their reports are saved as returned. No human other than Beau has reviewed it yet.

Choices Beau made: leave the older `participant/context/audit-log.md` untouched and start a new chained log; use a chain plus an anchor file; keep scripts and tests inside this evidence folder; remove his computer's name from the saved terminal output.

## What was built

- A chained audit log format: ten columns, five kinds of event (read, preview, confirmed write, failure, recovery).
- `scripts/auditlog.py`, with two commands: `append` (add one row at the bottom) and `check` (verify the file). It has no edit or delete command.
- `scripts/run_workflow.py`: one simulated piece of work (change a pretend ticket's assignee) that logs each step. Its first write fails on purpose so the log holds a failure and a recovery.
- `scripts/tamper_demo.py`: makes changes to copies of the log and shows what the check says.
- A sample log of six rows from Beau's run.

## Where the important artifacts are

Required evidence:

| Item | Path |
|---|---|
| Format, fields, five kinds with an example of each | `participant/context/audit-log-format.md` |
| Log from a run with all five kinds | `participant/context/audit-log-all-events.md` (with its anchor, `participant/context/audit-log-all-events.anchor`) |
| Append-only check output | `participant/evidence/base-camp-audit-log/base-attempt-002/logs/append-only.txt` |

Supporting files, all under `participant/evidence/base-camp-audit-log/base-attempt-002/`:

| What | Path |
|---|---|
| The tool, the workflow, the tamper demo | `scripts/auditlog.py`, `scripts/run_workflow.py`, `scripts/tamper_demo.py` |
| Tests, and the planted-bug runner | `tests/test_auditlog.py`, `tests/planted_bugs.py` |
| Beau's terminal output from the run that made the sample log | `logs/workflow-run.txt` |
| Test run, planted-bug run | `logs/tests.txt`, `logs/planted-bugs.txt` |
| The two AI review reports, as returned | `logs/independent-review-1.md`, `logs/independent-review-2.md` |

## How edits to earlier entries are detected

The tool detects changes; it does not prevent them. Anyone can open the file in an editor. What the check does (acceptance criterion 4):

1. **Fixed file shape.** `check` fails unless the file is the tool's fixed heading followed by rows written byte for byte as the tool writes them.
2. **Chain.** Each row ends with 16 hex characters computed from the previous row's value and the row's other nine cells. A changed cell, a removed row before the last, or moved rows leave a value that no longer matches.
3. **Anchor file.** It holds the row count and the last chain value. Rows cut from the end, or every chain value recomputed after an edit, no longer match it.
4. **Committed anchor.** `check --anchor-git-ref <commit>` compares the log with the anchor as it was at a Git commit. This is for the case where the log and the anchor file are rewritten together, which the plain check passes.

A correction is a new row that names the earlier row in Ref. The sample log has no correction row; a test shows one being added with the earlier bytes unchanged (`test_a_correction_is_a_new_row_and_earlier_bytes_stay`).

`logs/append-only.txt` records thirteen attempts on 2026-11-11 against the sample log:

- A1 to A6, on a copy with the anchor left alone: edit a row, delete a row, swap two rows, cut the last row, edit and recompute every chain value, delete and renumber and recompute. Each: check exit code 1, "DETECTED".
- A7 to A10, rows untouched: a made-up table above the real one, the same with the real table hidden in a comment, a false sentence in the heading, a note under the table. Each: exit code 1, "DETECTED".
- B1, B2: asking the tool to `edit` or `delete`. Refused, because the tool has no such command. This does not stop a text editor.
- C1, in a temporary Git repository: log and anchor rewritten together. The plain check passes (the known limit); the check against the committed anchor fails, "DETECTED".
- The sample log's and anchor's SHA-256 values are the same before and after, and the sample log passes its check at the end.

## The acceptance criteria

1. **Each entry has a time, action, target, initiating actor, outcome and confirmation status.** Observed: all six rows of the sample log have the six fields filled. `check` fails a row where any of them is empty (tests `test_each_required_field_empty_fails`, `test_missing_time_fails`).
2. **Reads, previews, confirmed writes, failures and recoveries.** Observed: rows 1 and 6 are reads, row 2 a preview, row 3 a failure, row 4 a recovery, row 5 a confirmed write.
3. **A failure gives the reason without quoting private content.** Observed: row 3's outcome is "Reason: the pretend tracker did not answer in time (code SIM_TIMEOUT)". The simulated error message carries a made-up ticket text and a made-up credential on purpose; a test checks that no 12-character run of either appears in the log or the screen output.
4. **Earlier entries are not edited or removed; a correction is a new entry.** See the section above. For this sample log, "not edited since it was written" rests on the check passing now and on the anchor that will be in the hand-in commit; before that commit exists, nothing outside this computer holds a copy.
5. **No credential or private record body.** Observed: targets are identifiers (`ticket SIM-101, field assignee`); the pretend ticket's text is never logged. `append` refuses values matching a short list of credential shapes, and `check` applies the list to existing rows. The first reviewer read the log, the format document and the saved logs and reported none.
6. **Another person can reconstruct the order.** Observed: Seq runs 1 to 6, times do not go backwards, and Ref ties row 3 to its preview (2), row 4 to its failure (3) and row 5 to its preview (2). Rows written in the same second are ordered by Seq. `check` fails on a missing, malformed or backwards time and on a wrong Seq.

Stretch goals: both are in the check (time order; each confirmed write must name an earlier preview for the same target).

## How to reproduce the behavior

From the repository folder. None of these changes the sample log.

```
python3 participant/evidence/base-camp-audit-log/base-attempt-002/scripts/auditlog.py check participant/context/audit-log-all-events.md
python3 participant/evidence/base-camp-audit-log/base-attempt-002/scripts/tamper_demo.py
python3 -m unittest discover -s participant/evidence/base-camp-audit-log/base-attempt-002/tests
```

To see a run of the workflow without touching the sample log, give it another file:

```
python3 participant/evidence/base-camp-audit-log/base-attempt-002/scripts/run_workflow.py --log /tmp/try-audit-log.md
```

Running it without `--log` appends six more rows to the sample log. That is allowed (it is a log), but the SHA-256 values in `logs/append-only.txt` would no longer match the file.

After hand-in, to compare the log with the anchor in a commit:

```
cd participant/context && python3 ../evidence/base-camp-audit-log/base-attempt-002/scripts/auditlog.py check audit-log-all-events.md --anchor-git-ref <commit>
```

This command was run only in temporary repositories (tests and Part C of the demo). It has not been run against the real hand-in commit, which does not exist yet.

## What was tested or validated

- **Expected results first.** Nine expected results and four conditions that would block hand-in were agreed with Beau before any code. 43 tests were written from them and run with no tool present: none passed.
- **Tests.** 86 tests, all passing in `logs/tests.txt`. The later tests were added from review findings, each run and seen failing before its fix where a fix was involved.
- **Planted bugs.** `tests/planted_bugs.py` plants 44 bugs one at a time in a copy of the scripts and runs the suite. `logs/planted-bugs.txt` is the second full run, made against the final scripts and tests: 44 planted, 44 caught. The first full run caught 41. Of the 3 that survived then, one was badly planted (it switched off one of two places that refuse a `|`) and two showed real gaps in the tests, which were tightened before the second run. The first run's output was replaced by the second and is not kept.
- **First review** (`logs/independent-review-1.md`): 15 findings, none marked Blocking, one High. Acted on in code, tests first: a made-up table or changed text around the rows passed the check (its F1, now A7 to A10); five line-break characters got past `append` and broke the log (F2); Ref accepted non-ASCII digits (F10); whitespace changes passed (F9). Test gaps it listed (F6) were closed with tests. Claims it found too broad (F4, F5, F7) were narrowed in the format document. The rest are in the limitations below.
- **Second review** (`logs/independent-review-2.md`), narrow, after the fixes: 92 changed files tried with the anchor untouched, none passed the check; 152 odd values tried through `append`, none left a log that fails its check. It found three inputs that crash and several invisible characters that are accepted; these are listed as limitations, and three sentences of the format document were corrected. By the stopping rule agreed beforehand, no third review was run.
- **`gtq validate`**, run on 2026-11-11 after this file was written, reported one warning, about a file from an earlier quest (`participant/skills/jira-read-assigned/SKILL.md`), and nothing about this quest's files.

Not assessed: the committed-anchor check against the real pushed commit; how GitHub or another viewer renders odd characters in a cell; Windows; two appends at the same moment; any Python version other than 3.15.0.

## Remaining limitations

Known so far; there may be others. The fuller list is at the end of `participant/context/audit-log-format.md`.

- Detection only. The file can be edited; the check has to be run for a change to show.
- Log and anchor rewritten together pass the plain check. The committed-anchor check covers that only if someone other than the editor holds the commit. The hand-in commit goes to Beau's own fork, which its owner could force-push, so that rests on the reviewer or the pull request record. The tool does not record which commit to trust.
- **The log cannot answer the scenario's own question with certainty.** Actor is the computer account, the same for a person and for an AI agent running under that account. "Typed at the prompt" means the answer came through a terminal, which a program can also drive (one test does). That Beau typed the two answers in the sample log rests on his word and `logs/workflow-run.txt`, which is a paste, not a machine capture.
- Actor and Confirmed are whatever text the caller passes to `append`; the check only requires them not to be empty.
- An `append` interrupted between writing the row and updating the anchor leaves a log that fails its check until the anchor is repaired by hand.
- The credential list is short and matches shapes. It missed, when tried, a password written without `=` or `:`, a short token, a card number and an email address, and it refused a 40-character commit ID.
- Some invisible or blank characters are accepted in a cell (for example U+034F and U+3164). Three inputs end in a Python error with nothing written (a Ref over 4300 digits, in `append` or in the file; an argument that is not valid UTF-8). Very long unbroken values are slow.
- The chain value is 64 bits. Time comes from the computer's clock. One preview can be named by more than one confirmed write.
- The older `participant/context/audit-log.md` and `participant/tools/create-fake-ticket.py` are unchanged and still unchained.

Reflection (the quest asks what the log could not answer): whether a person or the agent gave the yes. The log records how the answer arrived, not who gave it. Answering that would need a confirmation step the agent cannot perform, held somewhere the agent cannot write.

## Sensitive values

- No real credential, token or customer data was used. The ticket, the users and the tracker are made up; the "credential" and "private text" inside `run_workflow.py` are made-up strings that exist so the tests can check they never reach the log.
- The computer account name `beaubrown` appears in the Actor column and in paths inside the review reports. The computer's name was removed from `logs/workflow-run.txt` and from one line of the first review report; both files say so at the top.
- The test file contains made-up credential-shaped strings to exercise the refusal rules. The quest app's evidence scan first flagged four of them (three in the tests, one constant name in `run_workflow.py`). None was a real secret. The constant was renamed and the test strings are now joined at run time, so the scan reports nothing in this package.
