# Release Audit — Round 10

Status: **complete.** Thirty-three findings returned. Thirty-two were accepted after
verification here and one was not accepted. Every accepted finding is fixed or, where the
fix is an isolation layer release one does not have, stated as a limitation in the
contract it belongs to. Every code fix carries a test that fails without it.

Commit under audit: `8df0ac5` on `main`, the merge of `chore/round-09-audit`.
Predecessor: `docs/audits/round-09-independent-audit.md`.

## Why this round exists

`docs/ACCEPTANCE-CRITERIA.md` leaves **DH7** open. Nine rounds have run and each found
something. The criterion closes on a round that reports no unresolved blocking or high
findings — a round that finds nothing, not a round whose findings are all fixed.

## Method

Three lenses, each in its own worktree at `8df0ac5`, each given only paths, a commit and the
areas round 9 named: no summary of what the author believed, no sight of each other's
findings, and no access to `docs/audits/`.

| Lens | Scope |
|---|---|
| Curriculum | The eight quests against their validators, the generated site, the reviewer flow driven live through a second decision on one attempt, and accessibility measured with Playwright at 640px |
| Engine | The action layer and service, the validator subsystem with validators written to break it, `view_models.py` and `progress_calc.py`, `update.py` and `migrations.py` against a real bare upstream with a version bump, and hostile content |
| Tooling, tests, documentation | The Makefile, CI, a README-only clean clone, `make check` beside `make serve`, the suite mutated guard by guard, and every document outside this directory |

The engine lens ran on a larger model than the other two because its scope is where a
defect is unsafe rather than wrong.

## Findings

### Curriculum

| ID | Severity | Finding | Resolution |
|---|---|---|---|
| C1 | High | `jira-read-assigned-stories` required a skill file and a Markdown index; its required validator read only the first `*.json` under `participant/context/jira`, which the quest never mentioned. Following the quest could only ever return `inconclusive`, so `locally_validated` was unreachable. A JSON reconciliation summary — one of the quest's stretch goals — could be checked in place of the stories. | The validator reads one named file, `participant/context/jira/assigned/stories.json`. The quest requires it as proof and documents its shape. Quest version 2. Tests tie the validator's path to the quest's required proof and prove a neighbouring JSON file is not checked instead. |
| C2 | — | The home page once showed a verified quest as "In progress". | **Not accepted.** Not reproduced by the lens or here. The recommender excludes verified and submitted quests, and every action rebuilds before it answers; the captured page is consistent with a build from before resubmission. Carried to round 11. |

### Engine

| ID | Severity | Finding | Resolution |
|---|---|---|---|
| E1 | **Blocking** | After a quest version bump, approving an attempt started on the old version wrote the current content version into the review. The integrity check then read the reviewer's own approval as a forgery and refused to load participant state: `validate`, `build` and every action failed. `docs/guides/UPDATING.md` promises attempts keep their version, so this is the documented update flow. | Submission and review record `attempt.quest_version`. Test bumps the quest under an attempt, submits and approves, and asserts verified. |
| E2 | High | The validator child ran as `python -m` with its working directory in `participant/`, which put that directory first on the import path. A participant's `validators/` package replaced registered code, and a `json.py` would replace the standard module. | The child starts with `-s -c` and a bootstrap that puts the repository at the head of the path. Test shadows the validator and `json` from `participant/`. |
| E3 | High | The evidence secret scan skipped any file that was not valid UTF-8, so one Latin-1 byte hid a credential from the gate before evidence-ready and submission. | Files are decoded with replacement; a file that cannot be read blocks. Two tests. |
| E4 | High | A malformed `submission.yaml` or archived `review-*.yaml` passed `validate` and crashed `build` with a traceback carrying absolute paths. A merge conflict leaves exactly this. | Both are parsed and schema-validated at load. Parametrized test over both files and both kinds of damage. |
| E5 | Medium | `check_quest_references` had no caller: a quest naming an unregistered validator, or one registered for another quest, passed `validate` and `build`. An unparseable registry surfaced as raw parser or codec text. | `load_world` loads the registry and runs the cross-check; the registry is read through the content reader. Four tests. |
| E6 | Medium | Non-UTF-8 output from a validator raised `UnicodeDecodeError` in the parent and the run disappeared, contrary to the contract. | Output is read as bytes and decoded with replacement. Test on both streams. |
| E7 | Medium | `communicate()` read all output into memory before any limit applied (300 MB raised the parent to 920 MB), and a stray `print()` corrupted the result channel. | Output is read incrementally under a 1 MiB ceiling per stream; the run is stopped past it. The child moves its own stdout to stderr. Tests measure the parent's peak RSS and a stray print. |
| E8 | Medium | The process group was killed only on timeout: a grandchild outlived a finished run, and one holding the pipe turned a pass into `interrupted`. A grandchild that starts its own session outlives even the timeout kill. | The group is killed when the child exits, and the run ends on the child's exit, not on the pipes closing. Two tests. The own-session case needs an isolation layer and is stated as a limitation in `docs/VALIDATOR-CONTRACT.md`. |
| E9 | Medium | Runs completing in the same second were ordered by a random suffix, so an earlier pass could stand as latest over the fail after it. | Run IDs carry microseconds. Test. |
| E10 | Medium | No command applied a migration, a progress file declaring a newer schema was loaded and rewritten in the old shape, and the update allowlist carried a `fetch` nothing used. | `make migrate` (`quest update --migrate`) validates before and after and restores the original if state does not load. A newer or older progress file is refused at load with the command to run. The unused permission is removed. Three tests. |
| E11 | Medium | During a merge conflict the update check advised `git add -A && git commit`, which commits the conflict markers. | A merge in progress is its own blocking finding, pointing at resolving or `git merge --abort`. Test with a real conflict. |
| E12 | Low | An absolute proof path, an invalid schema file, a FIFO, a symlink to `/dev/zero` or to a file outside `content/` produced a traceback, a hang, an out-of-memory kill, or a silent load. | `ContentProblem.build` redacts an absolute path; a broken schema is one sentence from the CLI; discovery reads only regular files inside `content/` and reports the rest. Five tests. |
| E13 | Low | Sixty thousand `[` and a non-object `parameters` answered 500 with "Any change you made was recorded" before anything ran. | Refused as 400. Two tests. |
| E14 | Low | `?problem=` put any text a link chose inside a real alert on a real page. | The redirect carries an identifier for a message the service wrote; unknown identifiers show nothing. Existing tests now read the alert from the page. |
| E15 | Low | A request body that never arrived held a handler thread indefinitely. | 30-second socket timeout, answered by closing. Test. |
| E16 | Low | The off-site redirect guard missed a backslash path. | Refused. The existing test is parametrized over both forms. |
| E17 | Low | A run whose checks were all `skipped` was classed `pass` and qualified for `locally_validated`. | Classed `inconclusive`. Test. |
| E18 | Low | `network: denied` is recorded in every result and enforced nowhere. | Stated as a declaration in `docs/VALIDATOR-CONTRACT.md` and `docs/SECURITY-AND-PRIVACY.md`, with the other limits of the validator controls. |

### Tooling, tests, documentation

| ID | Severity | Finding | Resolution |
|---|---|---|---|
| T1 | High | The canonical registry example in `docs/guides/VALIDATOR-AUTHORING.md` declared `max_output_bytes: 200000`; the schema caps it at 20000, so copying the guide produced a registry that does not validate. | Example corrected. |
| T2 | High | `docs/IMPLEMENTATION-PLAN.md` left Stages 4, 5, 7, 8 and 9 unchecked and named audit files that were never written, while `README.md` and `PLANNING-STATUS.md` said those stages were complete. A reader following the plan, as `CLAUDE.md` requires, would conclude the opposite. | Rows point at `stage-04-to-09-implementation-audits.md`; completed items checked; Stage 10 left open. |
| T3 | Medium | Two documents called the clean-clone install untested and an open traceability row; the DH1 row names the `clean-export` CI job. | Reworded to match. |
| T4 | Medium | "A green `make check` means a green CI" — CI has three jobs and `make check` is one. | Scoped to the `check` job. |
| T5 | Medium | Component counts said ten; there are eleven since round 9 added the reviewer findings panel. | Corrected. |
| T6 | Medium | The FS1 test never called `quest_app.update`: it passed with `update.py` gutted. | Rewritten to run `preflight()` and the printed commands against a real upstream. Fails when the merge line is removed. |
| T7 | Medium | `tools/check_yaml_safe.py`, the ADR-025 gate, had no test. | `tests/security/test_yaml_safe_tool.py`. Fails when the pattern or the exception list is broken. |
| T8 | Low | The token-statement test passed with the Python guard removed, because the schema also caught it. | Asserts the guard's own message. |
| T9 | Low | "`make check` takes about a minute"; it takes between four and five. | Reworded. |
| T10 | Low | ADR-019's heading said Python 3.12 while its amendment and `pyproject.toml` say 3.10. | Heading corrected. |
| T11 | Low | `.pre-commit-config.yaml` was mentioned nowhere. | Named in `CONTRIBUTING.md`. |
| T12 | Low | README said eight known limitations; the release notes list nine. | Corrected. |
| T13 | Low | `TestTheConfirmationIsNotOnlyInTheBrowser` exercised the form handler's own duplicate check, not the shared gate ADR-033 describes. | A test calls `ActionRunner.perform` directly and fails when the shared gate is removed. |

## Gates

| Gate | Result |
|---|---|
| `make check` | pass — 689 passed, 42 deselected |
| `make test-ui` | pass — 42 passed |
| `make validate-content` | pass — 8 quests, 8 regions, 4 badges, 1 track, 0 warnings |
| `make verify-package` | pass — the exported archive installs, validates and builds on its own |
| Clean clone from a README-only reading | pass, twice, at `8df0ac5` (tooling lens), including `make serve` answering 200 |
| `make check` beside a running `make serve` | pass, three times (tooling lens) |
| Each fix reverted one at a time | every code fix and every rewritten test is caught: the attempt version, the import path, the byte ceiling, the exit-driven end of a run, the stray print, non-UTF-8 output, run-ID order, all-skipped, the secret scan decode and unreadable file, the load-time record checks, the registry cross-check, the schema refusal, the migrate rollback, the merge-in-progress finding, the Jira path, the service refusals, content discovery, `build`'s redaction and the schema error were each reverted and their test failed |
| CI on this branch | see the pull request |

The suite grew from 643 to 689. `make test-ui` is unchanged at 42.

## Verdict

**Round 10 does not close DH7.** It found one blocking and eight high findings.

The blocking one is the plainest statement yet of the pattern rounds 8 and 9 named. The
integrity check compared the review's version to the attempt's, and the review wrote the
content's; each half was right about the half its author was looking at, and the update
flow the guides promise was the case where they differ. The same shape runs through the
rest: the validator's working directory was applied for the contract's sake and put
participant code on the import path; the secret scan read every file it could decode; the
Jira validator checked the file it found rather than the file the quest asked for; and a
migration machinery built early "so the first real migration is not the moment to design
the safety" had no command that ran it.

The round-9 theme held where round 9 fixed it: the reviewer's findings reach the
participant, a second decision on one attempt is shown in order, and nothing but a
reviewer's approval reaches a verified state or verified XP.

Round 11 should run against the merge commit, with the same three lenses. Point it at:

- the update path again, now that `make migrate` exists: a real schema bump, a real
  upstream, and a participant who merges without reading the output;
- the validator child as rebuilt here — the byte ceiling, the exit-driven end of a run,
  and the bootstrap — with validators written for the occasion;
- C2: whether any sequence of actions, CLI or browser, can leave `generated/` describing
  a state that is no longer true while the service is serving it;
- the other seven quests read against the files they tell a participant to write, the
  way C1 was found;
- and the tests added this round, mutated the way this round mutated the older ones.
