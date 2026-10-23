---
id: ba-slice-story
version: 1
title: "Split Oversized Work into Independently Valuable Increments"
summary: "Divide a large story into slices that each deliver value on their own, in an order that can be released one at a time."
region: ba-ruins
level: navigator
xp: 50
estimated_minutes: 120
order: 90
tags:
  - business-analysis
  - stories
  - slicing
tools:
  - Markdown
  - YAML
bookend: intent
risk:
  external_write: false
  sensitive_data: false
  notes: "Use a synthetic oversized story."
prerequisites:
  - ba-write-story
outcomes:
  - "Slice by value, not by technical layer."
  - "Show each slice can ship alone."
  - "Show nothing was lost or duplicated in the split."
proof:
  required:
    - id: oversized-story
      type: file
      description: "Provide a synthetic story too large to finish in one iteration, with its criteria."
      path: participant/context/slicing/original-story.md
    - id: slices
      type: file
      description: "Provide the slices, each with its value, criteria, dependencies and the original criteria it covers."
      path: participant/context/slicing/slices.md
    - id: coverage-check
      type: command-record
      description: "Save the redacted output of a check that every original criterion is covered by exactly one slice and that no slice depends on a later one."
      path: participant/evidence/ba-slice-story/attempt-001/logs/coverage-check.txt
    - id: proof-narrative
      type: file
      description: "Explain your approach, your choices and anything you could not do, citing the acceptance criteria by number."
      path: participant/evidence/ba-slice-story/attempt-001/PROOF.md
author: Golden Thread maintainers
last_reviewed: "2026-10-20"
---

# Split Oversized Work into Independently Valuable Increments

## Mission

Slice a large story into increments that each deliver something a user would notice. Show that together they cover the original, and that each can be released without the ones after it.

## Scenario

A story called Build the reporting module takes four sprints and ships nothing until the last day. The first month of it could have been in use.

## Acceptance criteria

1. Each slice states the value it delivers on its own.
2. Slices are cut by user-visible value, not by technical layer.
3. Every original criterion is covered by exactly one slice.
4. No slice depends on a slice that comes after it.
5. The first slice can be released alone.
6. Nothing is added that the original story did not contain.
7. A reviewer can recompute the coverage from the files.

## Required evidence

Provide the original, the slices and the coverage check. In your `PROOF.md`, explain how you chose the first slice and one slicing you rejected, citing the acceptance criteria by number.

## Safety constraints

- Use only a synthetic story.
- Do not claim a slice is releasable without saying what it relies on.

## Hints

A slice called the database is a layer. A slice called a user can save one report is a slice.

## Reflection

Which slice would stakeholders ask to drop, and what would that cost the others?

## Stretch goals

- Order the slices by value and risk and justify the order.
- Find a dependency that forces two slices to ship together.
