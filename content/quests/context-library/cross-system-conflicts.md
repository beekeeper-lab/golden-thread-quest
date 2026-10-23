---
id: context-cross-system-conflicts
version: 1
title: "Report Contradictory State Across Systems"
summary: "Find work whose recorded state differs between systems, report each contradiction with its sources and times, and refuse to pick a winner."
region: context-library
level: navigator
xp: 50
estimated_minutes: 120
order: 60
tags:
  - context
  - conflicts
  - cross-system
tools:
  - Markdown
  - YAML
bookend: validation
risk:
  external_write: false
  sensitive_data: false
  notes: "The records are synthetic."
prerequisites:
  - context-stable-identities
  - context-preserve-source-fields
outcomes:
  - "Link the same work across systems and compare its state."
  - "Report a conflict with both values, sources and times."
  - "Distinguish a conflict from an expected lag."
proof:
  required:
    - id: linked-records
      type: file
      description: "Provide synthetic linked records across three systems, with some states that agree, some that differ, some that differ only by a stated lag and at least one record with no counterpart in another system."
      path: participant/context/conflicts/records.md
    - id: conflict-report
      type: file
      description: "Provide the report listing each conflict with the systems, both values, when each was last updated and why it counts as a conflict, plus the differences judged to be lag and a section of unlinked records."
      path: participant/context/conflicts/report.md
    - id: conflict-run
      type: command-record
      description: "Save the redacted output of the run showing no value was overwritten and that the same input gives the same report."
      path: participant/evidence/context-cross-system-conflicts/attempt-001/logs/conflict-run.txt
    - id: proof-narrative
      type: file
      description: "Explain your approach, your choices and anything you could not do, citing the acceptance criteria by number."
      path: participant/evidence/context-cross-system-conflicts/attempt-001/PROOF.md
author: Golden Thread maintainers
last_reviewed: "2026-10-20"
---

# Report Contradictory State Across Systems

## Mission

Surface contradictions instead of resolving them. Each report shows what each system says and when, so a person can decide what is true.

## Scenario

The tracker says Done, the board says In Review, and the repository issue is still open. A report claims the work is finished.

## Acceptance criteria

1. Linked items are compared field by field using their stable identities.
2. Each conflict lists both values, their systems and their last update times.
3. A difference within a stated lag is classified as lag, not conflict.
4. No value is overwritten and no winner is chosen.
5. A missing counterpart is reported as unlinked, not as a conflict.
6. The same input gives the same report.
7. A reviewer can see why each item was or was not called a conflict.

## Required evidence

Provide the records, the report and the run output. In your `PROOF.md`, explain your lag rule and one case you found ambiguous, citing the acceptance criteria by number.

## Safety constraints

- Use synthetic work items with invented identifiers; do not use a real project.
- This quest is read-only with respect to every external system, and no live connection is needed.
- Do not change the state of any real item.

## Hints

Say what you would need to know to decide. If it is a time or an owner, report that too.

## Reflection

Which system should you trust when they disagree, and why is that the wrong question for a report?

## Stretch goals

- Rank conflicts by how much downstream work they affect.
- Report conflicts that have persisted across runs.
