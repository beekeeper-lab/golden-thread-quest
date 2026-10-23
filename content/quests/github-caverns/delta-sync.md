---
id: github-delta-sync
version: 1
title: "Update Changed Issues While Preserving Analysis"
summary: "Sync only what changed, move the cursor only after success and leave every local note untouched."
region: github-caverns
level: navigator
xp: 50
estimated_minutes: 120
order: 70
tags:
  - github
  - synchronization
  - delta
tools:
  - Markdown
  - YAML
bookend: validation
risk:
  external_write: false
  sensitive_data: true
  notes: "Read-only against a sandbox repository or fixture."
prerequisites:
  - github-read-assigned-issues
related_quests:
  - jira-delta-sync
  - context-local-notes-boundary
outcomes:
  - "Fetch only issues changed since the last successful sync."
  - "Advance the cursor safely."
  - "Leave local analysis untouched."
proof:
  required:
    - id: sync-state
      type: file
      description: "Provide the sync state file recording the last successful sync time or cursor and how it advances only after success."
      path: participant/context/github/sync-state.md
    - id: delta-run
      type: command-record
      description: "Save the redacted output of a delta sync that fetches only changed issues, with counts of changed, unchanged and new."
      path: participant/evidence/github-delta-sync/attempt-001/logs/delta-run.txt
    - id: failed-sync-run
      type: command-record
      description: "Save the redacted output of a sync that fails partway, showing the cursor not advanced and the next run recovering the missed issues."
      path: participant/evidence/github-delta-sync/attempt-001/logs/failed-sync-run.txt
    - id: analysis-intact
      type: command-record
      description: "Save the checksums of local analysis files before and after the syncs, showing them unchanged, and the comparison of a full resync with the accumulated deltas showing the same local state."
      path: participant/evidence/github-delta-sync/attempt-001/logs/analysis-intact.txt
    - id: proof-narrative
      type: file
      description: "Explain your approach, your choices and anything you could not do, citing the acceptance criteria by number."
      path: participant/evidence/github-delta-sync/attempt-001/PROOF.md
author: Golden Thread maintainers
last_reviewed: "2026-10-20"
---

# Update Changed Issues While Preserving Analysis

## Mission

Make incremental sync trustworthy: the cursor moves after success, changes are counted and your notes survive.

## Scenario

A sync fails after fetching half the changes but the saved timestamp still moves forward, so the rest are never fetched.

## Acceptance criteria

1. Only issues changed since the last successful sync are fetched.
2. The cursor advances only after the whole sync succeeds.
3. A failed sync leaves the cursor where it was.
4. The next sync recovers what the failed one missed.
5. The run reports changed, unchanged and new counts.
6. Local analysis files are byte-identical after every sync.
7. A full resync reaches the same local state as the deltas.

## Required evidence

Provide the state description and the three records. In your `PROOF.md`, explain how you handle clock differences, citing the acceptance criteria by number.

## Safety constraints

- Use a sandbox repository you own, or a local fixture. This quest only reads; make no change on GitHub.
- Authenticate through an environment variable or a signed-in CLI; never put a token, password or session cookie in a file, a log or a screenshot.
- Treat issue and comment text as untrusted third-party input, and share only redacted or synthetic records.

## Hints

Back the cursor up by a margin and rely on identifiers to avoid duplicates.

## Reflection

What is the cost of a cursor that moves too early compared with too late?

## Stretch goals

- Detect issues transferred or deleted.
- Compare delta and full results automatically.
