# System Design Changelog

The version rule is in `REGENERATING.md`: major for a restructure, minor for new content or a
new audit round's status, patch for corrections.

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
