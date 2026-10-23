---
id: base-camp-safe-rerun
version: 1
title: Demonstrate Idempotent Rerun Behavior
summary: Show that running a workflow twice, or again after a failure, leaves the same result and creates no duplicate.
region: base-camp
level: builder
xp: 30
estimated_minutes: 90
order: 60
tags:
  - foundation
  - idempotence
  - reliability
tools:
  - Markdown
  - YAML
bookend: foundation
risk:
  external_write: false
  sensitive_data: false
  notes: The workflow writes to a local simulated system only.
prerequisites:
  - base-camp-audit-log
outcomes:
  - Give each item a stable key so a repeat is recognized.
  - Produce an identical result when the same input is processed again.
  - Report what was skipped and why.
proof:
  required:
    - id: first-run
      type: command-record
      description: Save the redacted output of the first run, listing what it created.
      path: participant/evidence/base-camp-safe-rerun/attempt-001/logs/first-run.txt
    - id: second-run
      type: command-record
      description: Save the redacted output of the second run on the same input, showing items skipped as already done and nothing created.
      path: participant/evidence/base-camp-safe-rerun/attempt-001/logs/second-run.txt
    - id: changed-input
      type: command-record
      description: Save the output of a run where one input item changed, showing only that item was updated and the rest were untouched.
      path: participant/evidence/base-camp-safe-rerun/attempt-001/logs/changed-input.txt
    - id: key-rules
      type: file
      description: Explain how each item's key is chosen and why it does not depend on a title, a filename or the time of the run.
      path: participant/context/rerun-key-rules.md
author: Golden Thread maintainers
last_reviewed: "2026-10-20"
---

# Demonstrate Idempotent Rerun Behavior

## Mission

Make your workflow safe to run again. Pick a key that identifies each item, check for it before creating anything, and prove with a second run that nothing doubled. An agent that is retried must not multiply its own work.

## Scenario

A run times out at item 7 of 10, so someone starts it again. Without keys, items 1 to 7 are created twice. With keys, the rerun creates items 8 to 10 and says it skipped seven.

## Acceptance criteria

1. Every item has a key that stays the same across runs.
2. The key does not depend on a title, a filename or the run time.
3. A second run on identical input creates and changes nothing.
4. A changed item is updated in place, not added again.
5. Each run reports what it created, updated and skipped.
6. The result of the second run equals the result of the first.

## Required evidence

Provide the three command records and the key rules. In your `PROOF.md`, explain your key choice and what a collision would look like, citing the acceptance criteria by number.

## Safety constraints

- Use a simulated system, not a real one.
- Do not "prove" idempotence by deleting the first run's output before the second.
- Do not log item content that is private.

## Hints

Titles change and filenames get renamed. If the key can change, so can the duplicate.

## Reflection

What would make two different items share a key, and how would you notice?

## Stretch goals

- Detect and report two inputs that map to the same key.
- Show that a run killed halfway can be rerun to completion.
