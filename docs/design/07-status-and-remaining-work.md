# Part 7. Where we are, and the phase plan

This part is the project's plan. It says what the goal is, where the work stands, how every
phase of the remaining work runs, and which phases remain. It replaces the audit-status part
of versions 1.x.

**The rule this part exists to enforce: scope changes only at a phase gate.** Between gates
the current phase's scope is frozen. A new idea, from anyone, goes to
`docs/PARKING-LOT.md` and is decided at the next gate, not acted on.

## 7.1 The goal

Put the Golden Thread Quest in front of real participants and a reviewer, learn from what
they do, and grow the curriculum and the application in the order that learning says is
most valuable.

The first release is a **pilot**: a small number of participants, working locally, on the
quests that exist today, with the known limitations written down (Section 7.6). It is not a
finished curriculum and not a hardened product. Everything after the pilot is chosen at a
gate.

## 7.2 Where we are (2026-09-29)

**Current phase: Phase 2B, the pilot run. It starts when the program owner sends the invitation.** The hand-in was rehearsed at `v0.2.0` with two local clones on 2026-09-29 and passes along the path `PILOT.md` describes (`docs/pilot/PILOT-LOG.md`). The GitHub fork and pull request can only be tested by the first real hand-in. Gate 1 passed on 2026-09-29, when the
program owner decided to release to a pilot. Phase 1's checklist passed and DH7 is closed
(`docs/audits/phase-01-verify.md`). Phase 2A fixes the two parking-lot items the program
owner chose and builds the release. Phase 2B is the pilot itself.

### How we got here

**The application is built.** Stages 0 to 9 of `docs/IMPLEMENTATION-PLAN.md` were completed
and audited on 2026-09-16 and 2026-09-17. Everything Parts 1 to 6 describe exists, with
1382 tests under `make check` and 57 browser-driven tests under `make test-ui`. Eight quests
ship, one per region.

**The last twelve days went to one open criterion.** Stage 10, the release decision, has one
unchecked criterion: DH7, "the final audit reports no unresolved blocking or high findings."
Its closing rule required an independent round that finds no blocking or high finding at
all. Seventeen rounds ran, from 2026-09-17 to 2026-09-29. Every round found at least one,
every finding was fixed with a test, and the next round, pointed at new angles and at the new
fixes, found more.

**What that taught us.** The rounds found real defects: round 12 found that every browser
form was refused, and round 17 found that the page showed a proof path the gates did not
read. But the closing rule had no bound. A fresh adversarial reviewer can always find
something in 15,000 lines of code, so the loop could not end on its own, and each round
widened the scope a little: a broader secret scanner, integrity checks, timing tests. None
of those widenings was a decision the program owner made at a checkpoint, and no working
build was shown to the program owner along the way.

**What stops now.** Round 18 is not run. The per-round audit loop is replaced by the phase
method below. The audit records under `docs/audits/` stay as history.

| Round | Blocking | High | | Round | Blocking | High |
|---|---:|---:|---|---|---:|---:|
| 1 (final audit) | 3 | 4 | | 10 | 1 | 8 |
| 2 | 1 | 3 | | 11 | 0 | 3 |
| 3 | 1 | 2 | | 12 | 2 | 4 |
| 4 | 0 | 10 | | 13 | 2 | 3 |
| 5 | 0 | 9 | | 14 | 0 | 3 |
| 6 | 2 | 6 | | 15 | 0 | 3 |
| 7 | 1 | 8 | | 16 | 0 | 2 |
| 8 | 0 | 7 | | 17 | 1 | 5 |
| 9 | 0 | 8 | | | | |

*Each round's record is `docs/audits/round-NN-independent-audit.md`; rounds 1 to 3 are in
`stage-10-final-audit.md` and `stage-10-final-re-audit.md`. An outside review on 2026-09-17
(`external-review-2026-09-17.md`) called the engine a release candidate and the curriculum
too thin.*

## 7.3 How every phase runs

Every phase has the same five steps. What changes from phase to phase is only the scope.

1. **Plan, then freeze.** At the gate before the phase, this part records the phase's goal,
   its scope as a numbered list, what is out of scope, a *done-when* checklist of things that
   can be shown true or false, the demo, and a budget in working sessions. Once the program
   owner approves it, the scope does not change until the next gate.
2. **Build.** Only the numbered scope items. Work happens on feature branches and merges to
   `main` on the implementer's judgment, as `CLAUDE.md` rule 2 allows. An idea that is not
   in scope goes to `docs/PARKING-LOT.md` with one line saying why it might matter.
3. **Verify.** One independent review, in a fresh context, checks the done-when list and
   nothing else. A blocking or high finding *inside the scope* is fixed, and only that fix is
   re-checked. A finding outside the scope goes to the parking lot. **At most two verify
   cycles**; if the phase still fails, it stops and goes to the gate as it is.
4. **Demo.** The program owner runs the phase's result, following written steps, and sees
   it work.
5. **Gate.** The design document gets a new minor version (the rule is in
   `REGENERATING.md`), recording what was done, what was learned and what changed. The
   parking lot is triaged: each item is scheduled into a phase, left in the lot, or cut.
   Then the program owner chooses the next phase and approves its plan.

**Two stop rules** end a phase early and go straight to the gate:

- the phase has used half again its budget (for example, a third session on a two-session
  phase);
- a safety or data-loss problem turns up outside the phase's scope. It is reported, not
  fixed on the spot, so the program owner decides whether it outranks the plan.

## 7.4 The phases

Every piece of remaining work the project knows about is in one of these phases or in the
parking lot. Phase 1 is planned in full. Later phases are sketched, and each one is planned
in full at the gate before it, using what the earlier phases taught. Each item carries a
recommendation: **do**, **decide** (at that phase's gate, likely on pilot evidence), or
**cut** (recommended not to do in the foreseeable future).

### Phase 0: Reset and plan (this version)

- **Goal:** stop the audit loop and put the plan in one document the program owner can read.
- **Done when:** this part is merged; `docs/PARKING-LOT.md` exists; `CLAUDE.md` states the
  phase rule; `PLANNING-STATUS.md` points here.
- **Gate 0 (2026-09-29): passed.** The program owner approved Phase 1 as written and the
  closing-rule change in its item 2.

### Phase 1: Pilot release decision (done)

- **Goal:** decide on a fixed checklist whether the application as built goes to a pilot,
  and let the program owner see it working.
- **Budget:** two sessions.
- **Scope:**
  1. **Housekeeping.** Remove the stale round 17 worktrees under `.worktrees/`, their local
     branches and `backup/round-17-before-rewrite`. Delete the remote `chore/round-*` and
     `fix/r*` branches that are merged into `main`.
  2. **Replace DH7's closing rule** with the release checklist in item 3: DH7 closes when
     every item in it passes and one verify pass finds no blocking or high finding *within
     those flows*. Approved at Gate 0.
  3. **The release checklist**, run for real, not by test client:
     1. CI is green on `main`, every job.
     2. A true `git clone` from GitHub, then `make setup`, `make check`, `make setup-ui` and
        `make test-ui`, all pass.
     3. **Participant flow:** open the site with `make serve`, pick a quest, start it, build
        its evidence, run its validator, and submit it.
     4. **Reviewer flow:** open the submission, ask for changes with a finding; the
        participant fixes and resubmits; the reviewer approves; the passport shows verified
        completion and verified XP, while claimed progress stays visibly separate.
     5. **Maintainer flow:** add a sample quest as one Markdown file; after `make build` it
        appears in its region, the catalog, search and its tag page with no change to UI code.
     6. **Failure flow:** break a content file; the build names the file and field, and the
        last good site stays up.
  4. **A demo walkthrough**, `docs/guides/DEMO.md`: the checklist's flows 3 to 6 as numbered
     steps the program owner can follow in about fifteen minutes.
  5. **The release record.** `docs/audits/final-audit.md` gets the checklist results and a
     recommendation, expected to be `release-with-advisories`; Stage 10's boxes in
     `docs/IMPLEMENTATION-PLAN.md` are checked; `docs/RELEASE-NOTES.md` and the `README`
     status note say "pilot".
- **Out of scope:** round 18's targets; every item in Phases 3 to 7; any new hardening.
- **Done when:** items 1 to 5 are complete, every checklist item passes, and the verify pass
  finds no blocking or high finding within the checklist's flows.
- **Demo:** the program owner follows `docs/guides/DEMO.md`.
- **Result:** every checklist item passed. CI on `main` first failed on a start-up race,
  which pull request 18 fixed. The verify pass found three Low wording problems in the demo,
  all fixed. Five observations are in the parking lot. See `docs/audits/phase-01-verify.md`.
- **Gate 1 (2026-09-29): passed.** The program owner decided to release to a pilot of about
  two participants, after fixing the two parking-lot items about missing proof.

### Phase 2A: Pilot release (current)

- **Goal:** a tagged release that two participants can take up from a Slack message, with
  the two missing-proof gaps closed.
- **Budget:** one session.
- **Scope:**
  1. **Refuse a submission that is missing required proof.** A required file, folder or
     command record that the evidence page shows as *Not detected* or *Needs attention*
     (empty) blocks submission, and the refusal names each one. Validators stay advisory at
     submission, as they are today, and demonstrations cannot be detected, so they are not
     checked.
  2. **An unfilled `PROOF.md` fails the Base Camp check.** A proof document that is still
     the template, with headings and nothing under them, is a `fail`, not an advisory. The
     check still looks at what the document says, not whether files exist, as
     `docs/VALIDATOR-CONTRACT.md` asks.
  3. **The release.** Version 0.2.0, the README and release notes say "pilot", and a Git tag
     `v0.2.0` has a GitHub release whose notes link the pilot guide.
  4. **`docs/guides/PILOT.md`**, for participants. It covers what they need installed,
     forking and setup, the two pilot quests (Base Camp required, BA Ruins' transcript quest
     if there is time), how to hand in evidence, how to send feedback, and a warning that
     forks of a public repository are public, so the pilot uses fictional material only.
  5. **`docs/guides/PILOT-LEAD.md`**, for the program owner. It holds the Slack message
     ready to paste, how to review a participant's evidence from their fork, what feedback
     to collect, and when the pilot ends.
- **Out of scope:** the other three parking-lot items and everything in Phases 3 to 7.
- **Done when:** items 1 to 5 are complete, with tests for 1 and 2 that fail without the
  fix. `make check` and CI pass on `main`. A verify pass acting as a new participant follows
  `PILOT.md` from the release through a Base Camp submission, then follows `PILOT-LEAD.md`'s
  review steps, and finds no blocking or high finding.
- **Demo:** the program owner reads the Slack message and `PILOT.md`, then sends the message.
- **Result:** built and verified. The verify pass (`docs/audits/phase-02a-verify.md`) found two
  high findings in cycle 1: refusals were cut short, and reviewing from a clone always showed
  a false "evidence changed" warning. Both were fixed and passed in cycle 2. The fork and
  pull-request step on GitHub itself is untested.

### Phase 2B: Pilot run

- **Goal:** watch two participants and one reviewer use the application, and collect what
  confuses, blocks or delights them.
- **Budget:** calendar time. The program owner sets the end date in the Slack message, and
  two weeks is suggested.
- **Scope:** code changes only for a defect that stops a participant from continuing. Every
  other observation goes to the parking lot.
- **Output:** a pilot report that ranks what to change. It is the main input to Gate 2 and to
  choosing among Phases 3 to 7.

### Phase 3: Participant and reviewer experience

Known items, likely joined by pilot findings. The ones marked **do** were found while
using the application; the others wait for evidence.

| Item | Source | Recommendation |
|---|---|---|
| A degraded view for an attempt whose evidence folder is missing, instead of an unbuildable site | D12 | Do: one deleted folder breaks everything today |
| Reviewer-awarded badges: a badge-award record so they can be granted | Known limitation 4 | Do if the pilot uses badges |
| Role separation between participant and reviewer pages | D11 | Decide |
| Success notices after an action | D14 | Decide |
| Showing the quest version an attempt started on, not only the current one | Known limitation 10 | Decide |
| Quest-page section order | D15 | Decide |
| Deeper gamification than the quest framing implies | External review 9 | Decide, with the curriculum |

### Phase 4 onward: Curriculum

The outside review's main finding was that the curriculum is thin: eight quests, one per
region. `docs/CURRICULUM-BACKLOG.md` proposes 128: Base Camp 9, Jira Jungle 23, Trello
Islands 17, GitHub Caverns 18, Context Library 12, BA Ruins 13, Scrum Village 9, Playwright
Labyrinth 20, and 7 hidden challenges.

- **One region per phase**, in an order chosen at each gate. The recommended first is
  **Base Camp**, because every other region builds on its safety quests.
- Each curriculum phase includes the validators its quests need and a glossary content type
  if the region's quests need one (D1).
- A quest that writes to Jira, Trello or GitHub must meet the preview-and-confirm conditions
  in `docs/SECURITY-AND-PRIVACY.md` first. The first region with such quests carries that
  capability as its own scope item.
- **Recommendation:** decide how many regions to build after the pilot. The full 128 is a
  plan, not a promise.

### Phase 5: Engineering hygiene

| Item | Source | Recommendation |
|---|---|---|
| A scheduled CI job that runs a true `git clone` and setup | Known limitation 9 | Do; Phase 1 runs it once by hand |
| Coverage reporting | D2 | Decide |
| A fixture that holds all eight quest states at once | D8 | Decide |
| A per-test timeout for the scaling tests | D16 | Decide |
| Splitting the largest modules, with complexity limits | External review 7 | Decide, only if a later phase is slowed by them |

### Phase 6: Security hardening

Release one's controls are documented in Part 5. These go further. They matter when
validators or quests come from authors the program does not review, which is not the case
today.

| Item | Source | Recommendation |
|---|---|---|
| Container or seccomp isolation for validators | D9 | Cut until third-party validators exist |
| Reaching a validator grandchild that starts its own session | Round 12 E9 | Cut, same reason; it depends on D9 |
| Wider secret-scanner coverage | D10 | Decide, only on a real false negative from the pilot |
| Scanning binary and compressed files | Known limitation 8 | Cut; the participant's confirmation in `PROOF.md` covers it |
| Type-tagged evidence hash chunks | D13 | Cut; it re-flags every approved attempt and closes a gap that hides nothing |

### Phase 7: New capabilities

Named in the specification and not built. Each is a product decision, not a fix.

| Item | Source | Recommendation |
|---|---|---|
| Live Environment Health checks through the local service | D7 | Decide after the pilot |
| A central, opt-in scoreboard | Product brief | Decide after the pilot |
| AI-assisted advisory evaluation of evidence | Product brief | Decide after the pilot |
| External-write previews | Product brief | Build with the first curriculum region that needs them |

## 7.5 Where things are recorded

| What | Where |
|---|---|
| The plan: goal, current phase, phase sketches | This part |
| Ideas that arrived mid-phase | `docs/PARKING-LOT.md` |
| What each version of the plan changed and learned | `docs/design/CHANGELOG.md` |
| The original stages and the deferred-work register (D1 to D16) | `docs/IMPLEMENTATION-PLAN.md` |
| Release criteria | `docs/ACCEPTANCE-CRITERIA.md` |
| Verify passes and audits | `docs/audits/` |

## 7.6 Known limitations of release one

Deliberate boundaries, stated for participants in `docs/RELEASE-NOTES.md`. The phase that
would lift each one is in brackets.

1. Recording a reviewer decision needs the local service or the CLI, because it writes files.
2. Reviewer identity is conventional, not cryptographic (ADR-030). [Phase 3, D11]
3. Environment Health shows build-time facts, not live ones. [Phase 7, D7]
4. Reviewer-awarded badges cannot yet be awarded; they show as pending. [Phase 3]
5. Validator isolation is policy plus process boundaries. [Phase 6, D9]
6. Catalog filtering needs JavaScript; region and tag pages work without it.
7. No coverage reporting, no glossary content type. [Phases 5 and 4, D2 and D1]
8. Binary and compressed files are not scanned for secrets. [Phase 6]
9. Clean-clone installation is tested in CI from a `git archive` export, not a real clone.
   [Phase 1 once by hand, Phase 5 on a schedule]
10. Earlier quest versions are not kept; pages show the current version's criteria.
    [Phase 3]
11. A validator grandchild that starts its own session outlives the timeout. [Phase 6]
12. Two builds are byte-identical only when `SOURCE_DATE_EPOCH` is set.
