# Release Audit — Round 7

Status: **in progress.** Three lenses are running against the merge commit. Their findings, the
verification pass over them, the gates and the verdict follow.

Commit under audit: `31a74cb` on `main`, the merge of `chore/round-06-audit`. The tree here is
what a clone of `main` now gets.
Range of newest work: `ad629a2..31a74cb`.
Predecessor: `docs/audits/round-06-independent-audit.md`.

## Why this round exists

`docs/ACCEPTANCE-CRITERIA.md` leaves **DH7** open. Six rounds have run and each one found
something. The criterion closes on a round that reports no unresolved blocking or high
findings, which is a round that finds nothing, not a round whose findings are all fixed.

## Method

Three lenses, each given the repository paths and the commit range and nothing else: no summary
of what the author believed, no sight of each other's findings, and no access to
`docs/audits/`, which would have told them what earlier rounds concluded.

| Lens | Scope |
|---|---|
| Curriculum | The eight quests as curriculum, regions, badges, tracks, the participant journey walked end to end, and what the built pages actually say |
| Engine | Code correctness, concurrency, the state model, the local service, the validator subsystem, and the architecture rules in `CLAUDE.md` |
| Documentation | Traceability, acceptance criteria, ADR accuracy, cross-document consistency, and clean-clone reproducibility from the remote |

The engine lens is pointed at what round 6 built or left unreached: the service port directory,
the refusal path that now closes connections, the rebuild advisory, and the validator
subsystem, action allowlist, `content_loader`, `view_models` and the evidence and review paths,
which round 6 did not reach. It also carries round 5's lesson about the editable install: a
mutation experiment must prove with `inspect.getsource` that the mutated module is the one the
test imports.

Every finding requires file:line or a command and its output. A claimed defect that could not be
triggered is recorded as unverified rather than as a finding. Findings returned by a lens are
re-verified here before they are accepted; a lens is a source, not a verdict.
