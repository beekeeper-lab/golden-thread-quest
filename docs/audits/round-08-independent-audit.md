# Release Audit — Round 8

Status: **in progress.** Three lenses are running against the merge commit. Their findings, the
verification pass over them, the gates and the verdict follow.

Commit under audit: `b0667c0` on `main`, the merge of `chore/round-07-audit`. The tree here is
what a clone of `main` now gets.
Range of newest work: `31a74cb..b0667c0`.
Predecessor: `docs/audits/round-07-independent-audit.md`.

## Why this round exists

`docs/ACCEPTANCE-CRITERIA.md` leaves **DH7** open. Seven rounds have run and each one found
something. The criterion closes on a round that reports no unresolved blocking or high
findings, which is a round that finds nothing, not a round whose findings are all fixed.

## Method

Three lenses, each given the repository paths and the commit range and nothing else: no summary
of what the author believed, no sight of each other's findings, and no access to
`docs/audits/`, which would have told them what earlier rounds concluded.

| Lens | Scope |
|---|---|
| Curriculum | The eight quests as curriculum, regions, badges, tracks, the participant journey walked end to end, the validator fixtures, and the accessibility of what is actually rendered |
| Engine | Code correctness, concurrency, the state model, the local service, the validator subsystem, and the architecture rules in `CLAUDE.md` |
| Documentation | Traceability, acceptance criteria, ADR accuracy, cross-document consistency, and clean-clone reproducibility from the remote at this branch's head |

Round 7 named two themes to carry forward: a mechanism correct in the case it was written for
and one step short everywhere else, and a check that cannot see what it is judging. The lenses
are pointed at the four request-path mechanisms round 7 added, the rebuild advisory now carried
into the page, `Workspace.attempt_files` and the three validators, and the modules no lens has
reached — `view_models`, `recommend`, `markdown_structure`, `update`, `migrations` — plus the
accessibility the browser tests do not assert.

Every finding requires file:line or a command and its output. A claimed defect that could not be
triggered is recorded as unverified rather than as a finding. Findings returned by a lens are
re-verified here before they are accepted; a lens is a source, not a verdict.

## Lens findings

Pending.

## Gates

Pending.

## Verdict

Pending.
