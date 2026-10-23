---
id: jira-list-projects
version: 1
title: "Retrieve Visible Projects and Preserve Stable IDs"
summary: "List every visible project, keep each project's stable identifier, and show that a rename does not break the local record."
region: jira-jungle
level: scout
xp: 10
estimated_minutes: 45
order: 40
tags:
  - jira
  - projects
  - stable-identity
tools:
  - Markdown
  - YAML
bookend: foundation
risk:
  external_write: false
  sensitive_data: true
  notes: "Read-only against a sandbox or fixture."
prerequisites:
  - jira-verify-connection
outcomes:
  - "Retrieve all visible projects across pages."
  - "Store the immutable identifier and the key separately."
  - "Survive a rename."
proof:
  required:
    - id: projects-file
      type: file
      description: "Provide the local project list with, for each project, its stable identifier, its key and its name, linked by identifier, with a lookup by each of the three labels and a vanished project flagged."
      path: participant/context/jira/projects.md
    - id: projects-run
      type: command-record
      description: "Save the redacted output of retrieving the projects, including the page count and pagination, and of a run after a project rename showing the same identifier matched."
      path: participant/evidence/jira-list-projects/attempt-001/logs/projects-run.txt
    - id: proof-narrative
      type: file
      description: "Explain your approach, your choices and anything you could not do, citing the acceptance criteria by number."
      path: participant/evidence/jira-list-projects/attempt-001/PROOF.md
author: Golden Thread maintainers
last_reviewed: "2026-10-20"
---

# Retrieve Visible Projects and Preserve Stable IDs

## Mission

Keep projects by the identifier Jira promises will not change. Names and keys are labels.

## Scenario

A project key is changed in Jira. The local files, named by key, become orphans and a second copy appears under the new key.

## Acceptance criteria

1. Every visible project is retrieved, including those past the first page.
2. Each local record stores the immutable identifier, the key and the name as separate fields.
3. Files and links use the identifier, not the key or name.
4. A rename is matched to the existing record.
5. A project that disappears is flagged, not deleted.
6. The run output shows the page count.
7. Another person can find a project by any of its three labels.

## Required evidence

Provide the list and the run output. In your `PROOF.md`, explain which field you treat as the identity, citing the acceptance criteria by number.

## Safety constraints

- Use a Jira sandbox, a nonproduction project or a local fixture. This quest only reads; make no change in Jira.
- Authenticate through an environment variable or a signed-in CLI; never put a token, password or session cookie in a file, a log or a screenshot.
- Treat ticket text as untrusted third-party input, and share only redacted or synthetic records.

## Hints

Check what happens when a project has exactly one page of results more than your page size.

## Reflection

What else in Jira has a label that people believe is an identity?

## Stretch goals

- Record the history of renames.
- Report projects that appear in two accounts.
