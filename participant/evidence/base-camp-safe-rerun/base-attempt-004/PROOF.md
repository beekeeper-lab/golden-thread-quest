# Proof · base-camp-safe-rerun

Attempt: `base-attempt-004`

## How this was made

An AI assistant (Claude) wrote the workflow, the tests, the key rules and this file, at Beau Brown's direction.
Beau agreed the approach before anything was written: the key choice, six conditions that would block the
hand-in, what to do with colliding or keyless items (refuse them), both stretch goals, and one round of
independent AI review with a fixed list of what could reopen the work. A second, separate Claude agent
reviewed the raw files. Its report is saved as returned in `logs/independent-review.md`.

After reading this file, Beau asked for three of the listed limitations to be dealt with: the real-kill and
many-at-once trials rerun on the current version, a run recorded at a later time, and a guard against a
changed source name. He also agreed a second, narrow review of the changes made since the first one, with a
hard stop: only a result that breaks one of the six blocking conditions reopens the work. That review is saved
as returned in `logs/independent-review-2.md`. It reported none of the six as fired. Sentences in this file
and in the key rules that it showed to be wrong or too wide were corrected.

Beau then chose to go past the hard stop for two of its findings, the two that could double or lose records:
finding 1 (a gap in the source-name guard) and finding 4 (a store file that gives a field name twice). Both
are fixed in code, with tests written first and planted bugs. No third review was run. The rest of its
findings are listed under "Remaining limitations".

Statements below are marked **observed** (a run recorded in `logs/` shows it), **tested** (a passing test in
`logs/tests.txt` shows it) or **not assessed**.

## What was built

A small workflow, `scripts/rerun.py`, that reads a JSON file of ten made-up work items and puts them into a
simulated system. The simulated system is one local JSON file (the "store"). There is no network use and no
real system.

For each item the workflow works out a key, looks the key up in the store, and creates, updates, skips or
refuses. It prints one line per item and then the counts.

### The key (criteria 1 and 2)

The key is the source system's name plus the ID that system gave the item, for example `intake:req-0007`.
The full rule is in `participant/context/rerun-key-rules.md`.

- Criterion 1, a key that stays the same across runs. Observed: `logs/first-run.txt` and
  `logs/second-run.txt` list the same ten keys.
- Criterion 2, no dependence on title, filename or run time.
  - Title. Observed: in `logs/retitled-run.txt` item 2 has a new title and is reported `updated`, with nine
    skipped and none created. `logs/store-check.txt` shows the record kept its record ID.
  - Filename. Observed: the first, changed-input and retitled runs read three differently named files against
    one store, and no record was created after the first run. Tested: `test_filename_or_folder`.
  - Run time. Observed over a short gap: `logs/later-run.txt` is the retitled input run again 58 minutes after
    the other recorded runs, against the same store. It reports 10 skipped and the store fingerprint is the same
    before and after. Tested over a long gap: `test_run_time` reruns with the workflow's clock set 400 days
    ahead and the store stays the same.

### What a collision would look like

Two different items that end up with one key. If the workflow guessed a winner, one item's content would
overwrite the other's and the report would call it an update.

- In one input file, this is detected. Observed: `logs/collision-run.txt`. Items at positions 3 and 11 share an
  ID and differ in content. Both are refused, each line names the other's position, nothing is written for that
  key, and the run ends with exit code 2. An item with no ID (position 12) is refused, and no key is made up
  for it.
- A source name the store has no records from is stopped. Observed: in `logs/source-change-run.txt` the same items arrive labelled
  `intake-v2` and the run is refused with nothing written. With `--new-source` it is refused again, because the
  items match the `intake` records. The third command in that log shows what a person can still allow on
  purpose with both flags.
- The same items under a source name the store already knows are stopped too. Observed: in
  `logs/relabel-run.txt` a second source, `billing`, is added with three items of its own, and then the ten
  intake items arrive labelled `billing`. The run is refused and the store snapshot is byte-for-byte the same
  before and after. The match is on ID, title and body together, and one matching item stops the run.
- Across two runs it is not detected. If the source reuses an ID for different work, or two systems are
  exported under one source name, the second run updates the first one's record. The key rules file lists
  these under "what this rule cannot see", with the sign to look for.
- Tidying is kept narrow. Only white space at the ends (spaces, tabs, line breaks and the like) and the case of
  A to Z are folded. IDs with other letters or
  look-alike characters are refused, so they are not merged with a plain ID. Tested for seven such characters
  (`test_look_alike_characters_are_refused_not_merged`) and for six pairs of similar IDs that must stay apart
  (`test_different_ids_stay_different_keys`).

### The runs (criteria 3 to 6)

Recorded 2026-11-17 at 15:09 UTC by `scripts/record_evidence.py` in one go. That was before the two source
checks were added. Recording again with the workflow as it is now, in a fresh copy, gives the same logs apart
from the time line (the last command under "How to reproduce"). The later run, the source-change run and the
relabel run were recorded at 16:07 UTC by `scripts/record_later_runs.py`, with the workflow as it is now.

| Criterion | What the logs show |
|---|---|
| 3. A second run on identical input creates and changes nothing | Observed: `logs/second-run.txt` reports 10 skipped, 0 created, 0 updated. `logs/store-check.txt` shows the store file byte-for-byte identical before and after. |
| 4. A changed item is updated in place | Observed: `logs/changed-input.txt` reports 1 updated (`intake:req-0004`), 9 skipped. `logs/store-check.txt`: 10 records before and after, same record ID `SIM-0004`, fields that differ are body and revision. |
| 5. Each run reports created, updated and skipped | Observed in each completed run's `summary:` line and per-item lines. Skip lines give a reason. Tested: the counts are compared with a separate reading of the store (`tests/store_oracle.py`, which does not import the workflow). |
| 6. The result of the second run equals the result of the first | Observed: the store fingerprint after the second run equals the one after the first (`609f1273...`), read from disk by the recorder as well as printed by the workflow. |

Stretch goals:

- Collision detection: observed, described above.
- A run killed halfway, then rerun. Observed: `logs/interrupted-run.txt`. The run is ended after its 7th write;
  the rerun reports 3 created and 7 skipped, and the store is byte-for-byte identical to the uninterrupted first
  run's store. The kill is simulated: the workflow ends itself abruptly (`os._exit`). The killed run printed six
  `created` lines although seven records were written, because it died between the write and the line. That is
  why the rerun trusts the store and not the earlier output.
- The same with a real kill, on the current version (run at 16:14 UTC, after the last code change). Observed:
  `logs/real-kill-and-parallel.txt`. Over six
  trials on a 600-item input, a SIGKILL sent from outside landed mid-run 11 times. After each one the store was
  readable with no key twice, and after a run was left to finish the store was byte-for-byte the uninterrupted
  run's store. Eight runs started at once, three times: one ran, seven were refused by the lock, and the store
  was the same again. The log ends with the same trials failing against two planted bugs.

### Safety constraints

- Simulated system only: `rerun.py` reads one input file and writes one store file, its side file and its
  lock file.
- The first run's output was not deleted before the second. `record_evidence.py` refuses to start if `work/`
  exists and has no delete or reset step between runs. `logs/second-run.txt` shows the store present before the
  command with the first run's fingerprint and 10 records. Limit, as the reviewer noted: the store is the same
  each time it is built, so fingerprints alone could not tell a kept store from a rebuilt one. The recorder's
  code is the evidence for that.
- No item title or body in the logs. Tested: `test_no_title_or_body_text_in_output` and
  `test_refused_runs_print_no_input_or_store_text`. Checked by search: no sample title, body or home folder
  path is in the `.txt` logs. The items are made up in any case. `store-snapshots/`, `work/` and `earlier-runs/`
  hold the simulated stores, which contain the sample titles and bodies. `logs/independent-review.md` contains
  folder paths as the reviewer wrote them.

## Where the important artifacts are

Required evidence:

- `participant/evidence/base-camp-safe-rerun/base-attempt-004/logs/first-run.txt`
- `participant/evidence/base-camp-safe-rerun/base-attempt-004/logs/second-run.txt`
- `participant/evidence/base-camp-safe-rerun/base-attempt-004/logs/changed-input.txt`
- `participant/context/rerun-key-rules.md`

Under `participant/evidence/base-camp-safe-rerun/base-attempt-004/`:

- `scripts/rerun.py`: the workflow. `scripts/record_evidence.py` and `scripts/record_later_runs.py`: record the
  runs. `scripts/sample/`: the seven input files.
- `tests/test_rerun.py` (72 tests), `tests/store_oracle.py` (separate reading of the store),
  `tests/planted_bugs.py` (86 bugs planted one at a time in a copy of the workflow), `tests/trials.py` (real-kill
  and many-at-once trials).
- `logs/retitled-run.txt`, `logs/interrupted-run.txt`, `logs/collision-run.txt`, `logs/store-check.txt`,
  `logs/later-run.txt`, `logs/source-change-run.txt`, `logs/relabel-run.txt`, `logs/real-kill-and-parallel.txt`.
- `logs/tests.txt`, `logs/planted-bugs.txt`, and the earlier rounds: `planted-bugs-round-1.txt`,
  `planted-bugs-round-2.txt`, `planted-bugs-round-3-first-pass.txt`, `planted-bugs-round-4-before-source-guard.txt`,
  `planted-bugs-round-5-before-second-review-fixes.txt`, `planted-bugs-round-6-first-pass.txt`,
  `tests-before-code.txt`, `tests-before-review-fixes.txt`, `tests-before-source-guard.txt`,
  `tests-before-second-review-fixes.txt`.
- `logs/independent-review.md`: the first reviewer's report. `logs/independent-review-2.md`: the narrow second
  review.
- `store-snapshots/`: a copy of the store after each recorded run. `work/`: the stores themselves.
- `earlier-runs/run-1-before-review-fixes/`: the first recording, made before the review fixes, kept as it was.
  Its `code/` folder holds the scripts and tests as they were at the first review, taken from the copy the
  first reviewer made.
- `earlier-runs/run-3-before-second-review-fixes/`: the later run, source-change run and trials as first
  recorded at 15:39 UTC, before the fixes for the second review.

## How to reproduce the behavior

From `participant/evidence/base-camp-safe-rerun/base-attempt-004/`, with Python 3 and nothing else installed.

Tests (they write only to temporary folders):

    python3 -B -m unittest discover -s tests -v

Planted bugs (about five minutes):

    python3 -B tests/planted_bugs.py

Real-kill and many-at-once trials (under a minute; results vary with timing):

    python3 -B tests/trials.py

Record the runs again in a fresh copy and compare with the saved logs (the `recorded` time line is left out
of the comparison):

    D=$(mktemp -d) && cp -R scripts tests $D/ && mkdir $D/logs
    (cd $D && python3 -B scripts/record_evidence.py && python3 -B scripts/record_later_runs.py)
    for f in first-run second-run changed-input retitled-run interrupted-run collision-run store-check later-run source-change-run relabel-run; do diff <(grep -v '^recorded' $D/logs/$f.txt) <(grep -v '^recorded' logs/$f.txt) && echo "same: $f"; done

This was run after the last code change and printed `same` for the ten recorded logs.

## What was tested or validated

- **Tests**: 72 pass (`logs/tests.txt`). They run the workflow as a separate program and do not import it. The
  expected keys are written by hand in the test file. The results the quest fixes (no new record on a rerun,
  same bytes, an update keeps its record, counts match the store) are checked through `store_oracle.py`. Exit
  codes, the report's line format and "refuse both colliding items" are design choices made for this attempt,
  not quest text.
- **Planted bugs** (`logs/planted-bugs.txt`): 86 planted, 86 caught, 0 survived, with a control run on an
  unmodified copy passing first. Earlier rounds, kept as they were: round 1 caught 43 of 45, and two tests were
  added; round 2 caught 45 of 45. The reviewer then planted 14 bugs of its own and reported nine survivors.
  Tests and plants for those classes were added, and the first pass afterwards caught 70 of 71; one assertion
  was added, giving 71 of 71. Six more were planted with the source-name guard. The saved run with them caught
  77 of 77. Ten more were planted with the fixes for the second review. On the first pass
  (`planted-bugs-round-6-first-pass.txt`) one of them survived and the run then stopped on a plant that
  pointed at a reworded line. The survivor changes nothing the workflow does (an item whose key is already in
  the store is never looked at by the new check), so no test could catch it, and it was taken off the list
  with a note. The stale plant was corrected. The final run is 86 of 86. After that run, one test variable
  was renamed because the quest app's secret scan read the line as a secret-like assignment (it held made-up
  marker text). The 72 tests were rerun, and the three planted bugs nearest that test were rerun and caught.
  The full round was not repeated.
- **One expected result was changed on purpose.** A test written with the source-name guard expected
  `--new-source` alone to let ten identical items be created under a new name. After the second review that is
  refused, and the test now expects the refusal (`test_new_source_flag_alone_does_not_let_the_same_items_in_again`).
- **Tests before code**: `logs/tests-before-code.txt` shows the first 38 tests failing before `rerun.py` existed.
  That only shows they needed the script. `logs/tests-before-review-fixes.txt` is the stronger record: the tests
  written for the review findings, failing against the workflow as it then was (22 failures).
  `logs/tests-before-source-guard.txt` is the same for the source-name guard (7 failures), and
  `logs/tests-before-second-review-fixes.txt` for the second review's two fixes (6 failures).
- **Independent review** (`logs/independent-review.md`): one round, on the first recording. It re-recorded the
  runs in its own copy and got the same logs and stores, checked the fingerprints against the snapshot files,
  killed the workflow for real (SIGKILL) at random moments in six trials, and started eight runs at once. It
  reported no duplicate, no damaged store and no private text in the logs, and eleven findings: none Blocking or
  High, three Medium, two Low to Medium, five Low, and one with no severity given.

What was done with the findings:

| Finding | Action |
|---|---|
| 1. Text that cannot be saved crashed the run part-way, and each rerun crashed at the same item | Fixed in code. Such an item is refused and the rest is processed. Tested. A store folder that cannot be written now ends with a `run stopped` line and no traceback. Tested for that one failure. Other failures can still end in a traceback (see limitations). |
| 2. Tests pinned keys only for the sample IDs; bugs that merge different IDs survived | Tests and planted bugs added for those classes. |
| 3. Changing the input's source name creates every item again | Fixed in code after the walkthrough: a source name the store has no records from is refused unless `--new-source` is given. Tested, and observed in `logs/source-change-run.txt`. |
| 4. A collision with an unusable twin still updated the record | Fixed in code. Tested. |
| 5. Recorded runs showed criterion 2 for filename only | A retitled run and a later run were added to the recordings. |
| 6. Unicode folding could merge different IDs; wording in the rules | Fixed in code: only a to z, digits, dot, dash, underscore are accepted. Rules reworded. |
| 7. `untouched_not_in_input` counted refused keys | Fixed in code. Tested. |
| 8. A hand-edited store was trusted too far | More store checks added (record IDs, next number, key form, revision). Tested for seven edits. |
| 9. A store given as a link was replaced | Fixed in code. Tested. |
| 10. Overclaims in docstrings and notes | Docstring and the interrupted-run note corrected; the "tests before code" claim narrowed above. |
| 11. Repeated field names, very long IDs | Both are now refused. Tested. |

The quest app's own validators had not been run when this file was written.

## Remaining limitations

Known so far; there may be others.

- The second review looked only at what changed since the first. No reviewer has read the whole of the current
  version in one pass. It re-recorded the nine run logs with the code as it then was and got the same logs and
  stores, and ran 1200 random runs plus 1200 identical reruns against a model of its own with no problem found.
- The two fixes made after the second review (the same-item check and the store's field-name check) have not
  been reviewed by anyone but the builder. What stands behind them is 10 tests, 9 planted bugs, the recorded
  relabel run, and the trials and re-recording rerun afterwards.
- The same-item check matches on ID, title and body together. A relabelled export in which every item was also
  edited matches nothing and is created again. Checked by a run: with one unedited item the run is refused, with
  none it creates all ten.
- From the second review, left as they are:
  - If the output is closed early (for example piped to `head`) or the run is stopped with Ctrl-C, the workflow
    ends in a Python traceback and prints no `run stopped` line. The reviewer found the store valid and a rerun
    complete in both cases. The `run stopped` message can also be wrong by one item: the item after the last
    line printed may have been written.
  - A trailing line break or other Unicode white space on an ID is removed like a space, so such an ID is
    accepted. No test covers that.
  - Two more hand-edit cases: a record ID with thousands of digits ends as `run stopped` where `run refused` was
    meant, and `SIM-0001` and `SIM-00001` are taken as two record IDs. The check on unsaveable text in a stored
    record has no test.
  - `tests/trials.py` exercises creates only. The first two lines and the last section of
    `logs/real-kill-and-parallel.txt` were produced by shell commands that are not saved as a script.
- The later run was 58 minutes after the first recording. A longer gap rests on the clock test.
- In the real-kill trials, 11 of 24 kills landed while the workflow was running; the others arrived after it had
  finished. The moments are random, so a rerun of the trials gives different numbers.
- Collisions across runs are not detected (see the key rules file). Both source checks can be waved through
  with their flags, and neither does anything on a store with no records.
- IDs with letters outside a to z are refused. A real source with such IDs would need a different rule.
- Fields other than title and body are not stored or compared.
- Records are never deleted. An item that disappears from the input stays in the store and is counted in
  `untouched_not_in_input`.
- Not assessed: power loss or a full disk during a write, network or shared file systems, Windows (the lock is
  Unix-only), Python versions other than 3.15.0, inputs larger than 600 items.
- The store is a file. A real system would need its own lookup-before-create call, and a way to do the lookup
  and the create as one step.

## Sensitive values

No secret, token, customer name or private ticket content is here. The ten work items are made up for this
quest. The workflow needs no credentials.
