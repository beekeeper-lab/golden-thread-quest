# Release Audit — Round 14

Status: **complete.** Nineteen findings returned. Fifteen were accepted after verification,
two were duplicates of accepted findings, and none was rejected. Four severities were lowered
on the evidence. Every accepted finding is fixed, or corrected in the documentation where the
finding was about a claim. Every code fix carries a test that was shown to fail with the fix
reverted.

Commit under audit: `3b9b7c2` on `main`, the merge of round 13.
Predecessor: `docs/audits/round-13-independent-audit.md`.

## Method

Three lenses, each in its own worktree at `e879341`, a commit on a throwaway branch that
deletes `docs/audits/` and the design guide's status part. Each was given only paths, a commit
and the areas round 13 named. The engine lens ran on the larger model. The curriculum lens
drove every action through a real Chromium browser.

**Independence was better than round 13 and still not complete.** No lens restored the
removed files, because their removal was committed. The tooling lens did confirm that the
removed design-guide files exist on `main`, so a lens can still reach earlier records through
Git history. No report cites an earlier audit. Round 15 should give each lens a shallow clone
of the throwaway commit (`git clone --depth 1`), which has no history to reach.

## Findings

Every finding was verified here by reproduction or by reading the code at the cited line.

### Curriculum

| ID | Severity | Finding | Resolution |
|---|---|---|---|
| C1 | Medium | Every validator panel says "Start the local service to run this check" on pages the running service built, next to a run button that works. `ValidatorView.available` was hard-coded `False` in `build.py`. The lens rated it High. It is Medium here: the action works and only the sentence is wrong. | The panel follows the service view the page was built with. Three tests. |
| C2 | — | "Evidence committed: yes" for an evidence package Git has never seen. Duplicate of E3. | See E3. |
| C3 | High | A submitted or verified quest's page lists every required item as "Not detected". The quest page built its checklist with no detection state, while the evidence page used it. | The quest page uses the same detection as the evidence page once an attempt exists. Before an attempt, "Not detected" stays. Two tests. |
| C4 | Medium | The reviewer page's "evidence changed since submission" banner compares the files as they were at the last build. A reviewer who only reads pages, as the reviewer guide allows, can miss a change made after it. Recording a decision does re-check the files and blocks an unacknowledged approval. | The banner says when its comparison was made and that recording a decision checks the files again. `docs/guides/REVIEWER.md` matches. The pages stay static. Two tests. |
| C5 | — | Double slash in a finding path under a declared directory. Duplicate of E10. | See E10. |

### Engine

| ID | Severity | Finding | Resolution |
|---|---|---|---|
| E1 | High | Round 13's E11 fix removed the leading word boundary from every fixed-prefix secret pattern, and every pattern ignored case. Ordinary text then counted as a secret: `…/48-task-review-onboarding-checklist` matched the OpenAI key pattern and `network_test_connectivity` matched the Stripe one. A Trello card URL in proof blocked `mark-evidence-ready`, and the Trello, GitHub and Jira quests ask for such URLs. | Fixed-prefix patterns are case-sensitive. Distinctive prefixes (`ghp_`, `AKIA`, `glpat-`, `xox?-`, `AIza`, `sk-ant-`, `ATATT3`, `eyJ` and the new ones in E7) still match with a letter directly before them. The short generic prefixes (`sk-`, `sk_`/`rk_live`/`rk_test`, `npm_`) now need a non-alphanumeric character before them and a digit in the body. This takes back part of round 13's E11 for those three prefixes on purpose: a letter glued to `sk-` is ordinary text far more often than it is a key. Thirteen false-positive tests from realistic evidence, detection tests kept. |
| E2 | Low | A genuine approval copied from another participant's repository, with their package, makes an attempt verified with no warning. First attempt IDs and the default participant ID are the same everywhere. The lens rated it High. It is Low here: a participant who can copy that record can equally write one, which ADR-030 already accepts, so the copy gives no new capability. `docs/SECURITY-AND-PRIVACY.md` overstated the check. | The security document says the check is internal consistency (attempt, quest, version), not participant identity. Known limitation 2 in the release notes says a copied approval cannot be told from a forged one inside the repository and names Git history, or review through pull requests, as the signal. No code change. |
| E3 | High | The evidence page shows "Evidence committed: yes" for evidence Git has never seen. `git_status.inspect` counted untracked paths but never added them to the paths it checks, so every new attempt was in this state. | Untracked paths are checked, including a new folder reported as one line. Evidence outside the repository reads as unknown instead of committed. Three tests against a real repository. |
| E4 | Medium | Declared proof outside the package was scanned with the whole `participant/` tree as its link boundary and hashed with the declared path as its boundary. A token behind a directory link was not found, content behind a file link could change after approval with no change to the hash, and a declared file linked outside `participant/` was skipped with no finding. | Scan and hash use the declared path as the boundary. A link out of it, and a declared path that cannot be resolved, are findings. A directory link is a finding instead of being silently skipped. Four tests. |
| E5 | Medium | The scan and the hash skipped a directory they could not list. A `chmod 000` folder holding a token was submitted with `secret_scan_clean: true`. Round 13's E8 covered unreadable files, not directories. | Both walk with an error handler. An unlistable directory is the same "could not be read" finding and `UnreadableFileError` the file case uses. Two tests. |
| E6 | Medium | With no configured participant root, a committed `participant` symlink was followed, and `start-quest` wrote progress, evidence and locks outside the clone and appended to an `ACTIVITY.md` there. The fix branch rated it High. It is Medium here, as round 12 rated the same shape inside `participant/`. | A default `participant` that is a link is refused before anything is resolved. A root configured by `GTQ_PARTICIPANT_ROOT` or `--participant-root` stays trusted (ADR-042). ADR-043 amended. Two tests, one proving nothing reaches a sentinel outside the clone. |
| E7 | Medium | The scan missed GitHub fine-grained tokens, Trello `ATTA` tokens, Slack `xapp-` tokens, Google `ya29.` tokens, a credential in a `key=` or `token=` query parameter, and any token in a UTF-16 file such as PowerShell `>` output. | Patterns added for each. UTF-16 is detected by its byte-order mark or its NUL ratio and decoded before scanning. Six tests. The query-parameter pattern was checked here against Trello, GitHub, Jira and OAuth callback URLs with no false positive. |
| E8 | Low | The live request token was substituted anywhere in a served page, including inside participant-written `PROOF.md`, so a link in proof could carry it off the machine. Chromium still refused a cross-origin post carrying it, so this weakened the second of two defences. | Only the exact hidden-input attribute the templates emit is substituted. Two tests. |
| E9 | Low | A process a validator starts in a new session survives the timeout kill. No registered validator starts processes. | `docs/VALIDATOR-CONTRACT.md` says a validator must not start a process outside its own process group and that such a process is not cleaned up. |
| E10 | Low | Findings under a declared directory with a trailing slash showed a double slash. | The trailing slash is removed before the path is joined. Test. |

The engine lens also named three suspicions it did not reproduce: hashes differing across
machines for Unicode file names (NFC and NFD), a committed `generated.previous/` holding the
output marker being deleted by a build, and a bypass of round 13's E7 content-hash guard for a
quest with two or more validators, which no current quest has. They are not accepted and are
listed for round 15.

### Tooling, tests, documentation

| ID | Severity | Finding | Resolution |
|---|---|---|---|
| T1 | Medium | `safe_io.unlink_regular_file` refuses to remove anything but a regular file, and no test covered that. Disabling it passed the suite. | Tests for a FIFO, a directory and a link, each failing with the refusal removed. |
| T2 | Medium | `actions._is_confirmed`, the confirmation check in front of every state change including `record-review`, had no test of its allowlist. Collapsing it to `bool(value)` passed everything. The lens rated it High. It is Medium here: the code was right and the gap was in the tests. | Unit tests of accepted and denied values, and integration tests calling `record-review` with each denial that assert nothing in the participant tree changed. Thirteen fail with the check collapsed. |

## Gates

| Gate | Result |
|---|---|
| `make check` | pass — 997 passed, 56 deselected |
| `make test-ui` | pass — 56 passed |
| `make validate-content` | pass — 8 quests, 8 regions, 4 badges, 1 track, 0 warnings |
| `make verify-package` | pass |
| Clean clone at `3b9b7c2`, by the tooling lens | pass: `make setup` and `make check` (903 passed, 5 skipped without the UI extras), and `make check` beside a running server |
| A new quest added by following the authoring guide | picked up by the catalog, region, tags, home, search and relationships indexes and the evidence page, with no template or code change |
| Each fix reverted one at a time | every new test failed with its fix reverted, by the branch that wrote it |
| Guards mutated by the tooling lens | 14 mutations, 12 caught, apart from T1 and T2 |
| CI on this branch | see the pull request |

The three fix branches (`fix/r14-scan`, `fix/r14-web`, `fix/r14-io`) merged with conflicts
only in the test counts in `README.md` and `docs/RELEASE-NOTES.md`, which were recounted after
the merge. No other follow-up was needed.

## Verdict

**Round 14 does not close DH7.** It found three high findings and no blocking one, the first
round without a blocking finding.

E1 is a regression made by round 13's fix for its E11. The fix was tested for what it should
catch and not for what it should leave alone. E3 and C3 are two pages that told the participant
something untrue about their own evidence. E4 and E5 are the same kind of gap round 13 closed
for files: the scan and the hash disagreed about what they cover.

What held: nothing but a reviewer's approval reached verified state. All eight quests were
completed through real browser forms, with six approvals (two acknowledging changed evidence),
one request for changes and one rejection, and claimed and verified XP agreed on every page.
axe found no violations on 15 page types at two widths. Links at every path the application
owns were refused by the build. The service's host, origin and path checks held, including
real cross-origin form posts from Chromium.

Round 15 should run against the merge commit with the same three lenses, each in a shallow
clone of a commit without the audit records. Point it at:

- the secret patterns as changed by E1 and E7, for both misses and false positives in real
  evidence from the Trello, GitHub and Jira quests;
- the new walk in the scan and the hash (links, unreadable directories, declared paths);
- the participant-root refusal and every other place a fixed name inside the clone is trusted;
- the three unreproduced suspicions above;
- and the tests added this round, mutated the same way.
