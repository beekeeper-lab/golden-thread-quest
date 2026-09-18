# The Golden Thread Quest

**Role:** AI Context Engineer
**Curriculum:** The AI Context Engineer Journey
**Tagline:** From human intent to verified delivery.

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
| Tests | 544 — 502 under `make check`, 42 driving a real browser |
| Screens | 13 page templates, 10 reusable components |
| Schemas | 10, validating content, progress, reviews, validation results and the validator registry |
| Sample curriculum | 8 regions, 3 quests, 4 badges, 1 track |
| Sample validators | 3, plus a probe used only to prove the timeout kills a process group |
| Build time | 203 quests in under a second |

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
open. Three release audits have run, each returned `do-not-release`, and every finding from
all three is fixed. An external reviewer then audited the result: the engine is a release
candidate, the participant journey is not, because three quests across eight regions is a
demonstration rather than a journey. `docs/audits/final-audit.md` holds the gate.

The application works end to end today. What is not signed off is putting it in front of a
cohort, and the blocker is curriculum depth rather than engine quality.

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
