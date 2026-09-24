# Part 7. Status and remaining work

This part says what is finished, what is open, and what is deliberately left for later. It
describes `main` at commit `16a0b03` (the merge of pull request 8, round 11), with the round
12 findings taken from `docs/audits/round-12-independent-audit.md` on the branch
`chore/round-12-audit` at `7a8cf7b`.

## 7.1 How the work was staged

`docs/IMPLEMENTATION-PLAN.md` divides the build into eleven stages. Each ends with an audit
by a fresh reviewer, recorded under `docs/audits/`, and a stage is checked off only when its
audit passes after fixes.

| Stage | Scope | State |
|---|---|---|
| 0 | Planning and feasibility audit | Complete |
| 1 | Repository and engineering foundation | Complete |
| 2 | Content contracts and loading | Complete |
| 3 | Deterministic site generation | Complete |
| 4 | Participant state and loopback service | Complete |
| 5 | Evidence workspaces and validator framework | Complete |
| 6 | Participant UI and accessibility | Complete |
| 7 | Submission and reviewer integrity | Complete |
| 8 | Fork updates, versioning and migrations | Complete |
| 9 | Documentation, hardening and release candidate | Complete |
| 10 | Final independent audit and release decision | **Open** |

## 7.2 Why Stage 10 is still open: DH7

Stage 10 closes when every release acceptance criterion in `docs/ACCEPTANCE-CRITERIA.md` is
met. Forty-seven are checked. One is open:

> **DH7**: the final audit reports no unresolved blocking or high findings.

The project reads DH7 strictly: it closes only on an audit round that **finds nothing**
blocking or high. Fixing a round's findings does not close it, because the fixes are
themselves unaudited; the next round runs against the merge commit that contains them.

**Method of a round.** Three independent review **lenses**, each in its own worktree at the
commit under audit with `docs/audits/` removed, each given only paths, a commit and areas to
probe, none shown the author's beliefs or another lens's findings. The lenses cover the
curriculum followed literally, the engine, and tooling, tests and documentation. Every
finding is verified by reproduction or by reading the cited code before it is accepted.

## 7.3 Audit history

| Round | Commit | Blocking | High | Record |
|---|---|---:|---:|---|
| 1 (final audit) | `1418b78` | 3 | 4 | `stage-10-final-audit.md` |
| 2 (re-audit) | `128617e` | 1 | 3 | `stage-10-final-re-audit.md` |
| 3 (second re-audit) | `aafce28` | 1 | 2 | `stage-10-final-re-audit.md` |
| External review | `a69a8b8` | n/a | n/a | `external-review-2026-09-17.md`: engine a release candidate, curriculum too thin |
| 4 | `207a7b3` | 0 | 10 | `round-04-independent-audit.md` |
| 5 | `ff0c63d` | 0 | 9 | `round-05-independent-audit.md` |
| 6 | `ad629a2` | 2 | 6 | `round-06-independent-audit.md` |
| 7 | `31a74cb` | 1 | 8 | `round-07-independent-audit.md` |
| 8 | `b0667c0` | 0 | 7 | `round-08-independent-audit.md` |
| 9 | `5248500` | 0 | 8 | `round-09-independent-audit.md` |
| 10 | `8df0ac5` | 1 | 8 | `round-10-independent-audit.md` |
| 11 | `ea36037` | 0 | 3 | `round-11-independent-audit.md` |
| 12 | `16a0b03` | 2 | 4 | `round-12-independent-audit.md` (on `chore/round-12-audit`) |

Every accepted blocking and high finding from rounds 1 to 11 is fixed on `main`, each code
fix with a test that fails without it. The round records say which lower findings were
deferred or stated as limitations instead. The pattern the audits name is
consistent: defects live in states no fixture occupied (no participant yet, a refused action,
a second process, a hostile file, a real browser rather than a test client).

## 7.4 Round 12: open findings

Round 12 audited `16a0b03` and found two blocking and four high findings, so it does not close
DH7. **None of the fixes is merged.** They are in progress on four branches: `fix/r12-web`,
`fix/r12-io`, `fix/r12-integrity` and `fix/r12-runner`. Until they merge and a further round
runs against the merge commit, the statements below describe the code as it is.

| ID | Severity | Finding |
|---|---|---|
| C1 | Blocking | Every browser action form fails: pages send `Referrer-Policy: no-referrer`, Chromium then sends `Origin: null`, and the origin check refuses it. Only the CLI changes state |
| E1 | Blocking | Three writes can follow a symbolic link out of `participant/`: the activity line, validation results in a linked `validation/` directory, and the review archive. A FIFO `ACTIVITY.md` hangs an action while it holds both locks |
| C2 | High | CLI tests with `--participant-root` still build into the repository's own `generated/`, so `make check` replaces a participant's site with fixture data until the next build |
| E2 | High | Validation result files are read without a size or file-type bound; a FIFO hangs `validate`, `build` and the service |
| E3 | High | `review*.yaml` files are globbed and parsed without a bound or error handling; a stray bad `reviewer-notes.yaml` passes `validate` and crashes `build` |
| E5 | High | A legitimate `locally_validated` attempt becomes a load error after an update that adds a validator to the quest, and every action is then refused |
| C3 | Medium | A link leading outside the evidence package makes the review page say a secret was found |
| C4 | Medium | After a pass, local validation and a failing re-run, the evidence page shows "passed" beside "Last run: fail" with nothing connecting them |
| C5 | Medium | When a newer quest version renames a proof path, the review checklist marks the old item "Not detected" with no note that the version changed |
| E4 | Medium | A hand-edited `state: submitted` with no `submission.yaml` loads and can be approved, skipping the secret-scan gate |
| E6 | Medium | The runner caps the output excerpt and check count but not other check fields, so an oversize field discards the whole run |
| E7 | Medium | Redaction runs after truncation, so a token cut at the boundary is stored in clear |
| E8 | Medium | Evidence files have no size ceiling; a very large log makes every build slow while it holds the locks |
| T1 | Medium | The documentation command test covers five documents and skips four guides |
| E9 | Low | A validator grandchild that starts its own session survives cleanup |
| E10 | Low | `make migrate` rewrites `progress.yaml` without an activity line |
| E11 | Low | A validator that finishes but leaves a non-daemon thread running is reported `interrupted` |
| T2 | Low | `PYTHON ?= python3` in the Makefile is never used |

**What this means for a reader of this document.** Parts 2 to 5 describe the design and the
code at `16a0b03`. Where a round 12 finding shows the code falling short of the design, the
relevant part says so next to the claim.

## 7.5 Known limitations

These are deliberate and documented in `docs/RELEASE-NOTES.md`. They are not defects to be
fixed before release; they are boundaries of release one.

1. Recording a reviewer decision needs the application (the local service or the CLI),
   because it writes files. Reading evidence works from generated pages alone.
2. Reviewer provenance is conventional, not cryptographic (ADR-030).
3. Environment Health reports build-time facts, not live ones (D7).
4. Reviewer-awarded badges cannot be awarded: there is no badge-award record type, so they
   show as pending.
5. Validator isolation is policy plus process boundaries, not a container or seccomp (D9).
6. Catalog filtering needs JavaScript; region and tag pages are the scripting-free routes.
7. No coverage reporting (D2) and no glossary content type (D1).
8. A screenshot is not scanned for secrets.
9. Clean-clone installation is tested in CI from a `git archive` export, one step short of a
   real `git clone`; a real clone was run by hand in round 4.
10. Earlier quest versions are not kept. An attempt records its version, but pages show the
    current version's criteria; Git history holds the earlier text.
11. Two builds are byte-identical only when `SOURCE_DATE_EPOCH` is set.

## 7.6 Deferred work

From the deferred-work register in `docs/IMPLEMENTATION-PLAN.md`. Items D3 to D6 were
delivered in their stages.

| ID | Work | Why deferred |
|---|---|---|
| D1 | Glossary content type | No schema, sample or screen needs it yet |
| D2 | Coverage reporting | Half-configured is worse than absent |
| D7 | Live Environment Health checks through the service | A generated page cannot inspect the machine when read |
| D8 | A fixture exercising all eight quest states at once | Tests reach the other states by mutation today |
| D9 | Container or seccomp isolation for validators | Release one is policy plus process boundaries |
| D10 | Wider secret-scanner coverage (distant assignments, bare keys, base64, webhooks, personal data) | Widening without a corpus risks false positives that teach people to route around the gate |
| D11 | Role separation between participant and reviewer | The reviewer page is in the primary navigation; ADR-030 already states provenance is conventional |
| D12 | A degraded view for an attempt whose evidence directory is missing | Today one deleted folder makes the site unbuildable until `progress.yaml` is edited |

**Curriculum.** Release one ships eight quests, one per region, four badges and one track.
`docs/CURRICULUM-BACKLOG.md` lists about 128 proposed quests across the eight regions plus
seven optional "trap" challenges, from repository safety through Jira, Trello and GitHub
synchronization to Playwright test repair. The backlog is a plan, not a promise, and any
quest that performs an external write must first meet the preview-and-confirm conditions in
`docs/SECURITY-AND-PRIVACY.md`. Several future-facing application capabilities are also named
in the specification and not built: a central opt-in scoreboard, AI-assisted advisory
evaluation, and external-write previews.

## 7.7 What done looks like

Stage 10 completes, and the project can make its release decision, when:

1. the round 12 fixes are merged, each with a test that fails without it;
2. a round runs against that merge commit and finds no blocking or high finding;
3. DH7 is checked, `docs/audits/final-audit.md` records the decision (`release`,
   `release-with-advisories` or `do-not-release`), and the Stage 10 boxes in
   `docs/IMPLEMENTATION-PLAN.md` are checked.

This document then gets a minor version for the new status (see `REGENERATING.md`).
