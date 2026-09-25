# Release Audit — Round 13

Status: **in progress.** Findings recorded and verified. Fixes under way.

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
| C1 | High | The secret scan reads only the evidence package. The proof files a quest requires outside it (`participant/context/**`, `participant/skills/**`) are never scanned, and both pages then say no secret was found. The lens rated it Blocking. It is High here: the scan is documented as a safety net over the package and nothing publishes those files, but the pages' reassurance is false. | |
| C2 | High | `mark-evidence-ready` calls a link out of the package or an oversized file "secret-like" (`actions.py` `_require_clean_secret_scan`). Submission words them correctly, but participants reach this gate first. | |
| C3 | Medium | Every quest page has two landmarks named "Required evidence": the authored section and the generated checklist. axe `landmark-unique`. | |
| C4 | Medium | At 640px the top bar's brand link sits outside any landmark on every page. axe `region`. | |
| C5 | High | After an approval that acknowledged changed evidence, the review page still shows the submission's hash and the "acknowledge this before approving" banner on a verified attempt. | |
| C6 | Low | `rejected` and `needs_changes` lead to the same state and badge, and no guide says so. The lens rated it Medium. | |

### Engine

| ID | Severity | Finding | Resolution |
|---|---|---|---|
| E1 | Blocking | The generated root is resolved through links, and a build renames and deletes it. A committed `generated -> ..` link, or `GTQ_GENERATED_ROOT` pointed at an existing folder, deletes that folder, including the repository. Verified in `config.py` and `build.py` `_swap`. | |
| E2 | Blocking | Writes under `local-data/` follow links: the build error page, the service port file and `generated.lock`. A committed link overwrote a file outside the clone. | |
| E3 | Medium | A `submitted` state is accepted with a submission record copied from another quest and attempt. The lens rated it High. It is Medium here, as round 12 rated E4. | |
| E4 | Medium | `serve --port` ignores `GTQ_GENERATED_ROOT` and `GTQ_LOCAL_DATA_ROOT`, so the service and the CLI use different roots. | |
| E5 | Medium | `progress.yaml`, `review.yaml`, `submission.yaml` and the archives are read and honored through links leading out of the tree, and key names of the linked file reach the problem report. | |
| E6 | Medium | The evidence hash skips any nested `validation` folder and nested files named `submission.yaml` or `review.yaml`, not only the top-level records. | |
| E7 | Medium | Lowering `quest_version` by hand turns a forged `locally_validated` from an error into a warning; the attempt's `content_hash` is not cross-checked. | |
| E8 | Medium | An unreadable file in a submitted or verified package crashes `validate` and `build` with a traceback carrying absolute paths. | |
| E9 | Medium | The repository-foundation validator reads only part of a large file and passes its secret check; `Workspace.read_text` reads the whole file first. | |
| E10 | Low | A check's `severity` is not normalized, so one bad value throws away the run. | |
| E11 | Low | Redaction and the evidence scan need a word boundary before a token, so `nnnghp_…` is stored in clear. | |
| E12 | Low | A validator that closes its result channel and then exits nonzero is recorded as its written verdict. | |

### Tooling, tests, documentation

| ID | Severity | Finding | Resolution |
|---|---|---|---|
| T1 | Low | The README's caveat says the printed count reads "one or two higher" without the UI extras; it reads three higher. | |
| T2 | Medium | `scripts/build_user_guide_html.py` falls back to a path in one maintainer's home directory, contrary to CONTRIBUTING's "without them the script says so and stops". | |
| T3 | Medium | The README's Status section says three audits have run. Twelve have. The lens rated it High. It is Medium here: it misstates history, not how to use the system. | |
| T4 | Low | The README says "ten known limitations"; the release notes number eleven, from 0. | |
| T5 | — | One `make check` run in a clean clone failed the session guard. Not reproduced in four attempts, and the lens had left a server of its own running. Not accepted. | |
| T6 | Low | In the lens's Chromium the browser form tests pass with the old referrer policy, so they do not guard it there. The header is still asserted by `tests/security/test_service.py`. The meta tag in `base.html.j2` is not asserted anywhere. The lens rated it Medium. | |

## Verdict

**Round 13 does not close DH7.** It found two blocking and three high findings.
