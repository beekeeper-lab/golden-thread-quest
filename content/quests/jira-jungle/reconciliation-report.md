---
id: jira-reconciliation-report
version: 1
title: "Explain Synchronized, Missing, Stale, Conflicted, and Failed Items"
summary: "Produce a sync report that accounts for every item in exactly one state and explains each one that is not simply in sync."
region: jira-jungle
level: builder
xp: 30
estimated_minutes: 90
order: 130
tags:
  - jira
  - reporting
  - reconciliation
tools:
  - Markdown
  - YAML
bookend: validation
risk:
  external_write: false
  sensitive_data: true
  notes: "Read-only against a sandbox or fixture."
prerequisites:
  - jira-delta-sync
  - jira-detect-conflicts
outcomes:
  - "Classify every item into one state."
  - "Explain each exception."
  - "Make the totals add up."
proof:
  required:
    - id: reconciliation-fixture
      type: file
      description: "Provide a fixture with items that are synchronized, missing from Jira, stale, conflicted and failed to fetch."
      path: participant/context/jira/reconciliation/fixture.md
    - id: reconciliation-report
      type: file
      description: "Provide the report: the count of each state, a total equal to the number of items considered and, for each exception, the item, the reason, the error class without private content, the next action and, for a stale item, its age and the limit."
      path: participant/context/jira/reconciliation/report.md
    - id: reconciliation-run
      type: command-record
      description: "Save the redacted output of generating the report twice with identical results and a check that the state counts sum to the total."
      path: participant/evidence/jira-reconciliation-report/attempt-001/logs/reconciliation-run.txt
    - id: proof-narrative
      type: file
      description: "Explain your approach, your choices and anything you could not do, citing the acceptance criteria by number."
      path: participant/evidence/jira-reconciliation-report/attempt-001/PROOF.md
author: Golden Thread maintainers
last_reviewed: "2026-10-20"
---

# Explain Synchronized, Missing, Stale, Conflicted, and Failed Items

## Mission

Account for everything. Every item is in exactly one state, the numbers add up, and every exception says why.

## Scenario

A report says 118 synchronized. The team has 130 items. Nobody knows where the other twelve went.

## Acceptance criteria

1. Every item is in exactly one state.
2. The counts of all states sum to the total considered.
3. Each missing, stale, conflicted or failed item is listed with a reason.
4. A stale item names its age and the limit.
5. A failed item names the error class without private content.
6. The same input gives the same report.
7. A reader can tell what to do next for each exception.

## Required evidence

Provide the fixture, the report and the run output. In your `PROOF.md`, explain how you chose between two states for an item that fit both, citing the acceptance criteria by number.

## Safety constraints

- Use a Jira sandbox, a nonproduction project or a local fixture. This quest only reads; make no change in Jira.
- Authenticate through an environment variable or a signed-in CLI; never put a token, password or session cookie in a file, a log or a screenshot.
- Treat ticket text as untrusted third-party input, and share only redacted or synthetic records.

## Hints

Make the check that the counts sum to the total the first thing the report does.

## Reflection

Which state is easiest to hide a problem in?

## Stretch goals

- Show the trend over the last five syncs.
- Link each exception to the log entry that explains it.
