# Release Audit — Round 12

Status: **in progress.** Findings recorded and verified. Fixes under way.

Commit under audit: `16a0b03` on `main`, the merge of `chore/round-11-audit`.
Predecessor: `docs/audits/round-11-independent-audit.md`.

## Why this round exists

`docs/ACCEPTANCE-CRITERIA.md` leaves **DH7** open. Eleven rounds have run and each found
something. The criterion closes on a round that finds nothing.

## Method

Three lenses, each in its own worktree at `16a0b03` with `docs/audits/` removed, each given
only paths, a commit and the areas round 11 named. None saw a summary of what the author
believed, and none saw another lens's findings. The engine lens ran on the larger model.

| Lens | Scope |
|---|---|
| Curriculum | The eight quests followed literally through the CLI and the running service, `proof_files` across versions, deletion and directories, every legitimate path through `locally_validated`, symlink consistency, the reviewer flow through several decisions, and accessibility at 640px and 1280px |
| Engine | `safe_io.py` and the symlink rules, `proof_files` digests, forged and legitimate state at load, the update path against a real bare upstream, hostile validators, and the service |
| Tooling, tests, documentation | A README-only clean clone, every gate, `make check` beside `make serve`, CI against the Makefile, every command printed in the guides run as printed, and mutations of the round-11 guards |

Every finding below was verified here before it was accepted, by reproduction or by reading
the code at the cited line.

## Findings

### Curriculum

| ID | Severity | Finding | Resolution |
|---|---|---|---|
| C1 | Blocking | Every action form fails in a real browser. Pages send `Referrer-Policy: no-referrer`, so Chromium sends `Origin: null` on a form POST, and `_origin_is_acceptable` refuses it as cross-origin. Only the CLI can change state. No test submitted a form: the one UI test that reaches the confirmation dismisses it. Verified here with a bare Chromium probe. | The policy is `same-origin` in the header and the meta tag, so a same-origin POST carries its real origin and a cross-origin one still sends `null` and is refused. The origin check is unchanged. Two browser tests submit real forms, accept the confirmation and check the files on disk: start-quest and record-review. Two service tests keep `Origin: null` refused. Both browser tests fail with 403 when the old policy is put back. |
| C2 | High | Tests that run the CLI with `--participant-root` still build into the repository's own `generated/`, because the generated root is not overridable. `docs/USER-GUIDE.md` tells participants to run `make check` to check their install, which replaces their site with fixture data, for example an approval by "A Reviewer", until the next build. Verified: one test file rewrote `generated/index.html`. | `GTQ_GENERATED_ROOT` and `GTQ_LOCAL_DATA_ROOT` are read by the CLI, and every test that shells out sets them. A session guard in `tests/conftest.py` fails the run if `generated/`, `local-data/` or `participant/` changed. It caught one more test added this round during the merge, which was fixed. ADR-018 amended. |
| C3 | Medium | A link leading outside the evidence package makes the review page say "The scan found something secret-like… the value rotated", because the page reduces the scan to a boolean (`build.py`, `review.html.j2`). | `scan_kinds` separates a secret, a link out of the package and a file too large to scan. The review page and the participant's evidence page each word the three separately, and all still say not to submit or approve. The file-too-large case was added during the merge, because the E8 ceiling created it. Five tests. |
| C4 | Medium | After a pass, `mark-locally-validated` and a failing re-run, the evidence page shows "Required automated checks passed" beside the same validator's "Last run: fail", with nothing connecting them. | The evidence page adds a note when a `locally_validated` attempt's declared validator last returned something other than a pass. The state logic is unchanged (ADR-017). Two tests. |
| C5 | Medium | When a proof path is renamed in a newer quest version, the review page's evidence checklist marks the old item "Not detected" with no per-item note that the version changed. | On a version mismatch, each missing checklist item notes that the list follows the published version and the attempt was on an earlier one. Two tests. |

### Engine

| ID | Severity | Finding | Resolution |
|---|---|---|---|
| E1 | Blocking | Two writes follow a symlink out of `participant/`: the activity line (`store.py`, `path.open("a")`) and validation results written into a linked `validation/` directory (`evidence.py`), which the loader then reads back. A FIFO `ACTIVITY.md` hangs the action while it holds both locks, after `progress.yaml` has changed. The review archive is written with a plain `write_text`. | Participant writes go through `safe_io.atomic_write` and `append_to_regular_file`, which walk down from the participant root without following links and never open a special file in a blocking way. That covers progress, PROOF.md, the manifest, the lock, validation results, submission, review, the review archive, the migration restore and the validator workspace. The loader does not read results through a linked `validation/`. An unusable `ACTIVITY.md` skips the line with a warning, because the change is already on disk. ADR-042. Parametrized tests over FIFO, links in and out, dangling links and directories. |
| E2 | High | Validation result files are read without a bound (`progress.py` `_load_validation`). A FIFO hangs `validate`, `build` and the service. A link to `/dev/zero` gets the process killed. | Results are read through the bounded reader with an 8 MB ceiling and refused when they are links. Parametrized test over FIFO, device, oversize and link. |
| E3 | High | `review_history` globs `review*.yaml` and parses without a bound or error handling, while the load check covers only `review-*.yaml`. A stray `reviewer-notes.yaml` with bad YAML passes `validate` and then crashes `build` with absolute paths. A FIFO hangs it. `read_submission` reads without a bound. | One definition of a review record, `review_archive_paths`, is used by the loader, the history and the evidence hash. Records are read bounded, and a damaged one is a load problem. `read_submission` is strict on the approval path. Parametrized tests, including a `build` that must exit 0. |
| E4 | Medium | A hand-edited `state: submitted` with no `submission.yaml` loads clean and can be approved to `verified`, skipping the secret-scan gate. The lens rated it High. It is Medium here, as round 11 rated the matching forged `locally_validated` case: it needs a hand edit of the participant's own file, and the review page still shows the scan result. | A `submitted` attempt without a readable submission record is a load error, and `record_decision` refuses it. Needs-changes, withdraw and resume histories load clean. Six tests. Five older tests that hand-wrote `submitted` now use the real submission step. |
| E5 | High | A legitimate `locally_validated` attempt becomes a load error after an ordinary curriculum update that adds a validator, because the check uses the current quest's validators and ignores the attempt's version. Every action is then refused, including the `run-validator` that would clear it. | On a version mismatch with at least one qualifying result, a newly required validator is a warning that names it. With the same version, or with no qualifying result, it stays an error. ADR-017 amended. Two tests. |
| E6 | Medium | The runner caps the excerpt and check count but not `summary`, `evidence`, `suggested_action`, `artifact`, the outcome value or the id pattern, so an oversize field throws away the whole run instead of recording it. | Over-long check fields are truncated with a marker. A check with an invalid outcome or id becomes an `inconclusive` check reporting the defect, and the run is `environment_failure`. It can no longer classify as a pass. Seven tests. |
| E7 | Medium | Redaction runs after truncation, so a token cut at the boundary is stored in clear with `redaction_applied: false`. The same holds for the stderr line on a failed run. | Redaction runs on the complete text before truncation, for the excerpt, the stderr line and every check field. Three tests with a token straddling each limit. |
| E8 | Medium | Evidence files have no size ceiling. A 135 MB log makes every build take about a minute while it holds the locks. `hash_directory` holds every file in memory. | Hashing streams in 1 MB chunks with unchanged digests. The scan reads each file up to 2 MB, and a larger file is a finding that blocks submission with its own message. PROOF.md over the ceiling is not rendered. Ceilings documented in `docs/SECURITY-AND-PRIVACY.md`. Three tests. |
| E9 | Low | A validator grandchild that starts its own session survives cleanup. | Not fixed. A reliable fix needs an isolation layer this release does not have. Stated in `docs/VALIDATOR-CONTRACT.md` and as known limitation 10 in `docs/RELEASE-NOTES.md`, with a test that both documents say it. |
| E10 | Low | `make migrate` rewrites `progress.yaml` without an activity line. | `apply_migrations` writes an activity line after a migration it keeps. Test. |
| E11 | Low | A validator that finishes but leaves a non-daemon thread running is reported `interrupted`, and its result is discarded. Not a false pass. | When the result channel has closed and the process is still alive a second later, the result is kept and the process group is killed. Two tests, one of them for an ordinary run. |

### Tooling, tests, documentation

| ID | Severity | Finding | Resolution |
|---|---|---|---|
| T1 | Medium | `tests/integration/test_doc_cli_examples.py` checks five documents and skips `docs/guides/PARTICIPANT.md`, `docs/SETUP.md`, `docs/guides/VALIDATOR-AUTHORING.md` and `docs/CONTENT-AUTHORING-GUIDE.md`. None prints an action command today. | The test checks every Markdown file at the root and under `docs/`, except `docs/audits/**` and five named planning-package files. Test with a planted example in `docs/SETUP.md`. |
| T2 | Low | `PYTHON ?= python3` in the Makefile is never used. | Removed. A test fails on any Makefile variable nothing references. |

## Verdict

**Round 12 does not close DH7.** It found two blocking and four high findings.
