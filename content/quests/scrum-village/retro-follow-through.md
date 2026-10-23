---
id: scrum-retro-follow-through
version: 1
title: "Reconcile Retrospective Actions Without Duplication"
summary: "Carry actions from one retrospective to the next, report which were done, dropped or repeated, and avoid recreating what already exists."
region: scrum-village
level: builder
xp: 30
estimated_minutes: 90
order: 70
tags:
  - scrum
  - retrospective
  - follow-through
tools:
  - Markdown
  - YAML
bookend: validation
risk:
  external_write: false
  sensitive_data: false
  notes: "Both retrospectives and their actions are synthetic."
prerequisites:
  - base-camp-safe-rerun
related_quests:
  - scrum-retro-analysis
outcomes:
  - "Match new actions to earlier ones by stable key."
  - "Report completed, open and dropped actions with their evidence."
  - "Refuse to recreate an action that already exists."
proof:
  required:
    - id: action-ledger
      type: file
      description: "Provide a ledger of retrospective actions from at least two retrospectives, each with a stable key, status, evidence of completion where done, and who dropped it or that this is unknown."
      path: participant/context/scrum/retro/action-ledger.md
    - id: reconciliation-report
      type: file
      description: "Provide the reconciliation report listing, for the latest retrospective, actions carried over, completed, dropped and newly created, with the reason for each and how many retrospectives each carried action has survived."
      path: participant/context/scrum/retro/reconciliation.md
    - id: reconcile-run
      type: command-record
      description: "Save the redacted output of reconciling twice from the same input, showing no duplicate action, and of a repeated theme that was linked to an existing action."
      path: participant/evidence/scrum-retro-follow-through/attempt-001/logs/reconcile-run.txt
    - id: proof-narrative
      type: file
      description: "Explain your approach, your choices and anything you could not do, citing the acceptance criteria by number."
      path: participant/evidence/scrum-retro-follow-through/attempt-001/PROOF.md
author: Golden Thread maintainers
last_reviewed: "2026-10-20"
---

# Reconcile Retrospective Actions Without Duplication

## Mission

Build the follow-through the retro rarely gets. Match each new action to what the team already tried, report what actually happened to old ones, and never create a second copy.

## Scenario

The same action, improve the build time, appears in four retrospectives under four wordings. Each time it is new, and each time it quietly dies.

## Acceptance criteria

1. Each action has a stable key that does not depend on its wording.
2. An action that matches an existing one is linked, not recreated.
3. Each earlier action is reported as completed, open or dropped.
4. A completed action cites evidence that it was done.
5. An action reported as dropped records who dropped it or that this is unknown.
6. Running the reconciliation twice creates no duplicate.
7. The team can see how many retrospectives an action has survived.

## Required evidence

Provide the ledger, the report and the run output. In your `PROOF.md`, explain how you chose the key and one pair of actions you decided were the same, citing the acceptance criteria by number.

## Safety constraints

- Use synthetic data with invented names, dates and work items.
- Nothing in this exercise is posted to a tracker, chat channel or email.
- Do not mark an action completed without evidence.

## Hints

If the key is the wording, every rewrite is a new action. Key on the underlying experiment instead.

## Reflection

What would you do about an action that has survived five retrospectives?

## Stretch goals

- Flag actions repeatedly carried over without any change.
- Link actions to the sprint metrics they were meant to move.
