# Release Audit — Round 6

Status: **in progress.** Three lenses are running against the merge commit. Their findings,
the verification pass over them, the gates and the verdict follow.

Commit under audit: `ad629a2` on `main`, the merge of `chore/round-04-completion`. This is the
first round to run against a merge commit, which is what round 5 said round 6 should do: the
tree here is what a clone of `main` now gets.
Range of newest work: `ff0c63d..ad629a2`.
Predecessor: `docs/audits/round-05-independent-audit.md`.

## Why this round exists

`docs/ACCEPTANCE-CRITERIA.md` leaves **DH7** open. Five rounds have run and each one found
something. The criterion closes on a round that reports no unresolved blocking or high
findings, which is a round that finds nothing, not a round whose findings are all fixed.

## Method

Three lenses, each given the repository paths and the commit range and nothing else: no
summary of what the author believed, no sight of each other's findings, and no access to
`docs/audits/`, which would have told them what earlier rounds concluded.

| Lens | Scope |
|---|---|
| Curriculum | The eight quests as curriculum, regions, badges, tracks, the participant journey walked end to end, and what the built pages actually say |
| Engine | Code correctness, the state model, the action layer, the local service, the validator subsystem, and the architecture rules in `CLAUDE.md` |
| Documentation | Traceability, acceptance criteria, ADR accuracy, cross-document consistency, and clean-clone reproducibility from `main` |

The engine lens is pointed at the four mechanisms round 5 introduced or left open, because its
own tests are the only ones that have ever looked at them:

- the build lock, new enforcement in the path of every publish;
- the service port file, new state written outside the participant's directory;
- the unlocked fall-through in `ProgressStore.exclusive`, the first path in this application
  that deliberately proceeds without a guarantee it asked for;
- the `Content-Length` stall, which round 5 recorded as open rather than fixing.

It also carries one instruction earned the hard way: this package is installed in editable
mode, so a scratch copy still imports `quest_app` from the original repository under pytest.
Round 5's first mutation run reported three false negatives for exactly that reason. The
probe must prove, with `inspect.getsource`, that the mutation is in the module the test
imports.

Every finding requires file:line or a command and its output. A claimed defect that could not
be triggered is recorded as unverified rather than as a finding. Findings returned by a lens
are re-verified here before they are accepted; a lens is a source, not a verdict.
