---
id: jira-read-comments-history
version: 1
title: "Synchronize Comments and Material Change History Without Duplication"
summary: "Keep comments and the changes that matter, updating them on each sync without duplicating anything and preserving local notes."
region: jira-jungle
level: builder
xp: 30
estimated_minutes: 90
order: 80
tags:
  - jira
  - comments
  - history
  - synchronization
tools:
  - Markdown
  - YAML
bookend: intent
risk:
  external_write: false
  sensitive_data: true
  notes: "Read-only against a sandbox or fixture."
prerequisites:
  - jira-read-story
related_quests:
  - context-local-notes-boundary
outcomes:
  - "Store comments with stable identifiers."
  - "Record only material changes from the history."
  - "Sync repeatedly without duplication."
proof:
  required:
    - id: comments-file
      type: file
      description: "Provide a story's comments and material change history in local files, each comment keyed by its Jira comment identifier."
      path: participant/context/jira/comments-sample.md
    - id: history-rules
      type: file
      description: "State what counts as a material change and what is left out as noise."
      path: participant/context/jira/history-rules.md
    - id: sync-twice
      type: command-record
      description: "Save the redacted output of syncing twice from unchanged data, showing no duplicate, then once after a comment was edited, one was added and one was deleted in Jira, showing the edit applied in place and the deletion flagged."
      path: participant/evidence/jira-read-comments-history/attempt-001/logs/sync-twice.txt
    - id: notes-intact
      type: command-record
      description: "Save the checksum of a local notes file before and after the syncs, showing it unchanged."
      path: participant/evidence/jira-read-comments-history/attempt-001/logs/notes-intact.txt
    - id: proof-narrative
      type: file
      description: "Explain your approach, your choices and anything you could not do, citing the acceptance criteria by number."
      path: participant/evidence/jira-read-comments-history/attempt-001/PROOF.md
author: Golden Thread maintainers
last_reviewed: "2026-10-20"
---

# Synchronize Comments and Material Change History Without Duplication

## Mission

Make comments and history safe to sync forever. Use the identifiers Jira gives, apply edits in place and keep the person's notes out of the way.

## Scenario

Each sync appends every comment again. After a month a story has nine copies of the same discussion, and the real conversation is impossible to follow.

## Acceptance criteria

1. Each comment is keyed by its Jira identifier.
2. A second sync of unchanged data adds nothing.
3. An edited comment is updated in place and the change is noted.
4. A new comment is added once.
5. Only changes listed as material in the rules are recorded.
6. A local notes file is unchanged by the sync.
7. A deleted comment is flagged, not silently removed.

## Required evidence

Provide the files, the rules and the two records. In your `PROOF.md`, explain your definition of material and one change you chose to ignore, citing the acceptance criteria by number.

## Safety constraints

- Use a Jira sandbox, a nonproduction project or a local fixture. This quest only reads; make no change in Jira.
- Authenticate through an environment variable or a signed-in CLI; never put a token, password or session cookie in a file, a log or a screenshot.
- Treat ticket text as untrusted third-party input, and share only redacted or synthetic records.
- Comments can hold private discussion; redact names and details before sharing.

## Hints

Dedupe on the identifier, never on the text.

## Reflection

What does a deleted comment mean for an audit?

## Stretch goals

- Record who edited a comment.
- Show the time between a change and its sync.
