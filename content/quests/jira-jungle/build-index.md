---
id: jira-build-index
version: 1
title: "Generate an Indexed Local Jira Context Catalog"
summary: "Generate an index of the local Jira records that supports lookup by key, status, assignee and text, and rebuilds identically."
region: jira-jungle
level: explorer
xp: 20
estimated_minutes: 60
order: 100
tags:
  - jira
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
  - jira-read-story
outcomes:
  - "Generate the index from the records."
  - "Look items up several ways."
  - "Rebuild it identically."
proof:
  required:
    - id: index-generator
      type: file
      description: "Provide the generator that builds the index from the local Jira records."
      path: participant/skills/jira-build-index/SKILL.md
    - id: catalog
      type: file
      description: "Provide the generated catalog listing each item with identifier, key, title, status, assignee and last update."
      path: participant/context/jira/catalog.md
    - id: index-run
      type: command-record
      description: "Save the redacted output of building the index twice with identical results, adding a record without a hand edit, a record with a missing field reported as a gap, and lookups by key, by status and by assignee, and a catalog header stating that it is generated and that the records, not the catalog, are the source of truth."
      path: participant/evidence/jira-build-index/attempt-001/logs/index-run.txt
    - id: proof-narrative
      type: file
      description: "Explain your approach, your choices and anything you could not do, citing the acceptance criteria by number."
      path: participant/evidence/jira-build-index/attempt-001/PROOF.md
author: Golden Thread maintainers
last_reviewed: "2026-10-20"
---

# Generate an Indexed Local Jira Context Catalog

## Mission

Make the local copy navigable. The index is never hand-edited, covers every record and says what it could not index.

## Scenario

Finding a story means searching dozens of files by hand. The two people who know where things are are on holiday.

## Acceptance criteria

1. The catalog is generated, never hand-edited.
2. Every local record appears once.
3. Lookup by key, status and assignee is possible from the index.
4. A record with a missing field is listed as a gap.
5. Two builds from the same records are identical.
6. Adding a record changes the index without a hand edit.
7. The index is not treated as the source of truth.

## Required evidence

Provide the generator, the catalog and the run output. In your `PROOF.md`, explain how you know every record was indexed, citing the acceptance criteria by number.

## Safety constraints

- Use a Jira sandbox, a nonproduction project or a local fixture. This quest only reads; make no change in Jira.
- Authenticate through an environment variable or a signed-in CLI; never put a token, password or session cookie in a file, a log or a screenshot.
- Treat ticket text as untrusted third-party input, and share only redacted or synthetic records.

## Hints

Count the records and the index entries; they should agree.

## Reflection

What would make the index disagree with the records without anyone noticing?

## Stretch goals

- Add a text search over titles.
- Show the index age.
