# The Golden Thread Quest — Design and Claude Code Handoff Package

**Role:** AI Context Engineer  
**Curriculum:** The AI Context Engineer Journey  
**Quest:** The Golden Thread Quest  
**Tagline:** From human intent to verified delivery.

This package contains the planning, product design, UI design, content contracts, sample content, and implementation plan for a local-first training application. It is intentionally a design package rather than the finished application.

The Golden Thread Quest trains people to manage the two bookends of software delivery:

1. Turn stakeholder intent into structured, traceable work.
2. Validate delivered behavior against that intent and preserve credible evidence.

The thread running through the curriculum is:

> Conversation → requirement → work item → implementation → test → evidence → outcome

## What is included

- Product and architectural decisions
- Screen specifications and reusable UI component definitions
- Content-authoring model using Markdown and YAML
- JSON Schemas defining the content and progress contracts
- Sample regions, badges, tracks, and quests
- Fixture participant and validation data
- A clickable, data-driven HTML/CSS prototype
- Security, accessibility, and verification requirements
- A staged, resumable Claude Code implementation plan
- Stage audits that must pass before implementation advances

## This is now an implementation

The planning package below is preserved as the specification. The application it describes
is built: `quest_app/` loads and validates the curriculum, generates the site, and runs a
loopback-only service for the few things a static page cannot safely do.

```bash
make setup && source .venv/bin/activate
make check      # format, lint, types, YAML safety, secret scan, 404 tests
make serve      # build, then serve on 127.0.0.1
```

| Read this | For |
|---|---|
| `docs/guides/PARTICIPANT.md` | Doing the quests |
| `docs/guides/REVIEWER.md` | Deciding whether evidence is verified |
| `docs/guides/VALIDATOR-AUTHORING.md` | Writing a check |
| `docs/guides/UPDATING.md` | Taking upstream curriculum changes |
| `docs/CONTENT-AUTHORING-GUIDE.md` | Writing a quest |
| `docs/SETUP.md` | Installing and troubleshooting |
| `docs/IMPLEMENTATION-DETAILS.md` | What was actually built, and where it diverges |
| `docs/TRACEABILITY.md` | Which test holds which requirement |
| `docs/RELEASE-NOTES.md` | What works, and the seven known limitations |
| `docs/audits/` | Every stage audit, including the ones that failed |

## Start here

### Review the planning package

Read these files in order:

1. `PLANNING-STATUS.md`
2. `docs/PRODUCT-BRIEF.md`
3. `docs/DECISIONS.md`
4. `docs/ARCHITECTURE.md`
5. `docs/CONTENT-MODEL.md`
6. `docs/ui/UI-SPECIFICATION.md`
7. `docs/ui/COMPONENT-CATALOG.md`
8. `docs/IMPLEMENTATION-PLAN.md`

### View the prototype

Open `prototype/index.html` directly in a browser. It uses a separate JavaScript fixture file and does not require a web server.

The prototype is a design reference, not production code. It demonstrates:

- Home and “continue quest” dashboard
- Quest map and regions
- Region and catalog filtering
- Quest details
- Evidence workspace and validation results
- Participant passport, badges, and verified progress
- Environment health
- Reviewer view
- Responsive navigation

### Hand the package to Claude Code

Open Claude Code in the extracted folder and provide:

> Read `CLAUDE.md`, `PLANNING-STATUS.md`, and the documents they identify. Audit the planning package before implementing anything. Then execute `docs/IMPLEMENTATION-PLAN.md` stage by stage. Never begin a new stage until every item in the current stage is checked, the stage audit has passed, and any findings have been fixed. Work in a feature branch and never commit directly to `main`.

## Source-of-truth boundaries

| Area | Source of truth | Ownership |
|---|---|---|
| Curriculum content | `content/` | Program maintainers |
| Data contracts | `schemas/` | Program maintainers |
| UI behavior and appearance | `docs/ui/` and prototype | Program maintainers |
| Production templates | To be implemented under `templates/` | Program maintainers |
| Participant work and evidence | Future `participant/` directory | Participant |
| Generated site and caches | Future `generated/` and `local-data/` | Machine; disposable |

Quest-specific titles, XP values, instructions, and badge rules must never be duplicated in HTML templates or application code.

## Package status

Planning and design are ready for an implementation audit and staged build. The production application has not been implemented. See `PLANNING-STATUS.md` for the exact boundary.
