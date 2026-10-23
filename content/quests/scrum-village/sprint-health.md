---
id: scrum-sprint-health
version: 1
title: "Report Progress, Aging Work, Blockers, WIP, and Dependency Risk"
summary: "Produce a sprint health report from recorded fields only, with each finding showing the items and fields it rests on."
region: scrum-village
level: builder
xp: 30
estimated_minutes: 90
order: 20
tags:
  - scrum
  - reporting
  - flow
tools:
  - Markdown
  - YAML
bookend: validation
risk:
  external_write: false
  sensitive_data: false
  notes: "The snapshot is synthetic and local. The report names invented people only."
prerequisites:
  - scrum-standup-digest
outcomes:
  - "Compute progress, aging, blocked work, work in progress and dependency risk from recorded fields."
  - "Show the items behind every number."
  - "Report missing data as a gap instead of estimating it."
proof:
  required:
    - id: sprint-snapshot
      type: file
      description: "Provide a synthetic sprint snapshot of at least twenty work items with status, assignee, created and updated dates, blockers and dependencies, including items with missing fields."
      path: participant/context/scrum/sprint-snapshot.md
    - id: health-report
      type: file
      description: "Provide the generated health report: progress, aging items, blocked items, work in progress per person and dependency risks, each listing the items it counts."
      path: participant/context/scrum/sprint-health.md
    - id: health-run
      type: command-record
      description: "Save the redacted output of generating the report twice from the same snapshot, showing identical output, and the gaps it reported for items with missing fields."
      path: participant/evidence/scrum-sprint-health/attempt-001/logs/health-run.txt
    - id: proof-narrative
      type: file
      description: "Explain your approach, your choices and anything you could not do, citing the acceptance criteria by number."
      path: participant/evidence/scrum-sprint-health/attempt-001/PROOF.md
author: Golden Thread maintainers
last_reviewed: "2026-10-20"
---

# Report Progress, Aging Work, Blockers, WIP, and Dependency Risk

## Mission

Build a sprint health report that a team can trust because it shows its working. Every number lists the items counted, every risk names the field that exposed it, and anything the snapshot cannot support is reported as a gap.

## Scenario

Day seven of a ten-day sprint. The board looks green because everything is In Progress, while four items have not changed in six days and two wait on a third nobody is working on.

## Acceptance criteria

1. Progress is computed from recorded status, and the report shows the items counted.
2. An item is called aging when its last update is older than a stated threshold, and the threshold is shown.
3. A blocked item is identified from a recorded blocker field, not from words in its title.
4. Work in progress per person is counted and the limit is stated, or the report says none is set.
5. A dependency risk names both items and why the chain is a risk.
6. An item with a missing field is listed as a gap and is not estimated.
7. Generating the report twice from the same snapshot gives identical output.

## Required evidence

Provide the snapshot, the report and the run output. In your `PROOF.md`, explain your aging threshold and one item the report could not classify, citing the acceptance criteria by number.

## Safety constraints

- Use synthetic data with invented names, dates and work items.
- Nothing in this exercise is posted to a tracker, chat channel or email.
- Do not name real colleagues or real work.

## Hints

Say what each finding is computed from. A finding with no field behind it is an opinion.

## Reflection

Which number in your report would a team most want to argue with, and what would settle it?

## Stretch goals

- Show the same report for two days and highlight what changed.
- Add a dependency chain longer than two items.
