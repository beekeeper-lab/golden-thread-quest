# The Golden Thread Quest

**Role:** AI Context Engineer
**Curriculum:** The AI Context Engineer Journey
**Tagline:** From human intent to verified delivery.

> **Status: work in progress. Not released, and not yet recommended for use.**
>
> The engine is substantially built and the whole of it is under test, but a release
> audit is open and has confirmed findings still being worked through. Interfaces,
> content and file layouts can change without notice, and no upgrade path is promised
> between now and a first release. Nobody has yet run this on the installed Cowork
> app, which is its primary target surface.
>
> `docs/ACCEPTANCE-CRITERIA.md` tracks what is done. `docs/audits/` holds the audit
> record, including what is currently open. `docs/RELEASE-NOTES.md` lists the known
> limitations.

A local-first training application. The curriculum lives in Markdown and YAML, your work
lives in ordinary files in your own Git repository, and the application reads them, checks
them, and presents them. It does not own them.

The Golden Thread Quest trains the two bookends of software delivery:

1. Turning stakeholder intent into structured, traceable work.
2. Validating delivered behavior against that intent and preserving credible evidence.

The thread running through it:

> Conversation → requirement → work item → implementation → test → evidence → outcome

## Start here

**If you are going to do the quests, read [`docs/USER-GUIDE.md`](docs/USER-GUIDE.md).** It
assumes you are working alone and remotely, and it covers everything from installing to
getting your first quest verified.

```bash
git clone <your fork> golden-thread-quest
cd golden-thread-quest
make setup
source .venv/bin/activate
make serve
```

`make serve` builds the site, starts a service bound to `127.0.0.1` only, and prints the
address. Open it.

## Where everything is

| Read this | For |
|---|---|
| [`docs/USER-GUIDE.md`](docs/USER-GUIDE.md) | **Everything a participant needs, start to finish** |
| `docs/guides/REVIEWER.md` | Deciding whether someone's evidence is verified |
| `docs/guides/VALIDATOR-AUTHORING.md` | Writing an automated check |
| `docs/guides/UPDATING.md` | Taking upstream curriculum changes without losing your work |
| `docs/CONTENT-AUTHORING-GUIDE.md` | Writing a quest |
| `docs/SETUP.md` | Installing, and troubleshooting when it will not start |
| `docs/RELEASE-NOTES.md` | What works, and the eight known limitations |
| `docs/IMPLEMENTATION-DETAILS.md` | What was actually built, and where it diverges from the plan |
| `docs/TRACEABILITY.md` | Which test holds which requirement |
| `docs/audits/` | Every audit, including the four that failed and the external review |
| `CONTRIBUTING.md` | Working on the application itself |

## What is here

| | |
|---|---|
| Tests | 575 — 533 under `make check`, 42 driving a real browser |
| Screens | 13 page templates, 10 reusable components |
| Schemas | 10, validating content, progress, reviews, validation results and the validator registry |
| Sample curriculum | 8 regions, 8 quests, 4 badges, 1 track |
| Sample validators | 3, plus a probe used only to prove the timeout kills a process group |
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

Stages 0 to 9 of `docs/IMPLEMENTATION-PLAN.md` are complete. The Stage 10 release decision is
open. Three release audits and one external review have run, each found something, and every
finding is fixed. The external review left the engine a release candidate and the participant
journey short: three quests across eight regions was a demonstration rather than a journey.
Since then every region has a quest — eight quests, one per region — and round 4 has audited
that work in `docs/audits/round-04-independent-audit.md`.

The application works end to end today. What is not signed off is putting it in front of a
cohort. Curriculum depth is no longer zero anywhere, but one quest per region is a first
pass, not a full journey; `docs/CURRICULUM-BACKLOG.md` holds the rest.

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
