---
id: ba-search-existing-work
version: 1
title: "Search for Related and Duplicate Work Before Creating It"
summary: "Before proposing new work, search local context for related and duplicate items and report matches with the reason each was matched."
region: ba-ruins
level: builder
xp: 30
estimated_minutes: 90
order: 70
tags:
  - business-analysis
  - duplicates
  - context
tools:
  - Markdown
  - YAML
bookend: validation
risk:
  external_write: false
  sensitive_data: false
  notes: "The search reads a local synthetic catalog; no tracker is queried."
prerequisites:
  - base-camp-repository-safety
outcomes:
  - "Search a local catalog of work by meaning and by key facts, not only by title."
  - "Explain each match."
  - "Recommend link, merge or proceed without deciding for the human."
proof:
  required:
    - id: catalog
      type: file
      description: "Provide a synthetic catalog of at least fifteen work items, including a true duplicate, a near duplicate and some related but distinct items."
      path: participant/context/search/catalog.md
    - id: search-report
      type: file
      description: "Provide a report for one proposed item listing each match, the fields that matched, a confidence and a recommendation."
      path: participant/context/search/report.md
    - id: search-run
      type: command-record
      description: "Save the redacted output of the search for a proposed duplicate and for a proposed new item with no match, showing the second reports no match instead of forcing one."
      path: participant/evidence/ba-search-existing-work/attempt-001/logs/search-run.txt
    - id: proof-narrative
      type: file
      description: "Explain your approach, your choices and anything you could not do, citing the acceptance criteria by number."
      path: participant/evidence/ba-search-existing-work/attempt-001/PROOF.md
author: Golden Thread maintainers
last_reviewed: "2026-10-20"
---

# Search for Related and Duplicate Work Before Creating It

## Mission

Build a pre-creation search that looks for related and duplicate work, shows why it matched, and says plainly when nothing matches.

## Scenario

Two teams each create a story for the same export feature in the same sprint. Both were built, and the second had to be thrown away.

## Acceptance criteria

1. The search considers more than the title, such as description, component and cited source.
2. Each match states which fields matched and how strongly.
3. A true duplicate is found and a distinct but related item is labeled related, not duplicate.
4. A proposal with no match reports none instead of returning the closest guess.
5. The recommendation is link, merge or proceed, and the human decides.
6. Running the search does not change the catalog.
7. A reviewer can see why each result was returned.

## Required evidence

Provide the catalog, the report and the run output. In your `PROOF.md`, explain how you tell a duplicate from a related item, citing the acceptance criteria by number.

## Safety constraints

- Use only a synthetic catalog.
- Do not query a real tracker.

## Hints

Two items can share a title and be different, or share nothing visible and be the same. Say which signals you trusted.

## Reflection

What does a false duplicate cost compared with a missed one?

## Stretch goals

- Tune a threshold and show the effect on your catalog.
- Report items that look related to several others.
