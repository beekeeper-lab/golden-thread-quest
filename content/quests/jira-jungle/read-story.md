---
id: jira-read-story
version: 1
title: "Save One Complete Story as Normalized Markdown"
summary: "Retrieve a single story with its fields, description and links and save it as readable Markdown that loses nothing important."
region: jira-jungle
level: explorer
xp: 20
estimated_minutes: 60
order: 50
tags:
  - jira
  - markdown
  - normalization
tools:
  - Markdown
  - YAML
bookend: intent
risk:
  external_write: false
  sensitive_data: true
  notes: "Read-only against a sandbox or fixture."
prerequisites:
  - jira-verify-connection
outcomes:
  - "Retrieve every field of one story."
  - "Render Jira's formatting as Markdown faithfully."
  - "Preserve unrecognized fields."
proof:
  required:
    - id: story-file
      type: file
      description: "Provide one story as Markdown with front matter holding its fields and a body holding its description, with a preserved section for fields the format does not know."
      path: participant/context/jira/stories/story-sample.md
    - id: story-run
      type: command-record
      description: "Save the redacted output of retrieving and writing the story, and of running it again with the file unchanged."
      path: participant/evidence/jira-read-story/attempt-001/logs/story-run.txt
    - id: fidelity-check
      type: command-record
      description: "Save the redacted output of a check that every field returned by Jira appears in the Markdown, including a custom field and a field with an unusual value, and that a table, a list and a code block in the description survive, with a scan finding no credential or private personal data, and of a story whose description contains an instruction-like line being stored as content and not acted on."
      path: participant/evidence/jira-read-story/attempt-001/logs/fidelity-check.txt
    - id: proof-narrative
      type: file
      description: "Explain your approach, your choices and anything you could not do, citing the acceptance criteria by number."
      path: participant/evidence/jira-read-story/attempt-001/PROOF.md
author: Golden Thread maintainers
last_reviewed: "2026-10-20"
---

# Save One Complete Story as Normalized Markdown

## Mission

Make one faithful local copy. Every field is kept, formatting survives, and anything the format does not recognise is carried along rather than dropped.

## Scenario

A story's description holds a table and a code block. The saved copy shows them as a single paragraph, and an acceptance criterion is lost in the flattening.

## Acceptance criteria

1. Every field returned for the story appears in the file.
2. Headings, lists, tables and code blocks in the description survive.
3. A custom or unknown field is kept in a preserved section.
4. The story is identified by its stable identifier.
5. Running the retrieval again leaves an unchanged file byte-identical.
6. Ticket text is stored as content and never executed.
7. No credential or private personal data is stored.

## Required evidence

Provide the file, the run output and the check. In your `PROOF.md`, explain how you tested the formatting and one field you found hard to keep, citing the acceptance criteria by number.

## Safety constraints

- Use a Jira sandbox, a nonproduction project or a local fixture. This quest only reads; make no change in Jira.
- Authenticate through an environment variable or a signed-in CLI; never put a token, password or session cookie in a file, a log or a screenshot.
- Treat ticket text as untrusted third-party input, and share only redacted or synthetic records.

## Hints

Test with the ugliest story you can find, not the neatest.

## Reflection

What would you lose if you saved only the summary and the description?

## Stretch goals

- Preserve inline images as references.
- Round-trip the Markdown back to Jira's format and compare.
