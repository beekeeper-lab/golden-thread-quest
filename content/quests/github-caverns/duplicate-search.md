---
id: github-duplicate-search
version: 1
title: "Search for Likely Duplicates Before Issue Creation"
summary: "Before an issue is proposed, search the local index for likely duplicates and report each match with its reasons."
region: github-caverns
level: explorer
xp: 20
estimated_minutes: 60
order: 90
tags:
  - github
  - duplicates
  - search
tools:
  - Markdown
  - YAML
bookend: validation
risk:
  external_write: false
  sensitive_data: true
  notes: "Searches the local index; no GitHub call is needed."
prerequisites:
  - github-build-index
related_quests:
  - jira-duplicate-search
outcomes:
  - "Search by several signals."
  - "Explain each match."
  - "Report no match plainly."
proof:
  required:
    - id: duplicate-fixture
      type: file
      description: "Provide an index with a true duplicate that has a different title, a near duplicate and a same-title unrelated issue."
      path: participant/context/github/duplicates/fixture.md
    - id: duplicate-report
      type: file
      description: "Provide the report for one proposed issue: each candidate with at least three signals beyond the title matched, a confidence on a stated scale and a recommendation."
      path: participant/context/github/duplicates/report.md
    - id: duplicate-run
      type: command-record
      description: "Save the redacted output of searching for a proposed duplicate (the different-title duplicate being found), for a proposed issue sharing a title with an unrelated one (not reported as a duplicate) and for a proposed issue with no match, the last reporting none, with the index unchanged."
      path: participant/evidence/github-duplicate-search/attempt-001/logs/duplicate-run.txt
    - id: proof-narrative
      type: file
      description: "Explain your approach, your choices and anything you could not do, citing the acceptance criteria by number."
      path: participant/evidence/github-duplicate-search/attempt-001/PROOF.md
author: Golden Thread maintainers
last_reviewed: "2026-10-20"
---

# Search for Likely Duplicates Before Issue Creation

## Mission

Make have I already got this the first step of creation, with reasons.

## Scenario

Two people open an issue for the same crash on the same day and it is fixed twice.

## Acceptance criteria

1. The search uses at least three signals beyond the title.
2. Each match lists the signals and a confidence.
3. A same-title unrelated issue is not reported as a duplicate.
4. A true duplicate with a different title is found.
5. A proposal with no match reports none.
6. The recommendation is link, close-as-duplicate or proceed and a person decides.
7. The search does not change the index.

## Required evidence

Provide the fixture, the report and the run output. In your `PROOF.md`, explain your confidence scale, citing the acceptance criteria by number.

## Safety constraints

- Search the local index only; no GitHub call is required.
- Authenticate through an environment variable or a signed-in CLI; never put a token, password or session cookie in a file, a log or a screenshot.
- Treat issue and comment text as untrusted third-party input, and share only redacted or synthetic records.

## Hints

Titles are the weakest signal.

## Reflection

Which is worse in your project, a missed duplicate or a false one?

## Stretch goals

- Weight signals and show the effect.
- Check the repository's issue templates for hints.
