# Golden Thread Quest: System Design

| | |
|---|---|
| Version | 1.1.0 |
| Date | 2026-09-25 |
| Describes | `main` at `0018e2d`, the merge of pull request 10 (round 12) |
| Audit status from | `main` at `0018e2d`: round 12 is complete and merged, eighteen findings all fixed except one (E9) stated as a known limitation. DH7 is still open; round 13 has not yet run against this commit |
| Rendered copies | `artifacts/html/design/golden-thread-system-design-v1.1.0.html`, `artifacts/pdf/design/golden-thread-system-design-v1.1.0.pdf` |

## About this document

This is the teaching design document for the Golden Thread Quest application. It is written
for a developer or technical stakeholder who has never seen the system, and it has two jobs:

1. explain what the system is for and how it is designed, in order, with the reason for
   each design choice;
2. say what is finished, what is open, and what is deliberately left for later.

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
6. [Key decisions](06-decisions.md): the forty-one ADRs grouped by the question each
   answers.
7. [Status and remaining work](07-status-and-remaining-work.md): stages, DH7, the audit
   history, the open round 12 findings, known limitations and deferred work.
8. [Glossary](08-glossary.md).

Also in this folder: `VERSION`, `CHANGELOG.md`, `REGENERATING.md`.

## Conventions

- Every diagram is Mermaid, drawn from the code, with a numbered walkthrough beside it.
  GitHub renders the Mermaid blocks; the HTML carries them as inline SVG.
- `ADR-nnn` refers to `docs/DECISIONS.md`. Round 12 finding IDs (C1, E1, T1 and so on) refer
  to `docs/audits/round-12-independent-audit.md`, now merged to `main`. `Dn` refers to the
  deferred-work register in `docs/IMPLEMENTATION-PLAN.md`.
- Commands are run from the repository root. `quest-app` needs the virtual environment
  active: `make setup`, then `source .venv/bin/activate`.
- Terms are defined at first use and collected in the glossary.
