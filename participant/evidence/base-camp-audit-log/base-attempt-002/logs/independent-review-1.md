<!-- Report of an independent AI reviewer (a fresh Claude subagent given the quest and the raw files, not the builder's conclusions), 2026-11-11. Copied by script from the reviewer's output, not retyped; the only change is that the participant's computer name is replaced with "[computer name removed]". It describes the work BEFORE the fixes listed in PROOF.md. -->

Independent review: base-camp-audit-log, base-attempt-002 (branch pilot/beau). Nothing under the repository was modified; all experiments ran on copies in `/private/tmp/claude-503/-Users-beaubrown-golden-thread-quest--claude-worktrees-next-logical-quest-56353f/c5bbd828-e274-4daf-88b3-ca1e1aefef6a/scratchpad/rev.DQc5` (`attacks.py` = checker attacks, `mut.py` = my mutations). Paths below are relative to `/Users/beaubrown/golden-thread-quest`; "scripts/", "tests/", "logs/" mean the ones under `participant/evidence/base-camp-audit-log/base-attempt-002/`.

## Findings, most serious first

**F1. High. `check` passes while what a reader sees is falsified, anchor untouched.** Everything above the first line starting `|---` is unread (`scripts/auditlog.py:98`). Reproduced, all `CHECK PASSED: 6 row(s)`:
- A second, fake table inserted above the real one using `| --- | --- |...` as its rule line (valid Markdown, not matched by `startswith("|---")`), holding a made-up row.
- The same fake table followed by an unclosed `<!--` line before the real header. In a rendered view only the fake table shows; the real rows are still in the raw file.
- Intro text replaced with a false statement ("Row 5 was made by an AI agent without confirmation").
- Header row relabelled (Actor and Target names swapped), header row deleted, extra rows placed between header and rule line, a full duplicate of rows 1-6 above the rule line.
The format doc admits only "The text above the table is not covered by the chain" (line 93). That is true but far narrower than what I got through: column labels and whole fake tables. Confidence high. Reproduced.

**F2. Medium. `append` accepts values that permanently break the log.** `append` refuses only `\n` and `\r` (`auditlog.py:211`), but `read_rows` uses `str.splitlines()`, which also splits on U+2028, U+0085, form feed, vertical tab, `\x1c`. Repro on a copy: `auditlog.py append LOG --kind read --action a --target t --actor x --confirmed n/a --outcome $'a\xe2\x80\xa8b'` prints "Appended row 7", then `check` fails ("line 15 is not a log row with 10 cells") and every later append is REFUSED. The only way out is hand-editing the append-only log. Same for `\x0c`, `\x0b`, `\xc2\x85`, `\x1c`. Makes format doc line 24 ("No field may contain ... a line break") false for these. Confidence high. Reproduced (5 characters).

**F3. Medium. An interrupted append leaves the log unusable; not listed as a limit.** The row is written and fsynced (`auditlog.py:240-243`) before the anchor is replaced (`:248`). I simulated an interrupt between them: `check` then reports "rows were added without the tool", append refuses from then on, and a `.anchor-*.tmp` file is left behind. An honest crash is indistinguishable from tampering and the only fix is editing the anchor by hand. "What this does not do" mentions only two simultaneous appenders. Confidence high. Reproduced by monkeypatching `os.replace` on a copy.

**F4. Medium. Actor and Confirmed are free text; the checker accepts contradictory rows.** On a copy: `append --kind "confirmed write" --actor "someone-else (ran nothing)" --confirmed "No. Nobody was asked." --ref 2` was appended and `check` passed. Also passed: a second confirmed write reusing preview 2 (a preview can authorize unlimited writes), and a recovery for target `OTHER-9` citing failure row 3 for a different target. The doc's rule column ("Must not be empty") is accurate, but these lines are broader than the code: line 18 "Actor: the computer account that ran the tool" and line 90 "Actor is the computer account name" (true only when `run_workflow.py` writes the row), and line 48 "A change that was made after a person said yes" (not enforced). Confidence high. Reproduced.

**F5. Medium. "Typed at the prompt" does not show a person typed it.** `run_workflow.py:89` uses `sys.stdin.isatty()`. Repro: `(sleep 2; echo yes; sleep 2; echo yes; sleep 2) | script -q /dev/null python3 scripts/run_workflow.py --log <tmp>/l.md` produced rows 3 and 5 with "Yes, typed at the prompt". Doc line 90 calls this "the only sign of which it was"; it is a sign any program with a pseudo-terminal can produce. So the sample log's two "typed at the prompt" cells, and the statement that it came "from the run Beau made" (doc line 28), are not verifiable from the artifacts. `logs/workflow-run.txt` is a pasted terminal transcript (mtime 10:37:18, 48 s after the log's last row), not a machine capture. Confidence high on the mechanism (reproduced); whether a person made the real run: NOT ASSESSABLE from files.

**F6. Medium. Tests: behaviours that can be removed with the suite still green.** I planted each on a copy and ran the full suite; all SURVIVED (44 tests OK):
- `check`-side credential scan removed (`auditlog.py:157-161`). Doc line 24 "`check` applies the same list to rows already in the log" has no test.
- "partly masked value" rule removed. `test_refuses_partly_masked_token` (tests/test_auditlog.py:348) uses `ATATT3x****9fQ2`, which the known-prefix rule also matches, so the test does not test what its name says. Removing the known-prefix rule alone also survives. "private key block" and "long opaque value" rules removed: both survive, no test at all.
- Recovery no longer needs a failure in Ref (the doc's stated rule; `test_links_and_order` only inspects workflow output, not the checker).
- Ref on other kinds unchecked (`:155`).
- Non-row lines after the table ignored (`:106`).
- Line break accepted in a field (only the pipe is tested).
- Append onto an already-failing log allowed (`:219-222`).
- Local time written instead of UTC.
- tty answer path forced to "piped" (the "typed" branch is never exercised).
- Final read-back row removed.
Also: `test_failure_row_gives_a_reason` (`:429`) asserts only that the word "reason" appears, which is in the fixed template `Failed. Reason:`; swapping the specific reason for the generic fallback survives. The canary test (`:408`) checks the whole string and its first and last 8 characters only; a leak of the middle would pass. Confidence high. Reproduced.

**F7. Medium. Committed-anchor protection is described and demoed but not in force for the handed-in log, and one claim about it is not shown.** `git status` shows the log, the anchor and the format doc all untracked, so today a rewrite of log plus anchor passes every available check (the doc says this at line 89). Part C of `logs/append-only.txt` runs in a throwaway repository; it shows the mechanism, not protection of this log. Doc line 89 implies the commit becomes one "the editor cannot rewrite" once hand-in pushes it. The participant owns the fork and branch and can force-push, so that depends on someone else recording the SHA. Nothing records which ref a checker should trust. Confidence high on current state (observed); the force-push point is inferred.

**F8. Low. Criterion 4's "a correction is a new entry" is stated, not shown.** No correction row in the sample log, no test, no kind for it. On a copy, `append --kind read --action "Correction to row 1" --ref 1` works and passes, but a correction has to be labelled as one of the five kinds. Observed.

**F9. Low. Whitespace and line-ending changes pass, so "unchanged" only holds at cell level.** PASSES with a changed file: CRLF, bare CR, rows separated by U+2028 / form feed / NEL, blank lines between rows, trailing spaces, changed cell padding, NBSP or ideographic space at cell edges, extra pipes at row ends, no trailing newline, BOM. None alters a stripped cell value. Doc line 76 "If a row is changed ... its Chain value ... no longer matches" is slightly broad. Reproduced.

**F10. Low. Uncaught exceptions instead of a PROBLEM/REFUSED line.** (a) `append ... --ref ²` gives a `ValueError` traceback from `int()` (`auditlog.py:155`, `isdigit()` is true for superscripts); nothing written. (b) `--ref ٢` (Arabic-Indic digit) is accepted and written as-is. (c) Invalid UTF-8 anywhere in the log makes `check` crash with a traceback (non-zero exit, so still not a pass). Reproduced.

**F11. Low. Credential list misses common shapes.** Appended without refusal on a copy: `password hunter2hunter2`, `the password is hunter2`, `Bearer abc1234`, `token ****9fQ2` (mask first, against the quest's "even masked in part"), `Authorization Basic dXNlcjpwYXNz`, an AWS-style secret containing `/`, a short JWT, a card number, an SSN shape, an email address. False refusals: `Reset the token: done`, a 40-character Git commit SHA, `sk-learn version checked`. Doc lines 24 and 92 state this limit in general terms, so not an overclaim; listed so the size of the gap is known. Reproduced.

**F12. Low. Real personal details in handed-in files.** `logs/workflow-run.txt:1` contains the shell prompt `beaubrown@[computer name removed]` and the absolute path `/Users/beaubrown/...`. Every log row and five doc examples carry the OS account name `beaubrown`; the doc names "Beau". These are the participant's own details, not a credential or private record. Observed.

**F13. Low. Part B of append-only.txt proves little, and it runs against the real log.** "REFUSED (the tool has no such command)" is argparse rejecting an unknown subcommand; it says nothing about whether the file can be edited (it can, with any editor; the doc says so). Harmless in effect (hashes equal before and after) but "refused" there should not be read as prevention. The OVERALL line "every attack was detected or refused" covers the 9 listed attacks only; none of F1's attacks are in the demo, because `tamper_demo.py:58-65` rewrites rows only and keeps everything above them.

**F14. Low. Unverifiable or contradicted claims in the test files.** `tests/test_auditlog.py:1` says "Written before the tool"; its mtime (10:32:55) is after `auditlog.py` (10:28:07). Mtime is last-modified, so this is inconclusive, but nothing supports the claim. `planted_bugs.py` has no saved output in `logs/`, so its results are not evidence. The test-side `split_row` (`:44`) is character-identical to the tool's, so parsing quirks are shared by tests and tool.

**F15. Low. Other.** (a) A row with a future timestamp passes and then blocks all later appends ("time is earlier than the row before it"); reproduced with `now=2999`. (b) `anchor_path` uses `with_suffix`, so `a.md` and `a.txt` share one anchor; appending to both breaks the first (reproduced). (c) Chain is truncated to 64 bits; fine against casual edits, not stated as a limit. (d) The quest's evidence path says `attempt-001/logs/append-only.txt`; the file is under `base-attempt-002/`. I did not check whether the platform's validator accepts that.

## Acceptance criteria

1. Six fields on each entry: **observed.** All 6 rows have time, action, target, actor, outcome, confirmed. Caveat F4: the checker only enforces non-empty.
2. Five kinds present: **observed** (read x2, preview, failure, recovery, confirmed write).
3. Failure gives reason without private content: **observed** in row 3 (fixed description plus code SIM_TIMEOUT). The simulated error does carry a made-up body and credential and neither appears in the log or `workflow-run.txt` (read and grepped). Caveat F6: the "reason" test is weak.
4. Earlier entries not edited or removed; correction is a new entry: detection of row edit, delete, reorder, truncation and recompute **observed** (my reruns agree with append-only.txt). "Not edited" for this specific log is **inferred** only: nothing is committed (F7), so a log-plus-anchor rewrite before hand-in would be invisible. Correction-as-new-entry **not shown** (F8). Presentation attacks pass (F1).
5. No credential or private record body: **observed** for the log, format doc and three saved logs (read in full plus pattern grep). Only F12.
6. Order reconstructable from the log alone: **observed.** Seq and times are consistent, Ref links 3->2, 4->3, 5->2 resolve. Rows 1-2, 3-4 and 5-6 share a second, so order within those pairs rests on Seq. The log cannot answer the scenario's "person or agent" question (F5; partly admitted in the doc).

## append-only.txt against the required evidence item

Meets the literal item: **observed.** Six attacks on a copy are each detected with a non-zero exit, and the real log's SHA-256 is equal before and after (9407aad2...9319). I recomputed both hashes on the current files and they match the saved output (log 9407aad2..., anchor 991d63bd...). Misleading parts: F13 (Part B wording, scope of the OVERALL line) and F7 (Part C is a demo repository, not this log).

## Checked, no problem found

- Independent recomputation of all six chain values with my own code: match; head equals the anchor.
- Content attacks with the anchor untouched, all caught: edit any cell (including last row), Cyrillic look-alike letter, zero-width space, double space, case change, upper-cased chain, delete first/middle/last/all rows, swap rows, duplicate a row, hand-added row 7 with a valid chain, two rows joined on one line, text or HTML comment after the table, duplicate header or rule line after the table, indented row, NUL byte, escaped pipe, empty file, table removed.
- The five example rows in the format doc are byte-identical to rows in the log.
- Refusal messages do not echo the refused value (read `auditlog.py:206-216`, and seen in output).
- Chain rule, anchor contents and `--anchor-git-ref` behaviour match doc lines 76-78 (read code; git-ref cases covered by the builder's tests, which pass on my copy: 44 OK).
- `participant/context/audit-log.md` is unmodified in `git status`, as the doc says.
- Clock set backwards: append refused, nothing written.
- The workflow contacts nothing external (read `run_workflow.py`; tracker is a temp JSON file).

## Not assessed

- `planted_bugs.py` in full (read only; its 25 mutations not run by me).
- Whether a person, not an agent, made the real run.
- PROOF.md (empty, ignored as instructed), manifest.yaml, and whether the platform's validator accepts the evidence path.
- Behaviour on Windows or with concurrent appenders.
- Whether a rendered view in GitHub hides the table exactly as CommonMark specifies for the unclosed-comment case (inferred from the spec, not rendered).
- Whether `gtq hand-in` actually commits the `.anchor` file (it is untracked now, not ignored).
- Second-preimage attacks on the 64-bit chain.
