# Golden Thread Quest: System Design

| | |
|---|---|
| Version | 2.0.0 |
| Date | 2026-09-29 |
| Describes | `main` at `a837e7a` (round 17's merge, with its timing-test fix) |
| Plan status | Phase 0 (reset and plan) complete; Gate 0 open: the program owner approves Phase 1 (Part 7, Section 7.4) |
| Rendered copies | `artifacts/html/design/golden-thread-system-design-v2.0.0.html`, `artifacts/pdf/design/golden-thread-system-design-v2.0.0.pdf` |

## About this document

This is the teaching design document for the Golden Thread Quest application. It is written
for a developer or technical stakeholder who has never seen the system, and it has two jobs:

1. explain what the system is for and how it is designed, in order, with the reason for
   each design choice;
2. say where the work stands and how the rest of it is planned: the goal, the phases, and
   the gate between each phase where scope may change.

It describes the code at the commit above. Where the code and the specification documents
(`docs/ARCHITECTURE.md`, `docs/CONTENT-MODEL.md` and others) disagree, this document follows
the code and says so at the point of disagreement. Where an open audit finding shows the code
falling short of the design, the finding is named beside the claim.

The Markdown files in this folder are the source of truth. The HTML and PDF are rendered from
them and carry the same version in their file names and on their title page.
`REGENERATING.md` explains the version rule and how to rebuild both.

## Contents

1. [Purpose and users](01-purpose-and-users.md): the problem, the three roles, the
   ownership boundary, and how progress stays honest.
2. [Architecture](02-architecture.md): the generator and the loopback service, content
   loading and schema validation, view models and rendering, the validator runner, the
   progress store and locks, and the update path.
3. [Data, identifiers and state](03-data-and-state.md): the repository folders, the
   records, stable IDs, versions and hashes, and the attempt state machine.
4. [The system in motion](04-activity-flows.md): activity diagrams for starting a quest,
   running a validator, submitting, reviewing, building and updating, and a sequence
   diagram of one browser action.
5. [The security model](05-security.md): threats, the loopback boundary, allowlisted
   writes, validator containment, the secret scan, review integrity.
6. [Key decisions](06-decisions.md): the forty-three ADRs grouped by the question each
   answers.
7. [Where we are, and the phase plan](07-status-and-remaining-work.md): the goal, the
   current state, how every phase runs, the phases, and release one's known limitations.
8. [Glossary](08-glossary.md).

Also in this folder: `VERSION`, `CHANGELOG.md`, `REGENERATING.md`.

## Conventions

- Every diagram is Mermaid, drawn from the code, with a numbered walkthrough beside it.
  GitHub renders the Mermaid blocks; the HTML carries them as inline SVG.
- `ADR-nnn` refers to `docs/DECISIONS.md`. Audit finding IDs (C1, E9 and so on) refer to the
  round record named beside them under `docs/audits/`. `Dn` refers to the
  deferred-work register in `docs/IMPLEMENTATION-PLAN.md`.
- Commands are run from the repository root. `quest-app` needs the virtual environment
  active: `make setup`, then `source .venv/bin/activate`.
- Terms are defined at first use and collected in the glossary.
