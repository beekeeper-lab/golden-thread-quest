---
id: context-daily-plan
version: 1
title: "Build a Capacity-Aware Daily Plan"
summary: "Turn a ranked list into a plan that fits stated capacity, leaves visible what was left out, and never overbooks a person."
region: context-library
level: builder
xp: 30
estimated_minutes: 90
order: 100
tags:
  - context
  - planning
  - capacity
tools:
  - Markdown
  - YAML
bookend: cross-bookend
risk:
  external_write: false
  sensitive_data: false
  notes: "Capacity and work are synthetic."
prerequisites:
  - context-next-work
outcomes:
  - "Fit ranked work into stated capacity."
  - "Show what did not fit and why."
  - "Reserve time for known commitments."
proof:
  required:
    - id: capacity-input
      type: file
      description: "Provide synthetic capacity for a day, including meetings and a partial day, and ranked work with estimates and one item with no estimate."
      path: participant/context/plan/inputs.md
    - id: daily-plan
      type: file
      description: "Provide the plan listing scheduled work with times or amounts, the work left out and the reason, and items needing an estimate."
      path: participant/context/plan/daily-plan.md
    - id: plan-run
      type: command-record
      description: "Save the redacted output of generating the plan, a run with less capacity showing fewer items scheduled, and a check that the total never exceeds capacity."
      path: participant/evidence/context-daily-plan/attempt-001/logs/plan-run.txt
    - id: proof-narrative
      type: file
      description: "Explain your approach, your choices and anything you could not do, citing the acceptance criteria by number."
      path: participant/evidence/context-daily-plan/attempt-001/PROOF.md
author: Golden Thread maintainers
last_reviewed: "2026-10-20"
---

# Build a Capacity-Aware Daily Plan

## Mission

Make the plan honest. It fits within the capacity you state, shows what it left out and why, and asks for an estimate instead of inventing one.

## Scenario

A plan lists nine items for a day with three hours free. By noon it has failed, and nobody can tell which items were never realistic.

## Acceptance criteria

1. The plan never schedules more than the stated capacity.
2. Known commitments reduce capacity before work is scheduled.
3. Work follows the ranking, skipping only what does not fit.
4. Each omitted item is listed with the reason.
5. An item with no estimate is not scheduled and is listed as needing one.
6. Reducing capacity schedules no more items than before and never fewer than zero, and the omitted list grows.
7. A person can see how the capacity was spent.

## Required evidence

Provide the inputs, the plan and the run output. In your `PROOF.md`, explain how you handled an item that nearly fit, citing the acceptance criteria by number.

## Safety constraints

- Use synthetic work items with invented identifiers; do not use a real project.
- This quest is read-only with respect to every external system, and no live connection is needed.
- The plan is advice; it does not book time or change any calendar.

## Hints

An empty gap is a fact about capacity. Do not fill it with an invented estimate.

## Reflection

What fraction of your capacity should be left unplanned, and what is that based on?

## Stretch goals

- Add a buffer for interruptions.
- Split a long item across two days with a stated rule.
