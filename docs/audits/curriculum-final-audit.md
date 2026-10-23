# Curriculum Final Audit (2026-10-21)

Compares what was specified, what was built, what was tested and what was written about it,
for the work that took the sample curriculum from eight quests to the full backlog and
released it as 0.3.0. It follows `docs/design/08-curriculum-plan.md` and sits beside the
per-step audits (`phase-c1-base-camp.md` to `phase-c9-trap-cards.md`) and the original
`final-audit.md`.

## Decision

**Released as 0.3.0, to the pilot, with advisories.** Instructed by the program owner on
2026-10-20 and 2026-10-21, while Phase 2B (the pilot) runs. Doc 07 says scope changes at a
gate; this change was made on the program owner's direct instruction, and Gate 2 should
confirm or reverse it.

## Specification against implementation

| Specified | Built | Matches |
|---|---|---|
| 128 quests, one for every row of `docs/CURRICULUM-BACKLOG.md` | 128 quest files with the proposed ids, names and levels | Yes: Base Camp 9, BA Ruins 13, Scrum Village 9, Context Library 12, Playwright Labyrinth 20, Jira Jungle 23, GitHub Caverns 18, Trello Islands 17, Trap Cards 7 |
| Hidden and adversarial challenges, "may be revealed during workshops or included as optional trap cards" | A ninth region, Trap Cards, with seven quests | Yes, with a decision: they are ordinary quests in their own region and count toward progress; nothing marks them optional |
| Plan order C1 to C9, one region per step, each audited | Built in that order, each with a recorded audit and a merged pull request (#28 to #36) | Yes |
| Authored content only: no template, Python or CSS change to make a quest appear | No change to `quest_app/`, `validators/`, `schemas/`, `templates/` or `tools/` since 0.2.4 | Yes |
| Quests that write to an outside system must meet the preview-and-confirm conditions first | Nineteen quests declare `risk.external_write: true` (Jira 7, GitHub 6, Trello 6) and require all five controls in their proof | Yes, as content controls; see "What is and is not enforced" |
| Prerequisites acyclic and reachable from a quest with none | Checked by validation and by the test that walks every chain | Yes. BA Ruins starts at `ba-ingest-transcript` rather than Base Camp, by design |

Totals: 4,360 XP across the 128 quests (6 scout, 39 explorer, 44 builder, 34 navigator,
5 boss). 70 quests are flagged `sensitive_data: true`.

## What changed outside the quest files

- `tests/test_release_facts.py`: the test that said no quest writes externally is replaced
  by `test_a_quest_that_writes_to_an_external_system_carries_the_stated_controls`. It names
  the nineteen write quests, requires the `write` tag to match the declared writes, and
  requires each writer's required proof to show a preview, a confirmation, a permission check,
  a duplicate check, a timestamped result, a second run and a sandbox allowlist, to follow
  `base-camp-write-preview`, to name a sandbox in its risk note and to rule out production in
  its safety constraints. The validator `network: denied` assertion is kept. It is a
  strengthening: it was shown to fail when a control word was removed from one quest. Its
  limit is that it matches keywords across the pooled proof descriptions, so the named set
  and the tag check carry part of the weight.
- `tests/integration/test_cli_actions.py`: the `unlock` helper skips a prerequisite that is
  already verified, so a quest with two paths to one prerequisite can be tested.
- `tests/ui/test_browser_flows.py`: one assertion said the Jira region shows one quest; it now
  counts the region's files. It was a stale assumption from the one-quest-per-region sample.
- `docs/SECURITY-AND-PRIVACY.md`: the external-writes section no longer says release one
  performs none; it says the application performs none, that these quests teach a sandboxed
  write, and that the controls are content properties.
- README, RELEASE-NOTES, PACKAGE-MANIFEST, PLANNING-STATUS, the implementation-plan log,
  doc 07, the pilot guides and `install.sh`: counts, status and the version.

## Tested

- `make check` equivalents at each step: format, lint, type and YAML-safety checks, the secret
  scan, and every non-browser test. At the last step, 1,654 passed. Earlier steps passed their
  own counts (1,470 at C3 to 1,640 at C8).
- The 57 browser tests were run once, at release, and pass after the stale assertion above was
  corrected. They had not been run at any earlier step.
- Each step was reviewed by an independent fresh-context pass before its checks, and the
  fixes reviewed again where the first pass found High findings (Playwright, Jira). Across the
  nine steps those passes found no Blocking finding and a recurring High: acceptance criteria
  that no required proof item would show. Every one was fixed by widening the proof, not by
  removing the criterion.
- Caveats on the test record: the later steps used a sharded runner (not `make check` itself)
  that lives outside the repository, with one concurrency-sensitive test,
  `TestThePortFileLifecycle`, rerun alone each time it failed under parallel load; it passes
  alone and in serial. An early sharded run was invalid because of a fault in the runner and
  was discarded. The 24-way run once filled `/tmp`.

## What is and is not enforced

The application still performs no external write and makes no outbound request of its own. The
nineteen write quests are controls the participant builds and the reviewer reads. Nothing in
the product stops a participant from writing to a production system; the quests tell them not
to, require a sandbox allowlist in their proof, and a reviewer decides.

## Not verified, and known limitations

1. **Nobody outside the project has read the 120 new quests.** Independent audit passes
   checked structure, proof coverage and safety; they cannot say whether a business analyst
   finds a quest clear or worth an hour. Expect rough spots.
2. **No validator checks the new quests.** All use files and command records, and a reviewer
   decides. The Playwright test-quality validator named in the plan was not built.
3. **The write quests need a sandbox** Jira project, GitHub repository or Trello board; who
   provides them is undecided.
4. **The full suite takes about 90 minutes in serial**, because many tests run once per quest.
5. **The home page's recommendation rule** was written for eight quests and has not been
   looked at with 128.
6. **Reviewer load** is untested: the pilot has produced one hand-in so far, and 128 quests
   multiply what a reviewer may be asked to read.
7. The remaining items are in `docs/PARKING-LOT.md`, dated 2026-10-21.

## Deferred

Gate 2 decisions: confirm or reverse this release; the pilot report; sandbox access; the
reviewer-load question; a human read of one region; the home-page recommendation; the slow
suite; and the Playwright validator.
