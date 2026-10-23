---
id: context-dependency-map
version: 1
title: "Build Work and Decision Dependency Indexes"
summary: "Build indexes of what depends on what, among work items and decisions, and report cycles, missing targets and the items that block the most."
region: context-library
level: builder
xp: 30
estimated_minutes: 90
order: 80
tags:
  - context
  - dependencies
  - indexing
tools:
  - Markdown
  - YAML
bookend: validation
risk:
  external_write: false
  sensitive_data: false
  notes: "The data is synthetic."
prerequisites:
  - context-stable-identities
related_quests:
  - scrum-sprint-health
outcomes:
  - "Derive dependency links from recorded fields."
  - "Build forward and reverse indexes."
  - "Report cycles and links to items that do not exist."
proof:
  required:
    - id: dependency-data
      type: file
      description: "Provide synthetic work items and decisions with dependency links, including a cycle and a link to a missing item, with the field each link comes from named."
      path: participant/context/dependencies/data.md
    - id: dependency-index
      type: file
      description: "Provide the generated forward and reverse indexes and the list of items blocking the most work."
      path: participant/context/dependencies/index.md
    - id: dependency-run
      type: command-record
      description: "Save the redacted output of the build, showing the cycle and the missing target reported by name and the same index produced on a second run."
      path: participant/evidence/context-dependency-map/attempt-001/logs/dependency-run.txt
    - id: proof-narrative
      type: file
      description: "Explain your approach, your choices and anything you could not do, citing the acceptance criteria by number."
      path: participant/evidence/context-dependency-map/attempt-001/PROOF.md
author: Golden Thread maintainers
last_reviewed: "2026-10-20"
---

# Build Work and Decision Dependency Indexes

## Mission

Make dependencies visible and checkable. The index answers what this waits on and what waits on this, and it complains loudly about cycles and links that point nowhere.

## Scenario

Two stories wait on each other and a third waits on a decision that was never recorded. The plan has them all starting Monday.

## Acceptance criteria

1. Dependencies come from recorded fields, not from words in a title.
2. A forward and a reverse index are both generated.
3. A cycle is reported with the items in it.
4. A link to a missing item is reported by name, not dropped.
5. A dependency on a decision is represented like one on a work item.
6. The five items blocking the most other items are listed with their counts.
7. The index is identical across two runs on the same input.

## Required evidence

Provide the data, the index and the run output. In your `PROOF.md`, explain how you detect cycles and one dependency you chose not to infer, citing the acceptance criteria by number.

## Safety constraints

- Use synthetic work items with invented identifiers; do not use a real project.
- This quest is read-only with respect to every external system, and no live connection is needed.
- Do not infer a dependency from wording alone.

## Hints

A reverse index is the answer to who is waiting on me, which is the question people actually ask.

## Reflection

Which dependency in your data would be easiest to miss in a real tracker?

## Stretch goals

- Compute the longest chain and show it.
- Show how an item's slip affects its dependents.
