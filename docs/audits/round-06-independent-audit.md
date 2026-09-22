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

## Lens findings

### Curriculum

| # | Finding | Severity | Verification | Disposition |
|---|---|---|---|---|
| CUR-1 | `content/quests/base-camp/repository-safety.md` criterion 6 requires that rerunning the demonstrated workflow creates no duplicate of the simulated external item. The only evidence of it, `recovery-demonstration`, sat under `proof.optional`, and the registered validator checks ignore rules, `PROOF.md` completeness and secrets, not rerun behaviour. A reviewer had nothing required to check the criterion against. | High | Confirmed in the front matter and on the rendered quest page, where the criterion appears under "How this is judged" and its only evidence under "Optional evidence" | **Fixed.** A required `rerun-record` command-record, on the pattern every sibling synchronization quest has used since it was written. |
| CUR-2 | `content/quests/ba-ruins/ingest-transcript.md` criterion 7 requires that re-ingesting the same transcript produces an identical source record and duplicates no utterance. No proof item addressed it, required or optional, and the required-evidence prose did not mention it either. | High | Confirmed: the `proof` block holds four required and one optional item, none about re-ingestion | **Fixed** the same way, and the required-evidence prose now names it. |
| CUR-3 | `content/regions/jira-jungle.yaml` offered work "assigned and queried". The shipped quest is scoped to work assigned to the authenticated user; `jira-query-stories`, "run a configurable saved query with pagination", is a backlog item. | Medium | Confirmed against the quest's criteria and `docs/CURRICULUM-BACKLOG.md`. This reviewer wrote the phrase in round 5 while correcting the same file's other two outcomes, and judged "queried" defensible because criterion 2 documents the query used. It is not: what it documents is which query the quest runs, not the participant's ability to run their own | **Fixed.** |
| CUR-4 | `content/regions/github-caverns.yaml` offered to "preserve repository conventions and human review authority". The region's only quest is read-only issue synchronization and never mentions conventions. | Medium | Confirmed: `grep -i convention` over the quest returns nothing. Round 5 corrected this file's first outcome and left this one | **Fixed.** It now describes what the quest does: report what could not be read, and what disappeared between runs, instead of dropping it silently. |

Raised as unverified by the lens, and not accepted as findings: that `context-scout` is awarded
for a Base Camp quest despite its name, and that `jira-jungle`'s "records that it did not
write" has no field named for it. Both are worth a look and neither is a defect.

**Version handling.** Changing proof rules increments the quest version, which
`docs/CONTENT-MODEL.md` requires, so both quests are at version 2 and the fixture attempt and
its review record moved with them. That exposed a test of its own: the test that proves
editing a verified quest warns rather than failing the build mutated the literal string
`version: 1`, so on the day the quest reached version 2 it mutated nothing and passed on
warnings the fixture already carried. It now bumps from whatever version the quest is on.

**What the lens confirmed.** Prerequisites form a clean directed graph from the one unlocked
start, every quest is reachable, no cycles and no orphans. XP sums to 210 and matches the
rendered total. Level and XP pairs agree across all eight quests. The track's bookend minimums
are satisfied exactly. Badge criteria resolve against what `progress_calc.py` actually
computes. Acceptance criteria are numbered without gaps across all eight quests, and the tone
holds: the same Mission, Scenario, Acceptance criteria, Required evidence, Safety constraints
shape, and the same habit of naming the designed failure and then requiring proof it did not
happen.
