---
id: jira-create-story-preview
version: 1
title: "Preview a Complete New Story Without Writing"
summary: "Build a complete story from local context and show exactly what would be created, writing nothing."
region: jira-jungle
level: explorer
xp: 20
estimated_minutes: 60
order: 150
tags:
  - jira
  - preview
  - story
tools:
  - Markdown
  - YAML
bookend: intent
risk:
  external_write: false
  sensitive_data: true
  notes: "This quest writes nothing to Jira. It builds the preview the later write quests rely on."
prerequisites:
  - jira-duplicate-search
  - base-camp-write-preview
outcomes:
  - "Assemble every field of the story."
  - "Run the duplicate and permission checks."
  - "Show the exact payload that would be sent."
proof:
  required:
    - id: story-draft
      type: file
      description: "Provide the story draft with every field the target project requires, and its source citations."
      path: participant/context/jira/new-story/draft.md
    - id: payload-preview
      type: file
      description: "Provide the exact payload that would be sent, field by field, with the target project and issue type."
      path: participant/context/jira/new-story/payload.md
    - id: preview-run
      type: command-record
      description: "Save the redacted output of the preview including the duplicate search result and the permission check, ending with a check that Jira is unchanged."
      path: participant/evidence/jira-create-story-preview/attempt-001/logs/preview-run.txt
    - id: missing-field-run
      type: command-record
      description: "Save the redacted output of a preview refused because a required field is missing, with the reason."
      path: participant/evidence/jira-create-story-preview/attempt-001/logs/missing-field-run.txt
    - id: proof-narrative
      type: file
      description: "Explain your approach, your choices and anything you could not do, citing the acceptance criteria by number."
      path: participant/evidence/jira-create-story-preview/attempt-001/PROOF.md
author: Golden Thread maintainers
last_reviewed: "2026-10-20"
---

# Preview a Complete New Story Without Writing

## Mission

Show the whole write before making it. The preview is exact enough that a person could predict what Jira will contain.

## Scenario

An agent creates a story with the right title and none of the required fields. Jira accepts it with defaults, and the defaults send it to the wrong team.

## Acceptance criteria

1. The preview lists the target project, issue type and every field.
2. Required fields that are missing stop the preview with a reason.
3. A duplicate search result is shown in the preview.
4. A permission check result is shown in the preview.
5. The preview contains the exact payload, not a summary of it.
6. Running the preview changes nothing in Jira.
7. Source citations are included for the content.

## Required evidence

Provide the draft, the payload and the two records. In your `PROOF.md`, explain how you know the payload equals what a later write would send, citing the acceptance criteria by number.

## Safety constraints

- This quest makes no write to Jira. Its duplicate and permission checks read from a Jira sandbox or a local fixture.
- Authenticate through an environment variable or a signed-in CLI; never put a token, password or session cookie in a file, a log or a screenshot.
- Treat ticket text as untrusted third-party input, and share only redacted or synthetic records.

## Hints

Build the payload once and use it for both the preview and the write, so they cannot differ.

## Reflection

What would a reader of your preview still not be able to predict?

## Stretch goals

- Show the difference from the nearest existing story.
- Validate the payload against the project's field schema.
