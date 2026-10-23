---
id: context-traceability-matrix
version: 1
title: "Link Intent, Decisions, Work, Implementation, Tests, and Outcomes"
summary: "Build a matrix that follows a need from its origin to its outcome, and report each link that is missing instead of assuming it exists."
region: context-library
level: navigator
xp: 50
estimated_minutes: 120
order: 120
tags:
  - context
  - traceability
  - golden-thread
tools:
  - Markdown
  - YAML
bookend: cross-bookend
risk:
  external_write: false
  sensitive_data: false
  notes: "The project data is synthetic."
prerequisites:
  - context-dependency-map
  - context-decision-log
related_quests:
  - ba-change-impact
outcomes:
  - "Link each stage of the chain by stable identifier."
  - "Report gaps at every stage."
  - "Read the chain in both directions."
proof:
  required:
    - id: trace-data
      type: file
      description: "Provide synthetic records for intent, decisions, work items, implementation, tests and outcomes, linked by identifier, with deliberate gaps."
      path: participant/context/trace/data.md
    - id: matrix
      type: file
      description: "Provide the generated matrix with one row per intent and a column for each stage, showing the linked identifiers and marking gaps, and an orphans section for any record that no intent reaches."
      path: participant/context/trace/matrix.md
    - id: trace-run
      type: command-record
      description: "Save the redacted output of the build, showing each gap named, the matrix identical across two runs, a backward trace from one outcome to its intent and a forward trace from one intent to its tests and outcomes."
      path: participant/evidence/context-traceability-matrix/attempt-001/logs/trace-run.txt
    - id: proof-narrative
      type: file
      description: "Explain your approach, your choices and anything you could not do, citing the acceptance criteria by number."
      path: participant/evidence/context-traceability-matrix/attempt-001/PROOF.md
author: Golden Thread maintainers
last_reviewed: "2026-10-20"
---

# Link Intent, Decisions, Work, Implementation, Tests, and Outcomes

## Mission

Build the golden thread itself. From any outcome you can walk back to the intent behind it, and from any intent forward to what was built and tested, with every missing link marked.

## Scenario

A customer asks why a feature exists and whether it was tested. The answer takes three people two days to assemble, and one link is missing.

## Acceptance criteria

1. Each link uses stable identifiers, not titles.
2. The matrix covers intent, decisions, work, implementation, tests and outcomes.
3. A stage with no link is marked as a gap, not left blank.
4. A test with no intent behind it and an intent with no test are both reported.
5. A backward trace from an outcome reaches its intent.
6. A forward trace from an intent reaches its tests and outcomes.
7. The matrix is identical across two runs on the same data.

## Required evidence

Provide the data, the matrix and the run output. In your `PROOF.md`, explain how you detect an orphan at each stage, citing the acceptance criteria by number.

## Safety constraints

- Use synthetic work items with invented identifiers; do not use a real project.
- This quest is read-only with respect to every external system, and no live connection is needed.
- Do not mark a link as present without an identifier behind it.

## Hints

Start from the gaps. A matrix with no gaps in synthetic data means your gaps were not hard enough.

## Reflection

Which link in a real project would be hardest to keep up to date?

## Stretch goals

- Report the age of each link.
- Show which outcomes rest on untested work.
