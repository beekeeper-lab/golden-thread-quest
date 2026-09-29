# Final Audit

## Release decision: `release-with-advisories`, to a pilot (2026-09-29)

**Decided by the program owner at Gate 1:** release to a pilot of about two participants,
after fixing the two parking-lot items about missing proof (Phase 2A, `docs/design/07-status-and-remaining-work.md`).
The release is version 0.2.0, tagged `v0.2.0`.

The recommendation it accepted was release with advisories, on the basis below.

The basis is Phase 1's release checklist, run for real and checked by an independent verify
pass (`phase-01-verify.md`). CI is green on `main`. A true `git clone` sets up and passes
every gate. The participant, reviewer, maintainer and failure flows all work in a real
browser. No blocking or high finding was found within those flows, so DH7 closes under the
rule set at Gate 0. The seventeen earlier rounds are indexed below.

**The advisories a pilot must know:**

- The known limitations in `docs/RELEASE-NOTES.md`.
- The five Phase 1 observations in `docs/PARKING-LOT.md`. The one most likely to matter:
  submission is accepted while required proof is missing, so the reviewer is the check.
- One quest per region. The pilot is a trial of the engine and the workflow, not of a full
  curriculum.
- The installed Cowork app, named in the README as a target surface, has not been tried.
  Phase 1 ran on Linux with a terminal and a browser.

**Checked for this recommendation:** the tracked tree has no secret (the repository scan,
run by `make check` in the clean clone) and no machine-specific path. The only home-directory
strings are four deliberate `PWD=` fixtures in `tests/unit/test_secret_patterns.py`.

## Earlier rounds

`CLAUDE.md` and `docs/IMPLEMENTATION-PLAN.md` name this file. It is an index rather than a
copy, because the release audit has run three times and an external reviewer has since
looked at the result. Every round matters: each one exists because the round before it found
something the suite did not.

| Round | Commit | Verdict | Record |
|---|---|---|---|
| First | `1418b78` | **do-not-release** — 3 blocking, 4 high, 6 medium, 4 low | `stage-10-final-audit.md` |
| Re-audit | `128617e` | **do-not-release** — 1 blocking, 3 high, 9 medium, 4 low | `stage-10-final-re-audit.md` |
| Second re-audit | `aafce28` | **do-not-release** — 1 blocking, 2 high, 2 medium | `stage-10-final-re-audit.md` |
| External review | `a69a8b8` | **not ready for participant release** — curriculum skeletal, 1 visible defect | `external-review-2026-09-17.md` |
| Rounds 4 to 17 | `207a7b3` to `bc190e9` | each found at least one blocking or high finding, all fixed | `round-04-independent-audit.md` to `round-17-independent-audit.md`; summarized in Part 7, Section 7.2 of the system design |
| Phase 1 verify pass | `edbede9` | no blocking or high finding within the release checklist's flows | `phase-01-verify.md` |

## What each round found, in one sentence

**Round one:** three blocking defects sat on the primary path — a new participant could not
create their progress file, no action in the generated UI was ever enabled, and the reviewer
queue linked to pages that were never generated — and the suite was green because every
fixture began from a pre-populated participant directory with nothing awaiting review.

**Round two:** the blocking three were genuinely fixed, and the audit then found that a
*refused* action was invisible — the secret gate refused to mark evidence ready and the page
the participant landed on still said the scan had found nothing — and that the per-validator
environment allowlist did not work in either direction.

## The pattern

Both rounds found the same class of defect: **something that only happens in a state no
fixture occupied.** No participant. Nothing awaiting review. An action that was refused. A
second validator in the same session. Each was invisible to a suite that only ever exercised
the state the fixtures were written in.

The corrective, recorded here because it is the most transferable thing this project
produced: fixtures should start from nothing, and from every state the product defines, not
from one healthy example.

## Release gate

- [x] No unresolved blocking or high findings: DH7 closed by the Phase 1 verify pass.
- [x] Acceptance criteria carry stable IDs, and all 48 are ticked.
- [x] `docs/IMPLEMENTATION-DETAILS.md` describes what exists.
- [x] Clean-clone reproduction: a true `git clone`, `make setup`, `make check`, `make setup-ui`
      and `make test-ui` on 2026-09-29 (`phase-01-verify.md`, item 3.2).
- [x] Pilot limitations are visible to participants and reviewers, in the guides and in
      `docs/RELEASE-NOTES.md`.

**The release decision was made at Gate 1** by the program owner: `release-with-advisories`,
to a pilot. It is recorded at the top of this file and in Part 7 of the system design.
