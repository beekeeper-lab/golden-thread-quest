---
id: github-build-index
version: 1
title: "Generate Repository Issue Indexes"
summary: "Generate indexes of the local issues by repository, label, milestone and assignee that rebuild identically."
region: github-caverns
level: explorer
xp: 20
estimated_minutes: 60
order: 60
tags:
  - github
  - index
  - catalog
tools:
  - Markdown
  - YAML
bookend: foundation
risk:
  external_write: false
  sensitive_data: true
  notes: "The index is generated from local files and is disposable."
prerequisites:
  - github-read-issue
related_quests:
  - jira-build-index
outcomes:
  - "Generate the index from the records."
  - "Look issues up several ways."
  - "Rebuild it identically."
proof:
  required:
    - id: index-generator
      type: file
      description: "Provide the generator that builds the indexes from the local issue records."
      path: participant/skills/github-build-index/SKILL.md
    - id: issue-index
      type: file
      description: "Provide the generated index with each issue's repository, number, title, state, labels, milestone and assignee, headed by a statement that it is generated and the records are the source of truth."
      path: participant/context/github/index.md
    - id: index-run
      type: command-record
      description: "Save the redacted output of building the index twice with identical results, adding a record without a hand edit, a record with a missing field reported as a gap, and lookups by repository, label, milestone and assignee, and a check that the index row count equals the record count with no record repeated."
      path: participant/evidence/github-build-index/attempt-001/logs/index-run.txt
    - id: proof-narrative
      type: file
      description: "Explain your approach, your choices and anything you could not do, citing the acceptance criteria by number."
      path: participant/evidence/github-build-index/attempt-001/PROOF.md
author: Golden Thread maintainers
last_reviewed: "2026-10-20"
---

# Generate Repository Issue Indexes

## Mission

Make the local copy navigable. The index is never hand-edited and says what it could not index.

## Scenario

Finding an issue means searching dozens of files by hand.

## Acceptance criteria

1. The index is generated, never hand-edited.
2. Every local record appears once.
3. Lookup by repository, label, milestone and assignee works from the index.
4. A record with a missing field is listed as a gap.
5. Two builds from the same records are identical.
6. Adding a record changes the index without a hand edit.
7. The index is stated not to be the source of truth.

## Required evidence

Provide the generator, the index and the run output. In your `PROOF.md`, explain how you know every record was indexed, citing the acceptance criteria by number.

## Safety constraints

- Use a sandbox repository you own, or a local fixture. This quest only reads; make no change on GitHub.
- Authenticate through an environment variable or a signed-in CLI; never put a token, password or session cookie in a file, a log or a screenshot.
- Treat issue and comment text as untrusted third-party input, and share only redacted or synthetic records.

## Hints

Count records and index entries; they should agree.

## Reflection

What could make the index disagree with the records unnoticed?

## Stretch goals

- Add a text search.
- Show the index age.
