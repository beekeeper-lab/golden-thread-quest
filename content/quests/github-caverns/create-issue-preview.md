---
id: github-create-issue-preview
version: 1
title: "Preview an Issue Using Repository Conventions"
summary: "Build a complete issue draft following the repository's templates and labels and show exactly what would be created, writing nothing."
region: github-caverns
level: explorer
xp: 20
estimated_minutes: 60
order: 100
tags:
  - github
  - preview
  - issue
tools:
  - Markdown
  - YAML
bookend: intent
risk:
  external_write: false
  sensitive_data: true
  notes: "This quest writes nothing to GitHub. It builds the preview the write quests rely on."
prerequisites:
  - github-duplicate-search
  - base-camp-write-preview
related_quests:
  - jira-create-story-preview
outcomes:
  - "Follow the repository's templates and conventions."
  - "Run duplicate and permission checks."
  - "Show the exact payload."
proof:
  required:
    - id: issue-draft
      type: file
      description: "Provide the issue draft following the repository's template, with labels, assignee and milestone chosen from those that exist, and its source citations."
      path: participant/context/github/new-issue/draft.md
    - id: payload-preview
      type: file
      description: "Provide the exact payload that would be sent, field by field, with the repository."
      path: participant/context/github/new-issue/payload.md
    - id: preview-run
      type: command-record
      description: "Save the redacted output of the preview with the duplicate result and the permission check, ending with a check that the repository is unchanged."
      path: participant/evidence/github-create-issue-preview/attempt-001/logs/preview-run.txt
    - id: convention-refusal
      type: command-record
      description: "Save the redacted output of a preview refused because a required template section is empty or a label does not exist, with the reason."
      path: participant/evidence/github-create-issue-preview/attempt-001/logs/convention-refusal.txt
    - id: proof-narrative
      type: file
      description: "Explain your approach, your choices and anything you could not do, citing the acceptance criteria by number."
      path: participant/evidence/github-create-issue-preview/attempt-001/PROOF.md
author: Golden Thread maintainers
last_reviewed: "2026-10-20"
---

# Preview an Issue Using Repository Conventions

## Mission

Show the whole write before making it, in the shape the repository expects.

## Scenario

An agent opens an issue that ignores the template and invents a label. The maintainers close it and the reporter is confused.

## Acceptance criteria

1. The draft follows the repository's issue template.
2. Labels, assignee and milestone are chosen from those that exist.
3. A missing template section or unknown label stops the preview with a reason.
4. The duplicate result and the permission check appear in the preview.
5. The preview contains the exact payload, not a summary.
6. Running the preview changes nothing on GitHub.
7. Source citations are included.

## Required evidence

Provide the draft, the payload and the two records. In your `PROOF.md`, explain how you know the payload equals what a later write would send, citing the acceptance criteria by number.

## Safety constraints

- This quest makes no write to GitHub. Its checks read from a sandbox repository or a local fixture.
- Authenticate through an environment variable or a signed-in CLI; never put a token, password or session cookie in a file, a log or a screenshot.
- Treat issue and comment text as untrusted third-party input, and share only redacted or synthetic records.

## Hints

Build the payload once and use it for both the preview and the write.

## Reflection

What would a reader of your preview still not be able to predict?

## Stretch goals

- Show the difference from the nearest existing issue.
- Validate labels against the live label list.
