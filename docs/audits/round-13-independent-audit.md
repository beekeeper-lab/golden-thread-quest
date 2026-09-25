# Release Audit — Round 13

Status: **complete.** Twenty-four findings returned. Twenty-three were accepted after
verification and one was not reproduced. Five severities were lowered on the evidence. Every
accepted finding is fixed except E12, which is mitigated and stated. Every code fix carries a
test that was shown to fail with the fix reverted.

Commit under audit: `a942237` on `main`, the merge of the design guide. Its code is the same
as `0018e2d`, the merge of round 12.
Predecessor: `docs/audits/round-12-independent-audit.md`.

## Method

Three lenses, each in its own worktree at `a942237` with `docs/audits/` and the design
guide's status part removed, each given only paths, a commit and the areas round 12 named.
The engine lens ran on the larger model. The curriculum lens drove every action through a
real Chromium browser.

**Independence was weaker than intended.** The curriculum and tooling lenses each found the
removed files showing as deletions and restored them with `git checkout -- .` before they
started, so both could have read earlier audit records. Neither report cites one. Their
findings are treated as evidence like any other and were verified here. The next round must
remove those files in a way a lens cannot undo, for example by committing their removal on a
throwaway branch.

## Findings

Every finding was verified here by reproduction or by reading the code at the cited line.

### Curriculum

| ID | Severity | Finding | Resolution |
|---|---|---|---|
| C1 | High | The secret scan reads only the evidence package. The proof files a quest requires outside it (`participant/context/**`, `participant/skills/**`) are never scanned, and both pages then say no secret was found. The lens rated it Blocking. It is High here: the scan is documented as a safety net over the package and nothing publishes those files, but the pages' reassurance is false. | `scan_declared_proof` scans the package and every declared proof path outside it under the same rules (no links out of `participant/`, the 2 MB ceiling, the skip list). Both gates and both pages use it. `docs/SECURITY-AND-PRIVACY.md` updated. Five tests. |
| C2 | High | `mark-evidence-ready` calls a link out of the package or an oversized file "secret-like" (`actions.py` `_require_clean_secret_scan`). Submission words them correctly, but participants reach this gate first. | `describe_scan_findings` words secret, link and oversize findings, and both gates share it. Three tests. |
| C3 | Medium | Every quest page has two landmarks named "Required evidence": the authored section and the generated checklist. axe `landmark-unique`. | The generated checklist's landmark is named "Required evidence checklist". The browser accessibility test now fails on `landmark-unique` and `region` at any impact. |
| C4 | Medium | At 640px the top bar's brand link sits outside any landmark on every page. axe `region`. | The top bar is a `<header>` landmark. Test at 640px. |
| C5 | High | After an approval that acknowledged changed evidence, the review page still shows the submission's hash and the "acknowledge this before approving" banner on a verified attempt. | A decided attempt shows the hash the review recorded and compares drift against the decision, with the approval-aware wording. Three tests: still submitted, verified with acknowledgement, verified then edited. |
| C6 | Low | `rejected` and `needs_changes` lead to the same state and badge, and no guide says so. The lens rated it Medium. | The page says a rejected attempt lands in needs-changes and what the participant can do next. Both guides say it. Test. |

### Engine

| ID | Severity | Finding | Resolution |
|---|---|---|---|
| E1 | Blocking | The generated root is resolved through links, and a build renames and deletes it. A committed `generated -> ..` link, or `GTQ_GENERATED_ROOT` pointed at an existing folder, deletes that folder, including the repository. Verified in `config.py` and `build.py` `_swap`. | The generated and local-data roots are no longer resolved through links. The build refuses, before locking, writing or deleting, a root or sibling that is a link, overlaps a source folder or the participant or local-data root, or is a non-empty folder without the application's marker or build manifest. ADR-043. Thirteen tests, each with a sentinel outside the clone. A `generated.building` folder left by a crash before this fix has no marker and is refused until `make clean` removes it. |
| E2 | Blocking | Writes under `local-data/` follow links: the build error page, the service port file and `generated.lock`. A committed link overwrote a file outside the clone. | The error page, the port file, stale-port pruning and the build lock go through the no-follow path with a `local-data` prefix. Eight tests with a sentinel outside the clone. |
| E3 | Medium | A `submitted` state is accepted with a submission record copied from another quest and attempt. The lens rated it High. It is Medium here, as round 12 rated E4. | A submission, review or archived review whose attempt, quest or version does not match the attempt is a load error, and a decision refuses it. Three tests. |
| E4 | Medium | `serve --port` ignores `GTQ_GENERATED_ROOT` and `GTQ_LOCAL_DATA_ROOT`, so the service and the CLI use different roots. | `serve` carries every configured root. Test that the service and a CLI action agree. |
| E5 | Medium | `progress.yaml`, `review.yaml`, `submission.yaml` and the archives are read and honored through links leading out of the tree, and key names of the linked file reach the problem report. | `read_state_yaml` refuses a link and names only the record. Used for every state record, the progress store and the update restore. Seven tests. |
| E6 | Medium | The evidence hash skips any nested `validation` folder and nested files named `submission.yaml` or `review.yaml`, not only the top-level records. | Only top-level names are skipped. ADR-031 notes that packages with such nested names hash differently. Test. |
| E7 | Medium | Lowering `quest_version` by hand turns a forged `locally_validated` from an error into a warning; the attempt's `content_hash` is not cross-checked. | The downgrade applies only when the attempt's content hash differs from the published quest's. Two tests: the forged and the genuine older version. |
| E8 | Medium | An unreadable file in a submitted or verified package crashes `validate` and `build` with a traceback carrying absolute paths. | An unreadable file is reported by its relative path, counts as changed for the stale checks, and a decision refuses cleanly. A read failure is no longer reported as a write failure. Four tests. |
| E9 | Medium | The repository-foundation validator reads only part of a large file and passes its secret check; `Workspace.read_text` reads the whole file first. | `Workspace.read_text_bounded` reads at most the limit from disk, and the secret check reports `inconclusive` when it could not read everything. Two tests. |
| E10 | Low | A check's `severity` is not normalized, so one bad value throws away the run. | An invalid severity is normalized. Three tests. |
| E11 | Low | Redaction and the evidence scan need a word boundary before a token, so `nnnghp_…` is stored in clear. | The leading word boundary is dropped from eleven fixed-prefix patterns. Nine detection tests and two false-positive tests. |
| E12 | Low | A validator that closes its result channel and then exits nonzero is recorded as its written verdict. | Mitigated, not fixed. The grace period before a leftover process is killed is 3 seconds instead of 1, so a validator that exits nonzero within it is judged by its exit status. One that exits later is still judged by its written verdict. The contract states the rule. Validators are program-owned. Two tests. |

### Tooling, tests, documentation

| ID | Severity | Finding | Resolution |
|---|---|---|---|
| T1 | Low | The README's caveat says the printed count reads "one or two higher" without the UI extras; it reads three higher. | The sentence explains the whole-module skips without a number. |
| T2 | Medium | `scripts/build_user_guide_html.py` falls back to a path in one maintainer's home directory, contrary to CONTRIBUTING's "without them the script says so and stops". | The home-directory fallback is removed. The script stops with its message unless `GTQ_HTML_SNIPPETS` is set. CONTRIBUTING matches. Test. |
| T3 | Medium | The README's Status section says three audits have run. Twelve have. The lens rated it High. It is Medium here: it misstates history, not how to use the system. | The Status section points at DH7 and `docs/audits/` without counts. |
| T4 | Low | The README says "ten known limitations"; the release notes number eleven, from 0. | The limitations are numbered 1 to 11, the README states no count, and a test checks the numbering. |
| T5 | — | One `make check` run in a clean clone failed the session guard. Not reproduced in four attempts, and the lens had left a server of its own running. Not accepted. | — |
| T6 | Low | In the lens's Chromium the browser form tests pass with the old referrer policy, so they do not guard it there. The header is still asserted by `tests/security/test_service.py`. The meta tag in `base.html.j2` is not asserted anywhere. The lens rated it Medium. | A test checks the meta tag on rendered pages. |

## Gates

| Gate | Result |
|---|---|
| `make check` | pass — 905 passed, 56 deselected |
| `make test-ui` | pass — 56 passed |
| `make validate-content` | pass — 8 quests, 8 regions, 4 badges, 1 track, 0 warnings |
| `make verify-package` | pass |
| Clean clone of `chore/round-13-audit`, with `make check` beside `make serve` | see below |
| Each fix reverted one at a time | every new test failed with its fix reverted, by the branch that wrote it |
| Round-12 guards mutated by the tooling lens | 10 mutations, 10 caught, apart from T6 |
| CI on this branch | see the pull request |

The four fix branches (`fix/r13-fs`, `fix/r13-scan`, `fix/r13-integrity`, `fix/r13-docs`)
merged with one textual conflict in `progress.py`, resolved by keeping both the link refusal
and the identity check. No other follow-up was needed.

## Verdict

**Round 13 does not close DH7.** It found two blocking and three high findings.

E1 and E2 extend round 12's write rule to the folders the application itself owns. Round 12
covered `participant/` and assumed `generated/` and `local-data/` were safe because they are
ignored by Git, but a symlink is stored as a file and a forced add commits one anyway. C1 has
the shape of round 11's C1: a check that covered the evidence package and not the proof files
outside it.

What held: nothing but a reviewer's approval reached verified state. All eight quests were
completed through real browser forms, including every decision and the acknowledged approval.
The participant write path, the service's request checks and the update path held under attack.

Round 14 should run against the merge commit with the same three lenses, with the audit
records removed by a commit the lenses cannot undo. Point it at:

- every place the application reads or writes outside `participant/`, now that `generated/`
  and `local-data/` have their own rules (ADR-043);
- `scan_declared_proof` against every proof shape the eight quests declare;
- the identity check on submission and review records, and the content-hash check on
  `locally_validated`;
- secret patterns without the leading word boundary, for false positives in real evidence;
- and the tests added this round, mutated the same way.
