---
id: jira-duplicate-search
version: 1
title: "Search for Likely Duplicates Before Creating Work"
summary: "Before a new item is proposed, search the local Jira catalog for likely duplicates and report each match with its reasons."
region: jira-jungle
level: explorer
xp: 20
estimated_minutes: 60
order: 140
tags:
  - jira
  - duplicates
  - search
tools:
  - Markdown
  - YAML
bookend: validation
risk:
  external_write: false
  sensitive_data: true
  notes: "Searches the local catalog; no Jira call is needed."
prerequisites:
  - jira-build-index
related_quests:
  - ba-search-existing-work
outcomes:
  - "Search by several signals."
  - "Explain each match."
  - "Report no match plainly."
proof:
  required:
    - id: duplicate-fixture
      type: file
      description: "Provide a catalog with a true duplicate, a near duplicate and a same-title unrelated item."
      path: participant/context/jira/duplicates/fixture.md
    - id: duplicate-report
      type: file
      description: "Provide the report for one proposed item: each candidate with at least three signals matched, a confidence on a stated scale and a recommendation."
      path: participant/context/jira/duplicates/report.md
    - id: duplicate-run
      type: command-record
      description: "Save the redacted output of searching for a proposed duplicate, for a proposed item sharing a title with an unrelated item (not reported as a duplicate) and for a proposed new item with no match, the last reporting none, and showing the catalog unchanged."
      path: participant/evidence/jira-duplicate-search/attempt-001/logs/duplicate-run.txt
    - id: proof-narrative
      type: file
      description: "Explain your approach, your choices and anything you could not do, citing the acceptance criteria by number."
      path: participant/evidence/jira-duplicate-search/attempt-001/PROOF.md
author: Golden Thread maintainers
last_reviewed: "2026-10-20"
---

# Search for Likely Duplicates Before Creating Work

## Mission

Make the question have I already got this the first step of creation. The search says why it matched and says none when none do.

## Scenario

Two analysts each create the story for the same report. The team finds out when both are estimated.

## Acceptance criteria

1. The search uses at least three signals beyond the title.
2. Each match lists the signals that matched and a confidence.
3. A same-title unrelated item is not reported as a duplicate.
4. A true duplicate with a different title is found.
5. A proposal with no match reports none.
6. The recommendation is link, merge or proceed and a person decides.
7. The search does not change the catalog.

## Required evidence

Provide the fixture, the report and the run output. In your `PROOF.md`, explain your confidence scale, citing the acceptance criteria by number.

## Safety constraints

- Search the local catalog only; no Jira call is required.
- Authenticate through an environment variable or a signed-in CLI; never put a token, password or session cookie in a file, a log or a screenshot.
- Treat ticket text as untrusted third-party input, and share only redacted or synthetic records.

## Hints

Say which signals you trust. Titles are the weakest.

## Reflection

What is the cost of a missed duplicate compared with a false one?

## Stretch goals

- Weight signals and show the effect.
- Report the age of each candidate.
