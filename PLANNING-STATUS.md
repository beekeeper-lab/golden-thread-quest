# Planning Status

## Current readiness

**Status (2026-09-21):** Implemented. Stages 0 to 9 are complete and audited. The Stage 10
release decision is still open: three release audits and one external review have run, and a
fourth round is recorded in `docs/audits/round-04-independent-audit.md`. The blocker the
external review named — three quests across eight regions — is addressed: every region now
has a quest, eight in total, and `docs/CURRICULUM-BACKLOG.md` holds the quests that would
turn one-per-region into a journey. See `docs/RELEASE-NOTES.md` for what works and the known
limitations, and `docs/audits/` for every audit including the ones that failed.

The original planning status follows, preserved because it is the specification the
implementation was held to.

**Status at planning time:** Ready for Claude Code planning audit, followed by staged
implementation.

The product direction, architecture boundary, content model, primary screens, component vocabulary, participant lifecycle, security model, and implementation stages are defined. A data-driven interactive prototype is included as the visual acceptance target.

This does **not** mean the application is already built. It means enough ambiguity has been removed for an implementation agent to work predictably.

## Planning decisions completed

- [x] Defined the professional role and curriculum hierarchy.
- [x] Selected an independent repository for The Golden Thread Quest.
- [x] Selected participant forks as the default distribution model.
- [x] Separated program-owned, participant-owned, and generated files.
- [x] Defined Markdown/YAML as authored content and JSON as generated interchange.
- [x] Defined JSON Schema validation as a build gate.
- [x] Selected Python and Jinja2 for deterministic HTML generation.
- [x] Selected a small loopback-only Python service for local mutations and validation.
- [x] Chosen a professional field-guide visual direction with restrained quest language.
- [x] Defined the primary screens and reusable components.
- [x] Defined claimed, validated, submitted, and verified progress states.
- [x] Separated self-reported progress from reviewer-verified progress.
- [x] Defined sample content and fixture state.
- [x] Defined a stage-gated, auditable implementation plan.

## Intentionally deferred decisions

These are implementation choices Claude may recommend during Stage 0, but it must record and justify any final choice in `docs/DECISIONS.md` before coding depends on it.

- Exact supported Python minor versions; target should include Python 3.12 or newer.
- Pydantic versus direct `jsonschema` use for internal model validation.
- FastAPI versus a smaller equivalent for the loopback service.
- Exact Markdown renderer, provided CommonMark and sanitization requirements are met.
- CSS organization details, provided design tokens and component isolation are preserved.
- Test runner details beyond the required test layers.

## Explicitly out of scope for the first release

- Hosted multi-user service
- Central authentication
- Central database
- Global leaderboard containing participant evidence
- Automatic publishing of private evidence
- Arbitrary shell command execution from the browser
- Automatic external-system writes without human confirmation
- Automatic reviewer approval
- Mobile-native application
- Rich collaborative editing
- Full curriculum content for every future quest

## Conditions for beginning implementation

Claude must first:

- [x] Create a feature branch; never work directly on `main`.
- [x] Read every document referenced by `CLAUDE.md`.
- [x] Run the design-package validation instructions.
- [x] Compare the prototype against the screen and component specifications.
- [x] Identify contradictions, omissions, unsafe assumptions, or infeasible requirements.
- [x] Record findings in `docs/audits/stage-00-planning-audit.md`.
- [x] Resolve all blocking findings before Stage 1.

## Definition of planning complete

Planning is complete when the receiving implementation agent can answer all of the following without inventing product behavior:

1. Who is the application for?
2. What is the application responsible for?
3. Where does curriculum content live?
4. How is that content validated?
5. Which files may the application modify?
6. What distinguishes participant, validator, and reviewer states?
7. Which screens and components are required?
8. What must work without network access?
9. What safety boundaries apply to local command execution?
10. How does the agent prove each implementation stage is complete?

This package is intended to answer all ten.
