# Independent AI review, saved as returned

Reviewer: a separate Claude agent with fresh context, given the quest text and the raw files, and no verdict from the builder. Returned 2026-11-17, before the review fixes. The text below the line is the reviewer's report, copied by script from the agent's output.

---

INDEPENDENT REVIEW: base-camp-safe-rerun, base-attempt-004

WHAT I RAN AND READ
- Read in full: the quest file, rerun-key-rules.md, scripts/rerun.py, scripts/record_evidence.py, tests/test_rerun.py, tests/store_oracle.py, tests/planted_bugs.py, the three sample inputs, all ten files under logs/, all six snapshots.
- On the originals (read-only): sha256 of every snapshot and work/ store, cmp/diff between snapshots, grep of logs/ for title and body words and for home-folder paths, file modification times.
- In a temp copy (/private/tmp/claude-503/-Users-beaubrown-golden-thread-quest--claude-worktrees-agitated-hamilton-40f255/24a2a59a-b88d-46c1-bac2-165a183d0e86/scratchpad/rev.5ukKh0): re-ran record_evidence.py from scratch; ran the 39 tests (all pass); about 45 inputs of my own; 6 trials of real SIGKILL at random moments (4 kills each, 600-item input); 8 runs started at once on one store; 14 bugs of my own planted in copies and run against the tests.
- Nothing under /Users/beaubrown/golden-thread-quest/ was changed.

Results that held up (observed, no issue found):
- Recorded hashes match the snapshot files: 1 = 2 = 5 = 609f1273..., 3 = 0a444ded..., 4 = e753838b..., 6 = a37593b2.... Snapshots 1 and 2 are byte-identical; 2 to 3 differs only in req-0004 body and revision; record_id unchanged.
- My re-recording at a later time and in a different folder gave logs identical to the originals except the timestamp line, and byte-identical snapshots.
- Real SIGKILL: after every kill the store parsed, had no duplicate key, and the final store equalled a clean run byte for byte in all 6 trials. No leftover .tmp.
- 8 runs at once: one exit 0, seven exit 1 "another run is using this store"; store equal to a clean run.
- No title or body text in any file under logs/ (grep for words from every sample title and for MARKER). No home-folder path in logs/.
- By reading and by run: the key uses only the input's source field and the item's source_id. Renamed file, reordered items, changed title, later run time: same keys.

FINDINGS, most serious first

1. A title or body that cannot be saved crashes the run after earlier items were written, and every rerun crashes at the same item
Severity: Medium. Confidence: high. REPRODUCED.
Input: 3 items, item 2 title contains the JSON escape "\ud800" (a lone surrogate, valid JSON). Output: Python traceback (UnicodeEncodeError in save_store), exit code 1, no summary line, no line for item 2. Store holds item 1 only; s.json.tmp left behind. Rerun: same traceback; item 3 is never created, however many times it is rerun.
This contradicts the rerun.py docstring ("1 the run was refused as a whole ... and nothing was written") and criterion 5 for that run (no report). Also seen: 200000-deep nested JSON input gives a RecursionError traceback (nothing written in that case).
Case against: needs malformed text that a real export seldom has; store stays valid; no duplicate is made.
Smallest fix: in plan(), refuse an item whose title or body cannot be encoded as UTF-8 (same treatment as non-text content); catch other exceptions in main() and print a "run stopped" line with what was already written.

2. The tests pin keys only for the ten sample IDs, so key bugs that merge different IDs survive
Severity: Medium. Confidence: high. REPRODUCED by planting.
Planted in a copy, all 39 tests still passed for each:
- dots removed and underscore turned to dash in the ID (a.b and ab become one key)
- ID cut to 12 characters
- runs of zeros collapsed
- NFKC step removed (the rule file states NFKC; nothing tests it)
- lower() in place of casefold()
- collision check compares body only (same key, same body, different title: the second item is silently treated as a repeat and its title is dropped)
- three-way collision checked on the first pair only
- revision not increased on update
- raw input echoed in a "run refused" message (privacy test never exercises refused runs)
The first three are exactly the quest's reflection question (two different items sharing a key), and none of the 45 planted bugs covers that class. planted-bugs.txt "45 planted, 45 caught, 0 survived" is true but says nothing about this class.
Case against: the real code does not have these bugs; this is a gap in the tests, not in the workflow.
Smallest fix: add tests that pairs of distinct IDs stay distinct (a.b vs ab, a_b vs a-b, long IDs differing only at the end, REQ-7 vs REQ-0007), one NFKC test, one same-key same-body different-title collision test, one privacy check on a refused run; add those plants.

3. Changing the input's source label creates every item again
Severity: Medium. Confidence: high that it happens; medium that it counts against the quest. REPRODUCED.
Input: same 3 items, source changed from "intake" to "intake-v2". Output: created=3, records 3 -> 6, exit 0.
The key rules list "two exports labelled with the same source name from different systems" but not the reverse (one system, label changed). The source label is a per-file field typed by whoever makes the export, which is close to the hint "filenames get renamed".
Case against: the label is content, not a filename; some namespace is needed; criterion 2 names only title, filename and run time.
Smallest fix: add this to the "not seen" list in rerun-key-rules.md, with its sign (a run that creates everything while untouched_not_in_input equals the old record count).

4. Key rules statement about collisions is false when the other item has bad content
Severity: Low to Medium. Confidence: high. REPRODUCED.
Rules say: two items with the same key and different title or body are both refused, and an existing record with that key "is left as it is". Input: store has req-0001; input has req-0001 with a new body, plus a second item with source_id REQ-0001, title 5 (a number). Output: "updated intake:req-0001 ... revision 1 -> 2" and "refused intake:req-0001 at position 4 (title or body is missing or is not text)". The record was changed although two different items claimed its key.
Case against: the second item is unusable anyway, and it is reported.
Smallest fix: register the key in by_key before the content check so both are refused, or narrow the sentence in the rules.

5. Criterion 2 is shown in the recorded runs for filename only
Severity: Low to Medium. Confidence: high. Inferred from the logs.
All five recorded commands carry "recorded (UTC): 2026-11-17 14:50:00", the same second, so they cannot show run-time independence. No recorded run changes a title (the changed input changes a body only). Filename independence is shown: changed-input.txt uses a different file name and 9 items are skipped. Title and run time rest on tests.txt pass lines (test_title, test_run_time) and on reading the code.
Case against: the tests are sound for those two (I read them; the fake clock is probed before use), and my own later re-recording gave the same hashes.
Smallest fix: record one more run with a retitled item and one made at a visibly different time, or say in PROOF.md that these two rest on tests.

6. Wording in rerun-key-rules.md that says more, or other, than the code does
Severity: Low. Confidence: high. REPRODUCED.
- "lower-cased": the code uses casefold plus NFKC, which merges IDs that differ by more than case. REQ-ß and REQ-SS give one key (intake:req-ss); REQ-① and REQ-1 give one key; long s "ſ1" and "S1" give one key. In one input these show as a collision; across two runs the second silently updates the first. The "not seen" list covers IDs that are not folded but not different IDs that are folded together.
- "may hold letters, digits, dash and underscore": only a to z. "REQ-É1" is refused. Also the first character must be a letter or digit: "-7", ".a", "_a" are refused, with a message that says the ID has other characters, which is untrue for them.
- "The workflow does not read the clock": true of rerun.py by reading (no time import). Not provable by a run; the fake-clock test supports it.
Smallest fix: reword those three sentences.

7. "untouched_not_in_input" counts refused keys that were in the input
Severity: Low. Confidence: high. REPRODUCED.
Store has req-0003; input has two colliding req-0003 items. Output line: untouched_not_in_input=1, though the key was in the input twice.
Fix: add refused keys to seen_keys, or rename the field.

8. A store edited by hand is trusted beyond what load_store checks
Severity: Low. Confidence: high. REPRODUCED.
- next_record_number set back to 1: next create gets SIM-0001, so two records share a record ID. Exit 0.
- A stored key changed to "intake:REQ-0001": next run creates a second record for req-0001. Exit 0.
- Two records given the same record_id, revision set to true: accepted, exit 0.
Case against: hand edits are outside the quest; duplicate keys and wrong shapes are refused.
Fix: check record IDs are unique, next_record_number is above the highest, and keys match the key pattern; or list as a limitation.

9. Store given through a symlink
Severity: Low. Confidence: high. REPRODUCED.
Run with --store link.json (a symlink to s.json): reports "updated", but the symlink is replaced by a regular file and the real s.json is not changed. The lock is on link.json.lock, so a run on s.json at the same time would not be excluded (that part inferred).
Fix: resolve the path with os.path.realpath first.

10. Smaller overclaims in docstrings and log notes
Severity: Low. Confidence: medium to high. Inferred, except where noted.
- rerun.py "exit 1 ... nothing was written": false for finding 1 (reproduced); also a .lock file is always created.
- interrupted-run.txt: the killed run prints 6 "created" lines but the store has 7 records (kill comes after the write, before the line). The note does not say so. Correct behaviour, but the killed run under-reports by one and a reader has to find that in store-check.txt.
- tests-before-code.txt shows everything failing because the script was absent, which any test would do; it is weak proof that a test can fail for a real reason. Its timestamp is the same second as rerun.py (09:44:03), so "before the code existed" cannot be checked from the files. test_rerun.py was last changed at 09:47:25, after the code, so "written from the acceptance criteria" before the code is only partly supported. The planted-bug run is the real evidence that tests can fail.
- save_store "a kill leaves the old or the new store": held under real SIGKILL. Not assessed for power loss (no directory fsync).
- Many expected values in the tests (exit codes 1 and 2, refuse both colliders, exact line format) are the builder's design choices, not quest text. The quest-derived ones (no new record on rerun, same bytes, update keeps record ID, counts match an independent read of the store) are checked against store_oracle.py, which does not import the workflow. EXPECTED_KEYS is hand-written, not computed by the code.

11. Other observations, no action needed unless wanted
- Duplicate names in the input JSON (two "items" lists, two "source_id" in one item): last one wins silently. Reproduced.
- A 100000-character ID is accepted and printed in full on the report line. Reproduced.
- A changed field other than title or body is reported as "content unchanged". Reproduced; the rules file does say only title and body are compared.
- store-snapshots/ and work/ hold full titles and bodies. They are not under logs/, and the content is made-up sample text.

SAFETY CONSTRAINTS
- Simulated system only: observed. rerun.py touches one local JSON file, its .tmp and .lock; no network import.
- First run's output not deleted before the second: supported, not proven. second-run.txt has the recorder's own "before" hash equal to first-run's "after" hash, records_before=10, and ten "skipped" lines naming SIM IDs; a wiped store would give ten "created". record_evidence.py has no delete or reset between runs and refuses to start if work/ exists. Limit: the store is deterministic, so the same hashes would appear if someone deleted the store, re-ran the first run, then ran the second. The hashes cannot tell those apart; only the recorder's code and the single-second timestamps argue against it. My re-recording with the unmodified recorder reproduced the logs.
- No private item content in logs/: observed (grep, see above).

ACCEPTANCE CRITERIA
1. Key stays the same across runs: observed-supported. first-run.txt and second-run.txt list the same ten keys; snapshots 1 and 2 identical. Items with no usable ID get no key and are refused (collision-run.txt position 12).
2. Key independent of title, filename, run time: partly. Filename: changed-input.txt. Title and run time: tests.txt and code reading only (finding 5). Depends on the input's source label (finding 3).
3. Second run creates and changes nothing: observed-supported. second-run.txt plus snapshots 1 and 2 byte-identical (my own cmp).
4. Changed item updated in place: observed-supported. changed-input.txt plus my diff of snapshots 2 and 3 (only req-0004 body and revision; same SIM-0004; 10 records).
5. Each run reports created, updated, skipped: observed-supported for completed runs (all five logs). The killed run under-reports by one, and a crashing run reports nothing (findings 1, 10).
6. Second result equals first: observed-supported. sha256 609f1273... for snapshots 1 and 2, checked by me, and store-check.txt.
Stretch: collision reported (collision-run.txt, snapshot 6 has no req-0003); killed run rerun to completion (interrupted-run.txt, snapshot 5 = snapshot 1; also my real-kill trials).

NOT ASSESSED
- PROOF.md, manifest.yaml, validation/, screenshots/ (told to ignore; PROOF.md is still a template, so the quest's "explain in PROOF.md, citing criteria by number" is not met yet).
- Whether the evidence paths satisfy the quest's stated paths (quest says attempt-001; work is in base-attempt-004).
- Power loss or disk-full during a write; network or shared file systems; Windows (fcntl is Unix only); Python versions other than 3.15.0.
- Whether the logs were hand-edited after recording (I can only say an unmodified re-run reproduces them).
- Whether tests were truly written before the code.
- Inputs larger than 600 items; memory limits.
- The planted_bugs.py run itself was not re-run by me; I ran my own plants through the same RERUN_SCRIPT route.
