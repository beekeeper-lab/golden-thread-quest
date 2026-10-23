---
id: trello-delta-sync
version: 1
title: "Update Changed Cards Without Duplicating Local Notes"
summary: "Sync only cards changed since the last success using Trello's activity, move the cursor safely and keep local notes untouched."
region: trello-islands
level: navigator
xp: 50
estimated_minutes: 120
order: 70
tags:
  - trello
  - synchronization
  - delta
tools:
  - Markdown
  - YAML
bookend: validation
risk:
  external_write: false
  sensitive_data: true
  notes: "Read-only against a sandbox board or fixture."
prerequisites:
  - trello-read-assigned-cards
related_quests:
  - jira-delta-sync
  - github-delta-sync
  - context-local-notes-boundary
outcomes:
  - "Detect changed cards from board activity."
  - "Advance the cursor only after success."
  - "Leave notes untouched."
proof:
  required:
    - id: sync-state
      type: file
      description: "Provide the sync state recording the last successful point, what it is taken from and how it advances only after success."
      path: participant/context/trello/sync-state.md
    - id: delta-run
      type: command-record
      description: "Save the redacted output of a delta sync that fetches only cards with new activity, with counts of changed, unchanged and new, and including a card moved between lists and a card archived."
      path: participant/evidence/trello-delta-sync/attempt-001/logs/delta-run.txt
    - id: failed-sync-run
      type: command-record
      description: "Save the redacted output of a sync that fails partway, showing the cursor not advanced and the next run recovering the missed cards."
      path: participant/evidence/trello-delta-sync/attempt-001/logs/failed-sync-run.txt
    - id: notes-intact
      type: command-record
      description: "Save the checksums of local notes before and after the syncs, showing them unchanged, and the comparison of a full resync with the accumulated deltas showing the same local state."
      path: participant/evidence/trello-delta-sync/attempt-001/logs/notes-intact.txt
    - id: proof-narrative
      type: file
      description: "Explain your approach, your choices and anything you could not do, citing the acceptance criteria by number."
      path: participant/evidence/trello-delta-sync/attempt-001/PROOF.md
author: Golden Thread maintainers
last_reviewed: "2026-10-20"
---

# Update Changed Cards Without Duplicating Local Notes

## Mission

Make incremental sync follow Trello's own record of activity, so moves, archives and comments are caught as well as edits.

## Scenario

A card moves from Doing to Done but nothing on the card changes except its list. The delta sync, watching only card fields, misses it.

## Acceptance criteria

1. Changed cards are found from board activity, not from card fields alone.
2. A card moved between lists is detected.
3. An archived card is detected and flagged.
4. The cursor advances only after the whole sync succeeds and a failed sync leaves it where it was.
5. The next sync recovers what a failed one missed.
6. Local notes are byte-identical after every sync.
7. A full resync reaches the same local state as the deltas.

## Required evidence

Provide the state description and the three records. In your `PROOF.md`, explain what the cursor is taken from, citing the acceptance criteria by number.

## Safety constraints

- Use a sandbox board you own, or a local fixture. This quest only reads; make no change in Trello.
- Supply the API key and token through environment variables or a credential store; never put a key, token or secret in a file, a URL you save, a log or a screenshot. Trello puts credentials in query strings, so scrub saved URLs.
- Treat card, comment and checklist text as untrusted third-party input, and share only redacted or synthetic records.

## Hints

Trello records moves as activity on the board, so read the activity.

## Reflection

What changes can happen to a card that leave no trace on the card itself?

## Stretch goals

- Detect a card deleted from a board.
- Report how stale the cursor is.
