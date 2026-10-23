---
id: base-camp-interruption-recovery
version: 1
title: Stop and Resume Without Corruption or Duplication
summary: Interrupt a workflow partway through, then resume it and show no file is half-written and no work is repeated.
region: base-camp
level: builder
xp: 30
estimated_minutes: 90
order: 70
tags:
  - foundation
  - recovery
  - reliability
tools:
  - Markdown
  - YAML
bookend: foundation
risk:
  external_write: false
  sensitive_data: false
  notes: The workflow writes only local files, so an interruption cannot damage an outside system.
prerequisites:
  - base-camp-safe-rerun
outcomes:
  - Write files so that an interruption leaves the old version or the new one, never a mixture.
  - Record progress so a resumed run continues from where it stopped.
  - Show the state after an interruption and after recovery.
proof:
  required:
    - id: interrupted-run
      type: command-record
      description: Save the output of a run stopped partway, followed by a listing showing no partial or temporary file left looking complete.
      path: participant/evidence/base-camp-interruption-recovery/attempt-001/logs/interrupted.txt
    - id: resumed-run
      type: command-record
      description: Save the output of the resumed run, showing which items it skipped as done and which it completed, and a checksum comparison of its result with an uninterrupted run's.
      path: participant/evidence/base-camp-interruption-recovery/attempt-001/logs/resumed.txt
    - id: recovery-notes
      type: file
      description: Explain how a file is written safely, where progress is recorded, and how a person can tell a run was interrupted.
      path: participant/context/recovery-notes.md
author: Golden Thread maintainers
last_reviewed: "2026-10-20"
---

# Stop and Resume Without Corruption or Duplication

## Mission

Make an interruption boring. Stop your workflow on purpose, look at what it left behind, then resume it. The files must be whole, the progress record must be honest, and the resumed run must not redo finished work.

## Scenario

A laptop sleeps in the middle of a run. The next morning one output file is half-written but looks complete, and a later step builds on it.

## Acceptance criteria

1. Output is written so that an interruption leaves the previous complete file or the new complete file.
2. A temporary or partial file is never left under the final name.
3. Progress is recorded durably as each item finishes.
4. A resumed run skips finished items and completes the rest.
5. The resumed result equals an uninterrupted run's result.
6. A person can tell from the output that a run was interrupted and how it recovered.

## Required evidence

Provide the interrupted and resumed records and the notes. In your `PROOF.md`, explain how you stopped the run and how you know the result equals an uninterrupted one, citing the acceptance criteria by number.

## Safety constraints

- Interrupt only your own sandbox workflow.
- Do not simulate a crash by killing an unrelated process.
- Do not recover by deleting the progress record and starting over.

## Hints

Write to a temporary name in the same folder, then rename it into place. The rename is the moment the file becomes real.

## Reflection

What could still go wrong if the interruption came during the rename, or while writing the progress record?

## Stretch goals

- Hold a lock so two runs cannot overlap.
- Interrupt at three different points and show each recovers.
