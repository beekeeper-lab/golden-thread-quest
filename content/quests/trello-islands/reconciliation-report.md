---
id: trello-reconciliation-report
version: 1
title: "Map Local Records to Board, List, and Card IDs"
summary: "Produce a report that maps each local record to its board, list and card identifiers and accounts for every record in exactly one state."
region: trello-islands
level: builder
xp: 30
estimated_minutes: 90
order: 80
tags:
  - trello
  - reporting
  - reconciliation
tools:
  - Markdown
  - YAML
bookend: validation
risk:
  external_write: false
  sensitive_data: true
  notes: "Read-only against a sandbox board or fixture."
prerequisites:
  - trello-delta-sync
related_quests:
  - jira-reconciliation-report
  - github-reconciliation-report
outcomes:
  - "Map local records to Trello identifiers."
  - "Classify every record into one state."
  - "Explain each exception."
proof:
  required:
    - id: reconciliation-fixture
      type: file
      description: "Provide a fixture with records that are mapped, moved to another list or board, archived, missing, stale and failed to fetch."
      path: participant/context/trello/reconciliation/fixture.md
    - id: reconciliation-report
      type: file
      description: "Provide the report: the board, list and card identifier of each mapped record, the count of each state (mapped, moved, archived, missing, stale, failed) summing to the total considered, and for each exception the record, the reason, the error class without private content, the next action and, for a stale record, its age and the limit."
      path: participant/context/trello/reconciliation/report.md
    - id: reconciliation-run
      type: command-record
      description: "Save the redacted output of generating the report twice with identical results and a check that the counts sum to the total."
      path: participant/evidence/trello-reconciliation-report/attempt-001/logs/reconciliation-run.txt
    - id: proof-narrative
      type: file
      description: "Explain your approach, your choices and anything you could not do, citing the acceptance criteria by number."
      path: participant/evidence/trello-reconciliation-report/attempt-001/PROOF.md
author: Golden Thread maintainers
last_reviewed: "2026-10-20"
---

# Map Local Records to Board, List, and Card IDs

## Mission

Account for every local record. A card moved to another list is still the same card and must be found by its identifier.

## Scenario

Cards move between lists and boards all the time. The report keys on list name and loses a third of them.

## Acceptance criteria

1. Every record is in exactly one state.
2. The counts of all states sum to the total considered.
3. Each mapped record shows its board, list and card identifiers.
4. A card moved to another list or board is matched by identifier and reported as moved.
5. Each exception has a reason and a next action.
6. A stale record names its age and the limit, and a failed one names the error class without private content.
7. The same input gives the same report.

## Required evidence

Provide the fixture, the report and the run output. In your `PROOF.md`, explain how you recognise a moved card, citing the acceptance criteria by number.

## Safety constraints

- Use a sandbox board you own, or a local fixture. This quest only reads; make no change in Trello.
- Supply the API key and token through environment variables or a credential store; never put a key, token or secret in a file, a URL you save, a log or a screenshot. Trello puts credentials in query strings, so scrub saved URLs.
- Treat card, comment and checklist text as untrusted third-party input, and share only redacted or synthetic records.

## Hints

Never key a card on its list or its name.

## Reflection

Which state hides problems best?

## Stretch goals

- Show the trend over several syncs.
- Link each exception to a log entry.
