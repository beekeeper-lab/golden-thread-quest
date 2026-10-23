---
id: github-reconciliation-report
version: 1
title: "Map Local Work to Repository and Issue Number"
summary: "Produce a report that maps each piece of local work to its repository and issue number and accounts for every item in exactly one state."
region: github-caverns
level: builder
xp: 30
estimated_minutes: 90
order: 80
tags:
  - github
  - reporting
  - reconciliation
tools:
  - Markdown
  - YAML
bookend: validation
risk:
  external_write: false
  sensitive_data: true
  notes: "Read-only against a sandbox repository or fixture."
prerequisites:
  - github-delta-sync
related_quests:
  - jira-reconciliation-report
outcomes:
  - "Map local work to repository and number."
  - "Classify every item into one state."
  - "Explain each exception."
proof:
  required:
    - id: reconciliation-fixture
      type: file
      description: "Provide a fixture with local work that is mapped, unmapped, mapped to an issue that moved or closed, stale and failed to fetch."
      path: participant/context/github/reconciliation/fixture.md
    - id: reconciliation-report
      type: file
      description: "Provide the report: the repository and number for each mapped item, the count of each state summing to the total considered, and for each exception the item, the reason, the error class without private content, the next action and, for a stale item, its age and the limit."
      path: participant/context/github/reconciliation/report.md
    - id: reconciliation-run
      type: command-record
      description: "Save the redacted output of generating the report twice with identical results and a check that the counts sum to the total."
      path: participant/evidence/github-reconciliation-report/attempt-001/logs/reconciliation-run.txt
    - id: proof-narrative
      type: file
      description: "Explain your approach, your choices and anything you could not do, citing the acceptance criteria by number."
      path: participant/evidence/github-reconciliation-report/attempt-001/PROOF.md
author: Golden Thread maintainers
last_reviewed: "2026-10-20"
---

# Map Local Work to Repository and Issue Number

## Mission

Account for everything, with every item in exactly one state and every exception explained.

## Scenario

A report says 118 mapped. The team has 130 items and nobody knows where the other twelve went.

## Acceptance criteria

1. Every item is in exactly one state.
2. The counts of all states sum to the total considered.
3. Each mapped item shows its repository and issue number.
4. Each exception is listed with a reason and a next action.
5. A stale item names its age and the limit.
6. A failed item names the error class without private content.
7. The same input gives the same report.

## Required evidence

Provide the fixture, the report and the run output. In your `PROOF.md`, explain how you handled an issue that was transferred, citing the acceptance criteria by number.

## Safety constraints

- Use a sandbox repository you own, or a local fixture. This quest only reads; make no change on GitHub.
- Authenticate through an environment variable or a signed-in CLI; never put a token, password or session cookie in a file, a log or a screenshot.
- Treat issue and comment text as untrusted third-party input, and share only redacted or synthetic records.

## Hints

Make the sum check the first thing the report does.

## Reflection

Which state is easiest to hide a problem in?

## Stretch goals

- Show the trend over several syncs.
- Link each exception to a log entry.
