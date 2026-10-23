---
id: base-camp-audit-log
version: 1
title: Record Read, Preview, Confirmed Write, Failure, and Recovery Events
summary: Keep an append-only log that lets a stranger reconstruct what an agent did, who asked, and what happened.
region: base-camp
level: explorer
xp: 20
estimated_minutes: 60
order: 50
tags:
  - foundation
  - audit
  - traceability
tools:
  - Markdown
  - YAML
bookend: foundation
risk:
  external_write: false
  sensitive_data: false
  notes: Log entries name targets and outcomes, never credentials or the content of private records.
prerequisites:
  - base-camp-repository-safety
outcomes:
  - Define the fields every audit entry carries and the five event kinds.
  - Write entries for a read, a preview, a confirmed write, a failure and a recovery.
  - Show that the log is append-only and holds no secret.
proof:
  required:
    - id: log-format
      type: file
      description: Define the entry fields and the five event kinds, with one example of each.
      path: participant/context/audit-log-format.md
    - id: sample-log
      type: file
      description: Provide a log produced by running a workflow that includes all five event kinds.
      path: participant/context/audit-log-all-events.md
    - id: append-check
      type: command-record
      description: Save the output of an attempt to edit or delete an earlier entry being refused or detected, with the log unchanged afterwards.
      path: participant/evidence/base-camp-audit-log/attempt-001/logs/append-only.txt
author: Golden Thread maintainers
last_reviewed: "2026-10-20"
---

# Record Read, Preview, Confirmed Write, Failure, and Recovery Events

## Mission

Design the log you will want when something goes wrong. A good entry answers when, what, on what, who asked, what came of it and whether a person confirmed it, and it cannot be quietly rewritten afterwards.

## Scenario

A ticket has the wrong assignee and nobody knows whether a person or the agent changed it, or when. Without a log, the only record is each participant's memory.

## Acceptance criteria

1. Each entry has a time, action, target, initiating actor, outcome and confirmation status.
2. The log covers reads, previews, confirmed writes, failures and recoveries.
3. A failure entry gives the reason without quoting private content.
4. Earlier entries are not edited or removed; a correction is a new entry.
5. The log contains no credential or private record body.
6. Another person can reconstruct the order of events from the log alone.

## Required evidence

Provide the format, a log containing all five event kinds, and the append-only check. In your `PROOF.md`, explain how you detect or prevent edits to earlier entries, citing the acceptance criteria by number.

## Safety constraints

- Log targets by identifier, not by copying their private content.
- Do not log a credential, even masked in part.
- Use simulated work for the sample.

## Hints

Writing "success" is easy. The failures and recoveries are the entries that earn the log its place.

## Reflection

What question about last week's work could your log not answer?

## Stretch goals

- Add a check that fails on a missing or out-of-order timestamp.
- Link each confirmed write to the preview it came from.
