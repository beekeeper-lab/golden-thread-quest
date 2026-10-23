---
id: scrum-scope-change
version: 1
title: "Detect Work Added, Removed, or Materially Changed After Sprint Start"
summary: "Compare a start-of-sprint snapshot with a later one and report scope change from recorded differences, separating real change from noise."
region: scrum-village
level: builder
xp: 30
estimated_minutes: 90
order: 30
tags:
  - scrum
  - scope
  - change-detection
tools:
  - Markdown
  - YAML
bookend: validation
risk:
  external_write: false
  sensitive_data: false
  notes: "Both snapshots are synthetic and local."
prerequisites:
  - scrum-sprint-health
outcomes:
  - "Compare two snapshots by stable identifier."
  - "Classify differences as added, removed or materially changed."
  - "Ignore changes that do not alter the commitment."
proof:
  required:
    - id: snapshot-pair
      type: file
      description: "Provide two synthetic snapshots, one at sprint start and one later, with estimates on every item, and items added, removed, re-estimated, re-worded and reassigned."
      path: participant/context/scrum/scope/snapshots.md
    - id: scope-report
      type: file
      description: "Provide the scope-change report listing each added, removed and materially changed item with the fields that differ and why it counts, and a net change to the committed total."
      path: participant/context/scrum/scope/scope-change.md
    - id: scope-run
      type: command-record
      description: "Save the redacted output of the comparison, including items that differed only in noise and were left out, and a run on identical snapshots reporting no change."
      path: participant/evidence/scrum-scope-change/attempt-001/logs/scope-run.txt
    - id: proof-narrative
      type: file
      description: "Explain your approach, your choices and anything you could not do, citing the acceptance criteria by number."
      path: participant/evidence/scrum-scope-change/attempt-001/PROOF.md
author: Golden Thread maintainers
last_reviewed: "2026-10-20"
---

# Detect Work Added, Removed, or Materially Changed After Sprint Start

## Mission

Detect what changed in the commitment after the sprint began. Match items by identifier, decide which differences matter, and show your reasoning so the team can see why a change was counted or ignored.

## Scenario

A sprint starts with 30 points and ends with 30 points. Nobody notices that 12 of them were swapped in week one, so the retrospective blames estimation.

## Acceptance criteria

1. Items are matched by stable identifier, never by title.
2. An item present only in the later snapshot is reported as added.
3. An item present only in the start snapshot is reported as removed.
4. A change to estimate, scope or acceptance criteria is reported as material, with the fields that differ.
5. A change to formatting, wording or assignee alone is reported as noise and not counted.
6. Identical snapshots report no change.
7. The report states the net effect on the committed total.

## Required evidence

Provide the snapshots, the report and the run output. In your `PROOF.md`, explain what you count as material and a change you were unsure about, citing the acceptance criteria by number.

## Safety constraints

- Use synthetic data with invented names, dates and work items.
- Nothing in this exercise is posted to a tracker, chat channel or email.
- Do not use a real sprint.

## Hints

A renamed item is the same item. If you match on title, a rename looks like one removal and one addition.

## Reflection

Where does a clarification end and a scope change begin on your team?

## Stretch goals

- Show the effect of each change on remaining capacity.
- Flag changes made by someone other than the product owner.
