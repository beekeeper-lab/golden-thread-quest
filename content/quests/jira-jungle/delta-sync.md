---
id: jira-delta-sync
version: 1
title: "Update Only Changed Work While Preserving Local Analysis"
summary: "Sync only what changed since last time, record what changed, and keep every local note and analysis file untouched."
region: jira-jungle
level: navigator
xp: 50
estimated_minutes: 120
order: 110
tags:
  - jira
  - synchronization
  - delta
tools:
  - Markdown
  - YAML
bookend: validation
risk:
  external_write: false
  sensitive_data: true
  notes: "Read-only against a sandbox or fixture."
prerequisites:
  - jira-read-assigned-stories
outcomes:
  - "Fetch only items changed since the last successful sync."
  - "Record the cursor safely."
  - "Leave local analysis untouched."
proof:
  required:
    - id: sync-state
      type: file
      description: "Provide the sync state file recording the last successful sync time or cursor and how it is updated only after success."
      path: participant/context/jira/sync-state.md
    - id: delta-run
      type: command-record
      description: "Save the redacted output of a delta sync that fetches only changed items, showing counts of changed, unchanged and new items."
      path: participant/evidence/jira-delta-sync/attempt-001/logs/delta-run.txt
    - id: failed-sync-run
      type: command-record
      description: "Save the redacted output of a sync that fails partway, showing the cursor was not advanced and the next run recovered the missed items."
      path: participant/evidence/jira-delta-sync/attempt-001/logs/failed-sync-run.txt
    - id: analysis-intact
      type: command-record
      description: "Save the checksums of local analysis files before and after the syncs, showing them unchanged, and the comparison of a full resync with the accumulated deltas showing the same local state."
      path: participant/evidence/jira-delta-sync/attempt-001/logs/analysis-intact.txt
    - id: proof-narrative
      type: file
      description: "Explain your approach, your choices and anything you could not do, citing the acceptance criteria by number."
      path: participant/evidence/jira-delta-sync/attempt-001/PROOF.md
author: Golden Thread maintainers
last_reviewed: "2026-10-20"
---

# Update Only Changed Work While Preserving Local Analysis

## Mission

Make incremental sync trustworthy. The cursor moves only after success, changes are counted, and nothing you wrote locally is overwritten.

## Scenario

A sync fails after fetching half the changes, but the saved timestamp still moves forward. The missing changes are never fetched again.

## Acceptance criteria

1. Only items changed since the last successful sync are fetched.
2. The cursor advances only after the whole sync succeeds.
3. A failed sync leaves the cursor where it was.
4. The next sync recovers the items the failed one missed.
5. The run reports changed, unchanged and new counts.
6. Local analysis files are byte-identical after every sync.
7. A full resync reaches the same local state as the deltas.

## Required evidence

Provide the state description and the three records. In your `PROOF.md`, explain how clock differences between machines are handled, citing the acceptance criteria by number.

## Safety constraints

- Use a Jira sandbox, a nonproduction project or a local fixture. This quest only reads; make no change in Jira.
- Authenticate through an environment variable or a signed-in CLI; never put a token, password or session cookie in a file, a log or a screenshot.
- Treat ticket text as untrusted third-party input, and share only redacted or synthetic records.

## Hints

Back up the cursor by a safety margin and rely on identifiers to avoid duplicates.

## Reflection

What is the cost of a cursor that moves too early compared with too late?

## Stretch goals

- Detect items deleted in Jira.
- Compare a delta result against a full resync automatically.
