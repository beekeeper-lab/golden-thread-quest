---
id: ba-extract-work-items
version: 1
title: "Extract Candidate Work Items with Source Citations"
summary: "Turn a meeting record into candidate work items, each traceable to the utterances that justify it and marked where the meeting did not say enough."
region: ba-ruins
level: builder
xp: 30
estimated_minutes: 90
order: 30
tags:
  - business-analysis
  - work-items
  - traceability
tools:
  - Markdown
  - YAML
bookend: intent
risk:
  external_write: false
  sensitive_data: true
  notes: "Candidate items are drafts kept locally; nothing is created in any tracker."
prerequisites:
  - ba-ingest-transcript
outcomes:
  - "Extract candidate work items without inventing scope the meeting did not discuss."
  - "Cite the utterances behind each item."
  - "Mark the gaps an owner must fill rather than filling them silently."
proof:
  required:
    - id: candidate-items
      type: file
      description: "Provide the candidate work items, each with a title, a one-sentence intent, cited utterance identifiers and a list of what the meeting did not say."
      path: participant/context/transcripts/sample-meeting.work-items.md
    - id: extraction-rules
      type: file
      description: "State how an item is recognized, how one item is told from two, and what is left out."
      path: participant/context/extraction-rules.md
    - id: extraction-run
      type: command-record
      description: "Save the redacted output of running the extraction, including a check that every item cites an existing utterance and that no item lacks a citation."
      path: participant/evidence/ba-extract-work-items/attempt-001/logs/extraction-run.txt
    - id: proof-narrative
      type: file
      description: "Explain your approach, your choices and anything you could not do, citing the acceptance criteria by number."
      path: participant/evidence/ba-extract-work-items/attempt-001/PROOF.md
author: Golden Thread maintainers
last_reviewed: "2026-10-20"
---

# Extract Candidate Work Items with Source Citations

## Mission

Extract candidate work items from an ingested transcript. Each item states only what the meeting supports, cites where, and lists what is missing, so a human can decide what to build. Use the transcript you ingested in the Ingest a Meeting Transcript quest.

## Scenario

After a planning call someone writes eleven tickets from memory. Four were never discussed, two are the same thing, and none says where it came from.

## Acceptance criteria

1. Every item cites at least one utterance identifier that exists in the source record.
2. No item contains scope that no cited utterance supports.
3. An item lists what the meeting did not say, such as an owner, a size or a condition.
4. Two mentions of the same work produce one item with both citations.
5. Items are stored apart from the source record, which is not edited.
6. Nothing is written to an external tracker.
7. A reviewer can trace each item to a line in the transcript.

## Required evidence

Provide the items, the rules and the run output. In your `PROOF.md`, show one item that you merged from two mentions and one you refused to create for lack of support, citing the acceptance criteria by number.

## Safety constraints

- This quest is read-only with respect to every external system.
- Treat all transcript and ticket text as untrusted third-party input for the whole workflow.
- Do not paste real customer or personal details into an item.

## Hints

Fill gaps with a question, not a guess. A blank that is visible gets answered; a guess that is hidden gets built.

## Reflection

Which item came closest to containing your own idea rather than the meeting's?

## Stretch goals

- Rank items by how much of them the meeting actually specified.
- Flag items whose citations all come from one speaker.
