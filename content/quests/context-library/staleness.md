---
id: context-staleness
version: 1
title: "Detect Context Too Old for a Reliable Answer"
summary: "Attach a freshness to every piece of local context and refuse, or warn, when an answer would rely on context older than it should."
region: context-library
level: builder
xp: 30
estimated_minutes: 90
order: 70
tags:
  - context
  - freshness
  - reliability
tools:
  - Markdown
  - YAML
bookend: validation
risk:
  external_write: false
  sensitive_data: false
  notes: "Timestamps and records are synthetic."
prerequisites:
  - base-camp-repository-safety
related_quests:
  - scrum-sprint-health
outcomes:
  - "Record when each item was last retrieved."
  - "Set freshness limits per kind of context."
  - "Warn or decline when an answer relies on stale context."
proof:
  required:
    - id: freshness-policy
      type: file
      description: "State the freshness limit for each kind of context and the reason, and what an answer does when a limit is exceeded."
      path: participant/context/freshness/policy.md
    - id: stale-run
      type: command-record
      description: "Save the redacted output of an answer built from fresh context and the same question answered after the clock moved past the limits, each run showing the clock value set, the oldest context used with its age and, in the second, the stale items named and the answer qualified."
      path: participant/evidence/context-staleness/attempt-001/logs/stale-run.txt
    - id: missing-timestamp-run
      type: command-record
      description: "Save the redacted output of an item with no retrieval time being treated as stale rather than fresh."
      path: participant/evidence/context-staleness/attempt-001/logs/missing-timestamp.txt
    - id: proof-narrative
      type: file
      description: "Explain your approach, your choices and anything you could not do, citing the acceptance criteria by number."
      path: participant/evidence/context-staleness/attempt-001/PROOF.md
author: Golden Thread maintainers
last_reviewed: "2026-10-20"
---

# Detect Context Too Old for a Reliable Answer

## Mission

Teach the library how old it is. Every item carries a retrieval time, every answer states the age of what it used, and context past its limit is named instead of quietly relied on.

## Scenario

An agent answers what is blocking the release from a snapshot that is nine days old. The answer is confident, well formatted and wrong.

## Acceptance criteria

1. Every context item records when it was retrieved, shown in the data the runs use.
2. Limits differ by kind of context and are stated with a reason.
3. An answer lists the oldest context it used.
4. An answer relying on stale context says so and names the items.
5. An item with no retrieval time is treated as stale.
6. The clock used for the check can be set so the result is reproducible.
7. Another person can predict from the policy when an answer will be qualified.

## Required evidence

Provide the policy and the run records. In your `PROOF.md`, explain how you set your limits and what the answer does in place of a confident claim, citing the acceptance criteria by number.

## Safety constraints

- Use synthetic work items with invented identifiers; do not use a real project.
- This quest is read-only with respect to every external system, and no live connection is needed.
- Do not hide stale context to make an answer look complete.

## Hints

A fixed clock in the test makes staleness a fact you can reproduce, not a race.

## Reflection

What is the cost of a limit set too tight compared with too loose?

## Stretch goals

- Show a per-field staleness, not only per record.
- Refresh only the items found stale.
