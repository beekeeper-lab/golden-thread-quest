# System Design Changelog

The version rule is in `REGENERATING.md`: major for a restructure, minor for new content or a
phase gate, patch for corrections.

## 2.2.0 (2026-09-29)

Gate 1. Describes `main` at `be2b766`, plus Phase 2A.

- **Gate 1 passed.** The program owner released to a pilot (`release-with-advisories`) of
  about two participants, and chose the two missing-proof items from the parking lot. The
  other Phase 1 observations stay in the lot until the pilot report, and round 17's
  pointers were cut, because Phase 1's browser flows covered them.
- **What we learned.** The demo turned two "works as specified" behaviours into product
  decisions, which is what a gate is for. Deciding them took one message, and building them
  took part of a session.
- Part 7 replaces the Phase 2 sketch with Phase 2A (pilot release, frozen scope) and
  Phase 2B (the pilot run).

## 2.1.0 (2026-09-29)

Gate 0, and Phase 1's result. Describes `main` at `4ad5368`.

- **Gate 0 passed.** The program owner approved Phase 1 as written and the new closing rule
  for DH7.
- **Phase 1 is built and verified.** Every release-checklist item passed; the verify pass
  found no blocking or high finding within its flows, so DH7 is closed. The recommendation is
  `release-with-advisories`, and the decision is taken at Gate 1 after the demo.
- **What we learned.** Running the flows in a real browser was quick and found things the
  test suite does not frame as defects: submission accepts missing proof, and a check can
  pass on an empty package. Both are in the parking lot as product questions. A merged pull
  request can still turn `main` red on a timing race, which is why CI on `main` is a
  checklist item rather than an assumption.
- Part 7 carries the current phase and Phase 1's result.

## 2.0.0 (2026-09-29)

Describes `main` at `a837e7a`. A major version because Part 7 is restructured: it was the
audit status and is now the project plan.

- **What changed and why.** Seventeen audit rounds ran between 2026-09-17 and 2026-09-29
  under a closing rule with no bound, and each widened the scope a little without a decision
  at a checkpoint. The program owner asked for a strict plan with scope changes only between
  phases. Round 18 is not run.
- Part 7 now states the goal (a pilot, then growth chosen from what it teaches), where the
  work stands, the five steps every phase follows (plan and freeze, build, one verify pass,
  demo, gate), two stop rules, and Phases 0 to 7 with a recommendation on each known item.
- Part 7 drops round 12's findings-and-fixes table and the long form of the audit history;
  both remain in `docs/audits/`.
- `docs/PARKING-LOT.md` is new: ideas that arrive mid-phase wait there for the next gate.
- The glossary adds *gate*, *parking lot*, *phase* and *verify pass*, and updates *DH7* and
  *round*.
- **Gate 0 is open.** The program owner approves Phase 1's plan, including replacing DH7's
  closing rule with Phase 1's release checklist, before Phase 1 starts.

## 1.3.0 (2026-09-29)

Describes `main` at `bc190e9` (round 16's merge commit), amended by the round 17 fixes landing
in this pull request. DH7 is still open under the closing rule set on 2026-09-28; round 18
runs against round 17's merge commit.

- Part 7 carries round 17's status, the new closing rule, rounds 16 and 17 in the audit
  history, and deferred items D13 to D16.
- The security part describes round 17's scanner, the approval re-scan, the four scan-finding
  kinds and the proof-path rule.
- Corrected the ADR count to forty-three and added ADR-043 to Part 6; review archives are
  named `review-<timestamp>-<6 hex>.yaml` everywhere (round 17 D4).

## 1.2.0 (2026-09-28)

Describes `main` at `95b173e` (round 15's merge commit), amended by the round 16
integrity-lens fixes landing in this pull request. DH7 is still open; round 16 is in
progress against `95b173e` (`PLANNING-STATUS.md`).

- Brought the security part's secret-scanner description up to date past this document's
  round 12 baseline: the GitLab and Trello patterns and the Basic/token-scheme
  `Authorization` header (round 15 E2), the pagination exemption and PGP block-marker fix
  (round 15 E12), and the ReDoS bound on the JWT and `basic-auth-url` patterns (round 15 E5).
- Documented the participant-root refusal for a configured root that is, is inside, or
  contains a program-owned folder (ADR-042 amended round 15 E13), and its case-folded
  comparison (round 16 S1).
- Documented that both the content and evidence hashes normalize a file's bytes only when it
  decodes as UTF-8, and its name always by NFC, across a Windows/Linux/macOS checkout
  (ADR-031 amended round 15 E4/S1, narrowed round 16 E10).
- Documented the review archive's random-suffixed name, which keeps two decisions recorded in
  the same second from overwriting each other's archive (round 16 S2).
- Noted where DH7 stands: rounds 13 through 15 are in the audit history table (Part 7,
  Section 7.3) with their commit and finding counts; round 16 is in progress. This revision
  does not extend Part 7 Section 7.4's round-12-style findings-and-fixes table past round 12
  — that is deferred to a future regeneration.
- Rendered as `artifacts/html/design/golden-thread-system-design-v1.2.0.html` and
  `artifacts/pdf/design/golden-thread-system-design-v1.2.0.pdf`.

## 1.1.0 (2026-09-25)

Describes `main` at `0018e2d`, the merge of pull request 10 (round 12). Round 12's fixes are
now on `main`; DH7 is still open, pending round 13 against this commit.

- Fixed the code/specification disagreements v1.0.0 recorded as open round 12 findings:
  browser action forms now work (`Referrer-Policy: same-origin`, round 12 C1); every
  participant write goes through `safe_io`'s no-follow, non-blocking write path (ADR-042,
  round 12 E1); validation results and review records are read bounded through one shared
  definition (round 12 E2, E3); a `submitted` attempt now needs a readable submission record
  (round 12 E4); a `locally_validated` attempt on an older quest version warns instead of
  erroring when the update added a validator (ADR-017 amended, round 12 E5); evidence hashing
  streams instead of holding files in memory, and evidence files have a 2 MB scan ceiling
  (round 12 E8); the runner normalizes check fields against their schema and redacts before
  truncating (round 12 E6, E7); a validator that finishes but leaves a non-daemon thread
  running is no longer reported `interrupted` (round 12 E11); `make migrate` now writes an
  activity line (round 12 E10); `GTQ_GENERATED_ROOT` and `GTQ_LOCAL_DATA_ROOT` join
  `GTQ_PARTICIPANT_ROOT` as configuration, with a test-suite session guard as backstop
  (round 12 C2).
- Updated the diagrams these changes touch: the validator-run activity diagram (a check
  that fails schema conformance is replaced and forces `environment_failure`; a validator
  whose result channel closes while a leftover thread holds the process is not `interrupted`),
  the review-decision activity diagram (a missing submission record refuses the decision),
  and the browser-action sequence diagram and the security part's control tables (the fixed
  referrer policy and the write path).
- Updated Part 7's audit history, round 12's open-work list (now a findings-and-fixes table),
  the known limitations (E9, the validator grandchild that starts its own session, is now
  known limitation 11), and the test counts (830 under `make check`, 45 browser-driven).
- Rendered as `artifacts/html/design/golden-thread-system-design-v1.1.0.html` and
  `artifacts/pdf/design/golden-thread-system-design-v1.1.0.pdf`.

## 1.0.0 (2026-09-24)

First version. Describes `main` at `16a0b03` and the round 12 findings recorded on
`chore/round-12-audit` at `7a8cf7b`, whose fixes are not merged.

- Eight parts: purpose and users, architecture, data and state, activity flows, security,
  decisions, status and remaining work, glossary.
- Twelve diagrams drawn from the code: system context, components, repository folders by
  owner, record relationships, the attempt state machine, six activity flows and one
  sequence diagram.
- Rendered as `artifacts/html/design/golden-thread-system-design-v1.0.0.html` and
  `artifacts/pdf/design/golden-thread-system-design-v1.0.0.pdf`.
