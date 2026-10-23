---
id: scrum-release-notes
version: 1
title: "Generate Release Notes and Flag Evidence Gaps"
summary: "Produce release notes from completed work, linking the evidence for each entry and listing entries the evidence does not support."
region: scrum-village
level: builder
xp: 30
estimated_minutes: 90
order: 80
tags:
  - scrum
  - release
  - evidence
tools:
  - Markdown
  - YAML
bookend: validation
risk:
  external_write: false
  sensitive_data: false
  notes: "The release data is synthetic."
prerequisites:
  - base-camp-repository-safety
related_quests:
  - scrum-review-agenda
outcomes:
  - "Draft release notes only from completed work."
  - "Link each note to the evidence that it shipped and works."
  - "Flag notes with no or weak evidence."
proof:
  required:
    - id: release-data
      type: file
      description: "Provide synthetic release data: completed items, items merged but not released, unfinished items, test results, known issues, and a folder of synthetic evidence files, with some items missing evidence."
      path: participant/context/scrum/release/release-data.md
    - id: release-notes
      type: file
      description: "Provide the generated release notes, each entry with its evidence link, a Known issues section and a separate list of flagged entries."
      path: participant/context/scrum/release/release-notes.md
    - id: notes-check
      type: command-record
      description: "Save the redacted output of a check that every entry links an existing evidence file, that no unfinished or merged-but-unreleased item appears, that flagged entries are listed apart, and that generating the notes twice gives identical text."
      path: participant/evidence/scrum-release-notes/attempt-001/logs/notes-check.txt
    - id: proof-narrative
      type: file
      description: "Explain your approach, your choices and anything you could not do, citing the acceptance criteria by number."
      path: participant/evidence/scrum-release-notes/attempt-001/PROOF.md
author: Golden Thread maintainers
last_reviewed: "2026-10-20"
---

# Generate Release Notes and Flag Evidence Gaps

## Mission

Generate release notes you can defend. Each line says what changed for a reader and where the proof is. A line the evidence cannot support goes on a flagged list for a person to resolve before the notes go out.

## Scenario

Release notes say a fix shipped. Support finds out it was merged to a branch that missed the release, a week after customers were told.

## Acceptance criteria

1. Every entry corresponds to a completed work item.
2. Every entry links evidence that exists.
3. No entry reuses its internal work-item title verbatim; each is worded for the reader.
4. Entries with missing or weak evidence are flagged and kept out of the main notes.
5. Known issues are listed separately and not omitted.
6. Generating the notes twice from the same data gives the same text.
7. Each entry says what changed for the reader in one sentence.

## Required evidence

Provide the data, the notes and the check. In your `PROOF.md`, explain what you counted as weak evidence and one entry you moved to the flagged list, citing the acceptance criteria by number.

## Safety constraints

- Use synthetic data with invented names, dates and work items.
- Nothing in this exercise is posted to a tracker, chat channel or email.
- Do not publish the generated notes anywhere.

## Hints

Merged is not shipped. Look for evidence that the change was in the release.

## Reflection

Which kind of evidence would you least want to rely on, and why?

## Stretch goals

- Group entries by audience.
- Show which notes changed since the previous release.
