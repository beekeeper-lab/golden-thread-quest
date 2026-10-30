# The Golden Thread Quest

**Role:** AI Context Engineer
**Curriculum:** The AI Context Engineer Journey
**Tagline:** From human intent to verified delivery.

> **Status: work in progress. Pilot release 0.3.1: not for general use.**
>
> It is released to a small invited pilot.
>
> If you are in the pilot, start with [`docs/guides/PILOT.md`](docs/guides/PILOT.md).
>
> The engine is built and under test, and it passed its release checklist: a true clean
> clone, and the participant, reviewer, maintainer and failure flows in a real browser
> (`docs/audits/final-audit.md`). The curriculum is the full backlog: 128 quests in nine
> regions, added in 0.3.0 and read so far only by independent audit passes
> (`docs/audits/curriculum-final-audit.md`). Interfaces,
> content and file layouts can change without notice, and no upgrade path is promised
> between the pilot and a first general release. Nobody has yet run this on the installed
> Cowork app, which is its primary target surface.
>
> `docs/ACCEPTANCE-CRITERIA.md` tracks what is done. `docs/audits/` holds the audit
> record. `docs/RELEASE-NOTES.md` lists the known limitations.

A local-first training application. The curriculum lives in Markdown and YAML, your work
lives in ordinary files in your own Git repository, and the application reads them, checks
them, and presents them. It does not own them.

The Golden Thread Quest trains the two bookends of software delivery:

1. Turning stakeholder intent into structured, traceable work.
2. Validating delivered behavior against that intent and preserving credible evidence.

The thread running through it:

> Conversation → requirement → work item → implementation → test → evidence → outcome

## Start here

**In the pilot** (a business analyst or manual tester, no Git needed): follow
[`docs/guides/PILOT.md`](docs/guides/PILOT.md). One pasted line sets everything up, `gtq start`
opens the application, and `gtq hand-in` and `gtq get-review` send your work and bring your
review back.

**If you are going to do the quests any other way, read [`docs/USER-GUIDE.md`](docs/USER-GUIDE.md).**
It assumes you are working alone and remotely, and it covers everything from installing to
getting your first quest verified. For a terminal and a browser:

```bash
git clone <your fork> golden-thread-quest
cd golden-thread-quest
make setup
source .venv/bin/activate
make serve
```

`make serve` builds the site, starts a service bound to `127.0.0.1` only, and prints the
address. Open it.

## The curriculum

128 quests in nine regions. A quest is locked until the quests it depends on are verified,
so you work through a region rather than around it. The catalog page lists all of them, and
every quest page says what it asks for, what evidence to hand in and who needs to approve it.

| Region | Quests | What it teaches |
|---|---|---|
| Base Camp | 9 | A safe workspace: ownership zones, secrets, previews, audit logs, reruns, recovery, hostile input, failure handling |
| BA Ruins | 13 | From a meeting to work items: transcripts, decisions, questions, ambiguity, stories, slicing, impact |
| Scrum Village | 9 | Stand-ups, sprint health, scope change, refinement, review, retrospectives, release notes, stakeholder summaries |
| Context Library | 12 | Trustworthy local context: identity, fidelity, freshness, dependencies, decisions, traceability |
| Playwright Labyrinth | 20 | Risk-based testing: strategy, maintainable Playwright tests, evidence, triage, repair, defect reports |
| Jira Jungle | 23 | Reading and (in a sandbox) writing Jira with an agent |
| GitHub Caverns | 18 | The same for GitHub issues and pull requests |
| Trello Islands | 17 | The same for Trello boards and cards |
| Trap Cards | 7 | Adversarial challenges: duplicates, stale context, contradictions, injected instructions, partial failures, flaky tests, false repairs |

**Where to start.** Everyone can begin with Base Camp. Analysts can start with
`ba-ingest-transcript`, which needs nothing before it, and testers with
`playwright-first-independent-test` after `base-camp-repository-safety`. The home page
recommends a next quest from what you have verified.

**The Quest Map.** The map page draws each region as land, larger where there are more
quests, each with the number of its quests that a reviewer has verified. Select a region to open
its card. The same regions are listed in text below the map.

**Quests that need an outside account.** The Jira, GitHub and Trello regions read from, and
some write to, those systems. You need an account, and for the 19 quests that write you need
a **sandbox** Jira project, GitHub repository or Trello board that you are allowed to change:
never a production one. Those quests tell you to stop and ask if you do not have one. The
application itself never writes to an outside system; in these quests *you* build the
write, with a preview, a confirmation, a permission and duplicate check, a result record, a
safe rerun and a sandbox allowlist, and a reviewer reads your evidence. Quests that write are
marked on their page.

**Using made-up material.** Your work is stored in your own repository. Use fictional
tickets, transcripts you wrote yourself and fake names unless your program has said
otherwise.

## Where everything is

| Read this | For |
|---|---|
| [`docs/guides/PILOT.md`](docs/guides/PILOT.md) | **Pilot participants: setup, a quest, hand-in and review, in order** |
| [`docs/USER-GUIDE.md`](docs/USER-GUIDE.md) | **Everything a participant needs, start to finish** |
| `docs/guides/PARTICIPANT.md` | A shorter reference for doing a quest |
| `docs/guides/PILOT-LEAD.md` | Running the pilot: the invitation, reviewing hand-ins, collecting feedback |
| `docs/guides/REVIEWER.md` | Deciding whether someone's evidence is verified |
| `docs/guides/VALIDATOR-AUTHORING.md` | Writing an automated check |
| `docs/guides/UPDATING.md` | Taking upstream curriculum changes without losing your work |
| `docs/CONTENT-AUTHORING-GUIDE.md` | Writing a quest, including the extra rules for a quest that writes to an outside system |
| `docs/CURRICULUM-BACKLOG.md` | The full list of planned quests, all built as of 0.3.0 |
| `docs/design/08-curriculum-plan.md` | How the curriculum was built out, region by region |
| `docs/PARKING-LOT.md` | Open questions and findings not yet decided |
| `docs/SETUP.md` | Installing, and troubleshooting when it will not start |
| `docs/RELEASE-NOTES.md` | What works, and the known limitations |
| `docs/IMPLEMENTATION-DETAILS.md` | What was actually built, and where it diverges from the plan |
| `docs/TRACEABILITY.md` | Which test holds which requirement |
| `docs/audits/` | Every audit, including the four that failed and the external review |
| `CONTRIBUTING.md` | Working on the application itself |

## What is here

| | |
|---|---|
| Tests | 1865 — 1800 under `make check`, 65 driving a real browser. The line `make check` prints counts skips too, and it can read higher than the total above: a module that skips itself as a whole because an optional dependency is missing (`pytest.importorskip`) counts as one skip, not one per test it would have contained. |
| Screens | 13 page templates, 11 reusable components |
| Schemas | 10, validating content, progress, reviews, validation results and the validator registry |
| Sample curriculum | 9 regions, 128 quests, 4 badges, 2 tracks |
| Sample validators | 3 quest-facing, plus 2 registered probes and one unregistered slow probe used only by the tests |
| Build time | the shipped curriculum plus 200 synthetic quests, in under a second |

## The rules it holds itself to

These are not aspirations. Each one has a test, and `docs/TRACEABILITY.md` names it.

- **Adding a quest is one Markdown file.** It appears in its region, the catalog, the
  filters, its tag page, the search index and the prerequisite graph with no change to
  Python, Jinja2, JavaScript or CSS. A test asserts those directories are byte-identical
  after a quest is added.
- **Content that does not validate is never published.** A failed build leaves the last good
  site standing and writes the errors as their own page.
- **Your files are yours.** The application writes only inside `participant/`, only through
  documented actions, atomically, and records every change in `participant/ACTIVITY.md`.
  `make clean` refuses to touch them. It never commits, pushes or merges.
- **Nothing the participant or a validator does can produce verified completion.** Only an
  approved review can, and fourteen attempts to get around that were tried by independent
  auditors; the two that succeed are documented limitations, not oversights.
- **No arbitrary commands.** A quest names a check by ID; it can never supply a command, an
  argument or a path.

## Ownership boundaries

| Area | Source of truth | Owner | In Git |
|---|---|---|---|
| Curriculum content | `content/` | Program maintainers | yes |
| Data contracts | `schemas/` | Program maintainers | yes |
| Application and templates | `quest_app/`, `templates/`, `assets/` | Program maintainers | yes |
| Registered validators | `validators/` | Program maintainers | yes |
| Your work and evidence | `participant/` | **You** | yes — it is your portfolio |
| Generated site and caches | `generated/`, `local-data/` | Machine; disposable | no |

Quest titles, XP values, instructions and badge rules never appear in templates or
application code. A test fails if one does.

## Status

Stages 0 to 9 of `docs/IMPLEMENTATION-PLAN.md` are complete. The remaining work follows the
phase plan in `docs/design/07-status-and-remaining-work.md`. Phase 1 passed its release
checklist, and at Gate 1 the program owner released 0.2.0 to a pilot, which is running.
`docs/audits/` holds every audit. An external review, early in that history, left the engine
a release candidate and the participant journey short: the curriculum was eight quests, one
per region. On the program owner's instruction, version 0.3.0 (2026-10-21) built it out to
the whole backlog: 128 quests in nine regions, each step audited
(`docs/audits/curriculum-final-audit.md`).

The application works end to end today. What is not signed off is putting it in front of a
cohort. The new quests have been checked by independent audit passes but not yet read by the
people they are written for, the 19 quests that write to an outside system need a sandbox
that nobody has yet been assigned to provide, and reviewer load across 128 quests is
untested. `docs/PARKING-LOT.md` lists these and the rest for the next gate.

## The planning package

The specification this was built from is preserved unchanged, because the audits are held
against it:

`PLANNING-STATUS.md` · `docs/PRODUCT-BRIEF.md` · `docs/DECISIONS.md` ·
`docs/ARCHITECTURE.md` · `docs/CONTENT-MODEL.md` · `docs/ui/UI-SPECIFICATION.md` ·
`docs/ui/SCREEN-SPECS.md` · `docs/ui/COMPONENT-CATALOG.md` · `docs/SECURITY-AND-PRIVACY.md` ·
`docs/ACCESSIBILITY-AND-DESIGN.md` · `docs/ACCEPTANCE-CRITERIA.md` ·
`docs/IMPLEMENTATION-PLAN.md`

`prototype/` holds the original clickable design reference. It is superseded by the
production screens and is kept only as the visual record of what was approved.

## Licence

Free to use, free to teach from, free to adapt. Two licences, because this repository holds
two kinds of work:

- **Software — MIT.** Everything except `content/`, `docs/` and the root Markdown documents.
- **Curriculum and documentation — CC BY 4.0.** `content/`, `docs/`, and the root Markdown
  documents. Credit Beekeeper Lab and say if you changed anything.

`LICENSE` and `LICENSE-CONTENT` have the terms. `vendor/axe.min.js` is third-party
(axe-core, Deque Systems, MPL-2.0) and carries its own licence.

Anything you author under `participant/` is yours. Neither licence claims it.
