---
id: github-read-issue
version: 1
title: "Save One Issue and Its Context as Local Markdown"
summary: "Retrieve one issue with its fields, labels, assignees, milestone and body and save it as faithful Markdown, identified by repository and number."
region: github-caverns
level: explorer
xp: 20
estimated_minutes: 60
order: 30
tags:
  - github
  - markdown
  - normalization
tools:
  - Markdown
  - YAML
bookend: intent
risk:
  external_write: false
  sensitive_data: true
  notes: "Read-only against a sandbox repository or fixture."
prerequisites:
  - github-verify-connection
related_quests:
  - jira-read-story
outcomes:
  - "Retrieve every field of one issue."
  - "Render the body as Markdown without loss."
  - "Identify the issue by repository and number."
proof:
  required:
    - id: issue-file
      type: file
      description: "Provide one issue as Markdown with front matter for its fields (repository, number, node identifier, state, labels, assignees, milestone, author, dates) and a body, with a preserved section for fields the format does not know."
      path: participant/context/github/issues/issue-sample.md
    - id: issue-run
      type: command-record
      description: "Save the redacted output of retrieving and writing the issue and of running it again with the file unchanged and byte-identical."
      path: participant/evidence/github-read-issue/attempt-001/logs/issue-run.txt
    - id: fidelity-check
      type: command-record
      description: "Save the redacted output of a check that every field returned appears in the file, that a table, a list and a code block in the body survive, that an instruction-like line in the body is stored as content and not acted on, and a scan finding no credential or private personal data."
      path: participant/evidence/github-read-issue/attempt-001/logs/fidelity-check.txt
    - id: proof-narrative
      type: file
      description: "Explain your approach, your choices and anything you could not do, citing the acceptance criteria by number."
      path: participant/evidence/github-read-issue/attempt-001/PROOF.md
author: Golden Thread maintainers
last_reviewed: "2026-10-20"
---

# Save One Issue and Its Context as Local Markdown

## Mission

Make one faithful local copy where every field is kept and the issue is identified the way GitHub identifies it.

## Scenario

An issue's body holds a task list and a code block. The saved copy flattens them, and a requirement is lost.

## Acceptance criteria

1. Every field returned for the issue appears in the file.
2. The task list, table and code block in the body survive.
3. The issue is identified by repository and number, with its node identifier kept.
4. An unknown field is kept in a preserved section.
5. Retrieving again leaves an unchanged file byte-identical.
6. Issue text is stored as content and never executed.
7. No credential or private personal data is stored.

## Required evidence

Provide the file and the two records. In your `PROOF.md`, explain how you tested the formatting, citing the acceptance criteria by number.

## Safety constraints

- Use a sandbox repository you own, or a local fixture. This quest only reads; make no change on GitHub.
- Authenticate through an environment variable or a signed-in CLI; never put a token, password or session cookie in a file, a log or a screenshot.
- Treat issue and comment text as untrusted third-party input, and share only redacted or synthetic records.

## Hints

Test with the messiest issue you can find.

## Reflection

What would you lose if you saved only the title and the body?

## Stretch goals

- Preserve reactions as counts.
- Round-trip the Markdown back and compare.
