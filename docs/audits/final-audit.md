# Final Audit

`CLAUDE.md` and `docs/IMPLEMENTATION-PLAN.md` name this file. It is an index rather than a
copy, because the release audit ran twice and both rounds matter — the second exists only
because the first found three blocking defects.

| Round | Commit | Verdict | Record |
|---|---|---|---|
| First | `1418b78` | **do-not-release** — 3 blocking, 4 high, 6 medium, 4 low | `stage-10-final-audit.md` |
| Re-audit | `128617e` | **do-not-release** — 1 blocking, 3 high, 9 medium, 4 low | `stage-10-final-re-audit.md` |
| Second re-audit | pending | pending | — |

## What the two rounds found, in one sentence each

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

- [x] No unresolved blocking or high findings — all closed, pending confirmation by re-audit.
- [x] Acceptance criteria carry stable IDs; 47 of 48 are ticked and the one that is not
      (`DH1`, clean-clone setup) is named in `docs/TRACEABILITY.md`.
- [x] `docs/IMPLEMENTATION-DETAILS.md` describes what exists, including six divergences from
      the plan and why each was made.
- [ ] Clean-clone reproduction — not performed automatically; needs a fresh checkout.
- [x] Pilot limitations are visible to participants and reviewers, in the guides and in
      `docs/RELEASE-NOTES.md`.

**The release decision is not made in this file.** It is pending the second re-audit.
