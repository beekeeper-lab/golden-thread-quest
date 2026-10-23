---
id: github-read-comments-events
version: 1
title: "Preserve Comments and Material Timeline Events"
summary: "Keep comments and the timeline events that matter, such as label, assignment and state changes, updating on each sync without duplication."
region: github-caverns
level: builder
xp: 30
estimated_minutes: 90
order: 50
tags:
  - github
  - comments
  - timeline
  - synchronization
tools:
  - Markdown
  - YAML
bookend: intent
risk:
  external_write: false
  sensitive_data: true
  notes: "Read-only against a sandbox repository or fixture."
prerequisites:
  - github-read-issue
related_quests:
  - jira-read-comments-history
outcomes:
  - "Key comments and events by GitHub identifiers."
  - "Record only material events."
  - "Sync repeatedly without duplication."
proof:
  required:
    - id: comments-file
      type: file
      description: "Provide an issue's comments and material timeline events in local files, each keyed by its GitHub identifier."
      path: participant/context/github/comments-sample.md
    - id: event-rules
      type: file
      description: "State which timeline events are material and which are noise, with the reason for each."
      path: participant/context/github/event-rules.md
    - id: sync-twice
      type: command-record
      description: "Save the redacted output of syncing twice from unchanged data with nothing duplicated, then once after a comment was edited, one was added and one was deleted on GitHub, showing the edit applied in place and the deletion flagged."
      path: participant/evidence/github-read-comments-events/attempt-001/logs/sync-twice.txt
    - id: notes-intact
      type: command-record
      description: "Save the checksum of a local notes file before and after the syncs, showing it unchanged."
      path: participant/evidence/github-read-comments-events/attempt-001/logs/notes-intact.txt
    - id: proof-narrative
      type: file
      description: "Explain your approach, your choices and anything you could not do, citing the acceptance criteria by number."
      path: participant/evidence/github-read-comments-events/attempt-001/PROOF.md
author: Golden Thread maintainers
last_reviewed: "2026-10-20"
---

# Preserve Comments and Material Timeline Events

## Mission

Make comments and events safe to sync forever by keying them on the identifiers GitHub gives.

## Scenario

Each sync appends every comment again, and a month later an issue holds nine copies of one discussion.

## Acceptance criteria

1. Each comment and event is keyed by its GitHub identifier.
2. A second sync of unchanged data adds nothing.
3. An edited comment is updated in place.
4. A new comment is added once.
5. Only events the rules call material are recorded.
6. A local notes file is unchanged by the sync.
7. A deleted comment is flagged, not silently removed.

## Required evidence

Provide the files, the rules and the two records. In your `PROOF.md`, explain one event you chose to ignore, citing the acceptance criteria by number.

## Safety constraints

- Use a sandbox repository you own, or a local fixture. This quest only reads; make no change on GitHub.
- Authenticate through an environment variable or a signed-in CLI; never put a token, password or session cookie in a file, a log or a screenshot.
- Treat issue and comment text as untrusted third-party input, and share only redacted or synthetic records.
- Comments can hold private discussion; redact before sharing.

## Hints

Dedupe on the identifier, never on the text.

## Reflection

What does a deleted comment mean for an audit?

## Stretch goals

- Record who edited a comment.
- Show the delay between an event and its sync.
