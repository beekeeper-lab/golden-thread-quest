# Release Audit — Round 11

Status: **complete.** Twenty findings returned. They cover nineteen distinct defects, because
C1 and E1 are the same one, and all nineteen were accepted after verification. One more defect
was found here during verification and is recorded as part of T1. Two severities were lowered
on the evidence. Every accepted finding except E14 is fixed, and E14 is stated as a
limitation. Every code fix carries a test that was shown to fail with the fix reverted.

Commit under audit: `ea36037` on `main`, the merge of `chore/round-10-audit`.
Predecessor: `docs/audits/round-10-independent-audit.md`.

## Why this round exists

`docs/ACCEPTANCE-CRITERIA.md` leaves **DH7** open. Ten rounds have run and each found
something. The criterion closes on a round that reports no unresolved blocking or high
findings — a round that finds nothing, not a round whose findings are all fixed.

## Method

Three lenses, each in its own worktree at `ea36037` with `docs/audits/` removed, each given
only paths, a commit and the areas round 10 named. None saw a summary of what the author
believed, and none saw another lens's findings.

| Lens | Scope |
|---|---|
| Curriculum | The eight quests followed literally against their required proofs and validators, stale generated pages while the service runs (round 10's C2), the reviewer flow driven live through a second decision, and accessibility with Playwright at 640px and 1280px |
| Engine | The update path against a real bare upstream with a quest version bump and a progress schema bump, the rebuilt validator child attacked with validators written for the occasion, the service, state integrity, and hostile state files |
| Tooling, tests, documentation | A README-only clean clone, every gate, `make check` beside `make serve`, CI against the Makefile, the guards added in round 10 mutated one at a time, and every document outside this directory |

The engine lens ran on the larger model. The fixes were made on three branches, one per area,
and merged into `chore/round-11-audit`.

## Findings

### Curriculum

| ID | Severity | Finding | Resolution |
|---|---|---|---|
| C1 | High | The "changed since submission" gate and the stale-approval check hashed only the attempt's evidence folder. Every quest requires proof files outside it (`participant/tests/playwright/…`, `participant/context/…`, skill files), so those could be edited after submission or after approval with no warning. Found independently by the engine lens as E1. The curriculum lens rated it Blocking. It is rated High here because the reviewer reads the files as they are on disk: the failure misleads a reviewer and does not make anything unsafe. | Submission and review records carry `proof_files`, a digest per declared proof path outside the package. They are compared at approval, on the review page, and at load after approval (`progress.proof_changed_since_approval`). A record without the field is compared on the package hash alone, so older records neither read as changed nor as forged. Paths that resolve outside `participant/` are recorded as unresolvable and never read. ADR-031 amended. Seven tests. |
| C2 | Low | The reviewer's confirmation read "Approving produces verified completion and verified XP" whatever decision was chosen. The lens rated it High. It is Low here, because the sentence is conditional and true for every decision. | The neutral text says only an approval produces verified completion. Each decision carries its own confirmation in the form, the CLI and the service's refusal. The gate is unchanged. Five tests, one in the browser. |
| C3 | Low | The repository-foundation validator matched ignore-rule categories by substring, so `mysecretfolder/` counted as a credentials rule. | Rules are matched as globs against sample names. Three tests. |
| C4 | — | Round 10's C2: a verified quest shown as "In progress" while the service runs. | **Not reproduced**, through CLI and live-service sequences covering start, submit, needs-changes, resubmit, approve and withdraw. Closed. |

### Engine

| ID | Severity | Finding | Resolution |
|---|---|---|---|
| E1 | High | Same defect as C1. | See C1. |
| E2 | High | `make update-check` crashed with a traceback carrying absolute paths when `progress.yaml` held merge-conflict markers. The crash happened before the merge-in-progress advice `UPDATING.md` relies on was printed. `update` and `update --migrate` crashed the same way on a non-integer `schema_version`, malformed YAML, non-UTF-8, a non-mapping file, a symlink and a directory, all of which `validate` reports cleanly. | The store reads through a bounded reader and reports damage as a `StoreError`. A non-integer version is a `MigrationError`. With a merge in progress the migration report is skipped and `--migrate` is refused. Parametrized test over every variant and both commands. |
| E3 | Medium | On timeout or output overflow, `_terminate_tree` stopped once the direct child was reaped, so a grandchild that ignores SIGTERM outlived the run. The lens rated it High. It is Medium here: validators are registered repository code, and round 10 rated the neighbouring case Medium. | The group ID is recorded at spawn, and the group always gets SIGKILL after the grace period. Two tests, one for timeout and one for overflow. |
| E4 | Medium | PROOF.md was rendered through a symlink to anywhere. The hash recorded the link text, and the secret scan skipped links, so a retargeted link changed what the review page showed with no stale warning. | A link leading out of the package is a scan finding that blocks submission, is not rendered, and raises a load warning. A link inside the package is hashed by the content it points at. ADR notes that a package holding a link hashes differently from before. Seven tests. |
| E5 | Medium | A hand-edited `state: locally_validated` with no validation results loaded silently and was shown under the registered validator's authority. | At load it is an error unless each declared validator has a qualifying result, as with a forged `verified`. It does not require the latest result to pass, because ADR-017 says a failing re-run leaves the attempt where it is. ADR-017 amended. Five tests. |
| E6 | Medium | `UPDATING.md` said migrations "refuse to drop an attempt or a field", but the guard checks top-level keys and attempt IDs only. | The document says exactly that. The guard is not made recursive, because a legitimate migration renames nested fields. |
| E7 | Medium | State files had no size ceiling and were read through symlinks: an 18 MB `progress.yaml` hung `validate`, a link to `/dev/zero` raised `MemoryError`, and a FIFO hung. | `quest_app/safe_io.py` reads state only from small regular files, with a 2 MB ceiling, in both the content loader and the store. Parametrized test over FIFO, device and oversize for each state file. |
| E8 | Medium | `make migrate` did not take the progress lock that every action holds. | The migration runs under `ProgressStore.exclusive()`. Test. |
| E9 | Low | The restore after a failed migration turned CRLF into LF. | It restores bytes. Test. |
| E10 | Low | On environment failure the last stderr line was copied verbatim, absolute paths included, contrary to the runner's own redaction rule. | The line is path-redacted. Test. |
| E11 | Low | Twenty thousand checks exceeded the 1 MiB ceiling and became `environment_failure`, so the `MAX_CHECKS` truncation was never reached. | The child truncates before serializing. Test. |
| E12 | Low | The printed update sequence never named `make migrate`, and stale-version notes were suppressed until migration ran. | `UPDATING.md` and the printed sequence name `make migrate` after `make validate-content`. Test. |
| E13 | Low | The review page for an attempt on an older quest version said "Quest version 2" with no note that a newer version is published. | The page names the published version and says that earlier criteria text is not kept. Test. |
| E14 | Low | The quest page shows only the current version's criteria to a participant whose attempt is on an older version. | Not fixed. The application keeps no text of earlier quest versions. It stays a known limitation and the review page now states it (E13). |

### Tooling, tests, documentation

| ID | Severity | Finding | Resolution |
|---|---|---|---|
| T1 | Medium | `tools/check_yaml_safe.py` exempted any file named `check_yaml_safe.py` in any directory. The lens found that the `yaml_loader.py` exemption was untested against a same-named file elsewhere, and the basename exemption was found here during verification. | Both exemptions match exact relative paths. Tests plant an unsafe call in each basename in another directory. |
| T2 | High | Every CLI example for `start-quest`, `submit-for-review` and `record-review` in `USER-GUIDE.md` and `REVIEWER.md` omitted the required `--confirm`, so a participant following the guide was refused at the first action. The troubleshooting table misdiagnosed that refusal as an illegal transition. | `--confirm` added to every example, each run as printed against a scratch copy, and a troubleshooting row added. `tests/integration/test_doc_cli_examples.py` fails when a document shows a confirmed action without the flag. |
| T3 | Medium | Removing the `returncode != 0` half of the runner's failure test left the suite green. | Test: a validator that writes a complete result and then exits nonzero is `environment_failure`. The contract states the rule. |

The tooling lens reported one operational mistake, and it is recorded here because it could
look like an application defect. It stopped its own `make serve` with `pkill -f`, which also
stopped the servers the other lenses were running. No files were affected.

## Gates

| Gate | Result |
|---|---|
| `make check` | pass — 751 passed, 43 deselected |
| `make test-ui` | pass — 43 passed |
| `make validate-content` | pass — 8 quests, 8 regions, 4 badges, 1 track, 0 warnings |
| `make verify-package` | pass — the exported archive installs, validates and builds on its own |
| Clean clone of `chore/round-11-audit` from GitHub | pass at `2b42f71`: `make setup`, `make check` (749 passed, 4 skipped without the UI extras), and `make serve` on a second port |
| `make check` beside a running `make serve` | pass, here and by the tooling lens |
| Each fix reverted one at a time | every new test failed with its fix reverted: C1, C2, C3, E2 (store, version guard, merge skip), E3 (both paths), E4, E5, E7, E8, E9, E10, E11, E13, T1, T2 and T3 |
| Round-10 guards mutated by the tooling lens | 13 mutations, 11 caught; the two that were not are T1 and T3, now fixed |
| CI on this branch | see the pull request |

The suite grew from 689 to 751, and `make test-ui` grew from 42 to 43.

## Verdict

**Round 11 does not close DH7.** It found three high findings and no blocking ones.

C1 has the same shape as the blocking finding in round 10. The integrity check guarded the
folder the application creates, and a quest's proof names files the participant creates
anywhere in their repository. Both lenses that drove a quest end to end found it
independently. E2 is the round-10 merge-in-progress fix failing in the one case it was written
for, a conflict in the participant's own state. T2 is a guide that had not been run as printed
since the confirmation gate moved server-side.

What held: nothing but a reviewer's approval reaches verified state or verified XP. The update
happy path kept attempt versions, reviews and submissions through a real quest bump and schema
bump. Shadow modules, output floods and pipe-holding grandchildren did not affect the runner.
The service refused every malformed request without a 500. A stale page while the service
runs was not reproduced.

Round 12 should run against the merge commit, with the same three lenses. Point it at:

- the new `proof_files` record: paths that move between quest versions, a proof path that is
  a directory, and a reviewer who approves after the participant deletes a file;
- `safe_io.py` and the symlink rules, now applied in three places, for consistency between
  render, hash, scan and load;
- the `locally_validated` load check against every legitimate path into and out of that state;
- the documentation test for `--confirm`, and every other command a guide prints, run as
  printed;
- and the tests added this round, mutated the same way.
