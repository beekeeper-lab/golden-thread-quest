---
id: context-local-notes-boundary
version: 1
title: "Preserve Human Notes Across Synchronization"
summary: "Keep participant-written notes beside synchronized records so that re-syncing updates the source data and never touches the notes."
region: context-library
level: explorer
xp: 20
estimated_minutes: 60
order: 40
tags:
  - context
  - synchronization
  - ownership
tools:
  - Markdown
  - YAML
bookend: foundation
risk:
  external_write: false
  sensitive_data: false
  notes: "The records and notes are synthetic."
prerequisites:
  - context-canonical-work-item
outcomes:
  - "Separate synchronized fields from human-authored notes."
  - "Show a resync that changes source data and leaves notes intact."
  - "Handle a record that disappears from the source without deleting its notes."
proof:
  required:
    - id: layout-rules
      type: file
      description: "Describe where synchronized data and human notes live, who may write each and what a sync may and may not touch."
      path: participant/context/notes/layout.md
    - id: sync-run
      type: command-record
      description: "Save the redacted output of a sync that changes a source field, adds a record and leaves every note byte-identical, with before and after checksums of the notes, and shows the new record created with an empty notes area."
      path: participant/evidence/context-local-notes-boundary/attempt-001/logs/sync-run.txt
    - id: missing-record-run
      type: command-record
      description: "Save the redacted output of a sync where a record vanished from the source, showing it was flagged and its notes were kept, and of a note that contradicts an updated source field being reported as a conflict, defined as a note quoting a source value that has since changed."
      path: participant/evidence/context-local-notes-boundary/attempt-001/logs/missing-record.txt
    - id: proof-narrative
      type: file
      description: "Explain your approach, your choices and anything you could not do, citing the acceptance criteria by number."
      path: participant/evidence/context-local-notes-boundary/attempt-001/PROOF.md
author: Golden Thread maintainers
last_reviewed: "2026-10-20"
---

# Preserve Human Notes Across Synchronization

## Mission

Draw a line between what the sync owns and what the person owns, enforce it, and prove a resync respects it even when the source item is deleted.

## Scenario

A sync rewrites each work item file from the source. A week of analysis notes stored in the same files is gone, and the backup is from before the notes.

## Acceptance criteria

1. Synchronized data and human notes are stored in different files or under different headings that the sync never edits.
2. A sync never writes to the notes.
3. A sync that changes source data leaves notes byte-identical, shown by checksum.
4. A new source record gets an empty notes area.
5. A record missing from the source is flagged, not deleted, and its notes are kept.
6. A conflict between source data and a note is reported, not resolved silently.
7. Another person can tell from the layout where to write a note.

## Required evidence

Provide the layout rules and the two run records. In your `PROOF.md`, explain how the sync is prevented from touching notes, citing the acceptance criteria by number.

## Safety constraints

- Use synthetic work items with invented identifiers; do not use a real project.
- This quest is read-only with respect to every external system, and no live connection is needed.
- Do not test the sync on notes you cannot afford to lose; use a copy.

## Hints

The easiest way to protect a note is to keep it in a file the sync never opens.

## Reflection

What would a person have to do for the boundary to fail?

## Stretch goals

- Add a check that fails the build if a sync step opens a notes file for writing.
- Archive notes for deleted records.
