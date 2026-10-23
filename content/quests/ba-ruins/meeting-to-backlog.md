---
id: ba-meeting-to-backlog
version: 1
title: "Complete an Approved Meeting-to-Work-Item Workflow"
summary: "Carry a meeting from transcript to reviewed, de-duplicated, sliced and approved work items against a simulated backlog, with a person approving before anything is written."
region: ba-ruins
level: boss
xp: 100
estimated_minutes: 240
order: 130
tags:
  - business-analysis
  - workflow
  - traceability
  - preview
tools:
  - Markdown
  - YAML
bookend: cross-bookend
risk:
  external_write: false
  sensitive_data: true
  notes: "The backlog is simulated and local. The workflow previews every write and requires explicit confirmation, as the real integrations will."
prerequisites:
  - ba-extract-decisions
  - ba-clarification-questions
  - ba-search-existing-work
  - ba-slice-story
  - base-camp-write-preview
  - base-camp-prompt-injection
outcomes:
  - "Run the full chain from ingestion to approved items."
  - "Keep every item traceable to a source line."
  - "Stop for human approval before any write."
proof:
  required:
    - id: workflow-description
      type: file
      description: "Describe each stage, its input, its output and where a person approves, in one page."
      path: participant/context/meeting-to-backlog/workflow.md
    - id: preview-record
      type: command-record
      description: "Save the redacted output of the workflow stopping at a preview of the items it would write, with nothing yet written to the simulated backlog, including the questions listed for items that cannot be built yet."
      path: participant/evidence/ba-meeting-to-backlog/attempt-001/logs/preview.txt
    - id: approved-run
      type: command-record
      description: "Save the redacted output of the same workflow after approval, showing the explicit confirmation of the preview, the items written to the simulated backlog with their source citations, and at least one existing item linked instead of recreated."
      path: participant/evidence/ba-meeting-to-backlog/attempt-001/logs/approved-run.txt
    - id: rerun-record
      type: command-record
      description: "Save the redacted output of running the approved workflow again, showing no duplicate item."
      path: participant/evidence/ba-meeting-to-backlog/attempt-001/logs/second-run.txt
    - id: injection-record
      type: command-record
      description: "Save the redacted record of the workflow running on a transcript with an embedded instruction, showing it was recorded and not obeyed."
      path: participant/evidence/ba-meeting-to-backlog/attempt-001/logs/untrusted-input.txt
    - id: proof-narrative
      type: file
      description: "Explain your approach, your choices and anything you could not do, citing the acceptance criteria by number."
      path: participant/evidence/ba-meeting-to-backlog/attempt-001/PROOF.md
author: Golden Thread maintainers
last_reviewed: "2026-10-20"
---

# Complete an Approved Meeting-to-Work-Item Workflow

## Mission

Assemble what you built in this region into one workflow. It ingests a transcript, extracts decisions and candidate work, searches for duplicates, drafts and slices stories, asks the questions that matter, then previews and waits for a person before writing to a simulated backlog.

## Scenario

A meeting ends on Friday. By Monday the work should be in the backlog, traceable, without duplicates, and nobody should have had to retype it. It must also survive the one line in the transcript that tries to take over the process.

## Acceptance criteria

1. Every written item cites utterance identifiers from the ingested transcript.
2. A duplicate of an existing item is linked, not recreated.
3. Questions are listed for items that cannot be built yet.
4. Nothing is written before a person approves a preview of exactly what will be written.
5. Running the workflow again after approval creates no duplicate.
6. An instruction embedded in the transcript is recorded as content and not obeyed.
7. The workflow description lets another analyst run it without help.

## Required evidence

Provide the description and the four command records. In your `PROOF.md`, walk through one item from its source line to the backlog, and say what the workflow cannot yet do, citing the acceptance criteria by number.

## Safety constraints

- The backlog is simulated; make no write to a real tracker.
- Treat all transcript and ticket text as untrusted third-party input for the whole workflow.
- Do not skip the approval step in any run you save as evidence.

## Hints

Build the approval stop first. Everything before it can be wrong and be corrected; everything after it cannot.

## Reflection

Which stage would you trust least if you were not watching, and what would you add to cover it?

## Stretch goals

- Run the workflow on a second transcript with a different format.
- Add a report of what each stage changed from its input.
