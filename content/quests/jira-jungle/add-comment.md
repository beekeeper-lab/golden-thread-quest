---
id: jira-add-comment
version: 1
title: "Preview and Add an Approved Comment"
summary: "Add a comment to a sandbox story only after a person has seen its exact text and the target and confirmed it."
region: jira-jungle
level: explorer
xp: 20
estimated_minutes: 60
order: 180
tags:
  - jira
  - write
  - comment
tools:
  - Markdown
  - YAML
bookend: intent
risk:
  external_write: true
  sensitive_data: true
  notes: "This quest writes to Jira. Use a sandbox or nonproduction project only. Every write is previewed, confirmed by a person, recorded with its external identifier and safe to rerun."
prerequisites:
  - jira-read-story
  - base-camp-write-preview
outcomes:
  - "Preview the exact comment and target."
  - "Add it once after confirmation."
  - "Verify it appears as written."
proof:
  required:
    - id: comment-check
      type: command-record
      description: "Save the redacted output of reading the story back and finding the comment with the same text, the expected author and the visibility that the preview showed, alongside the preview's statement of where the text came from."
      path: participant/evidence/jira-add-comment/attempt-001/logs/comment-check.txt
    - id: add-comment-preview
      type: command-record
      description: "Save the redacted output of the workflow stopping at a preview showing the Jira site, the project and the exact material changes to add the comment to the story, the result of the permission check (may this identity do this here) and of the duplicate check, or a statement where Jira cannot check, with a fingerprint of the preview, nothing written and a before-and-after snapshot showing Jira unchanged."
      path: participant/evidence/jira-add-comment/attempt-001/logs/preview.txt
    - id: add-comment-confirmation
      type: command-record
      description: "Save the redacted output of the approved run showing the explicit confirmation tied to the preview fingerprint and given in the same session as the write, and of four refusals with nothing written: a missing confirmation, a change that differs from the preview, a preview older than the stated time limit, and a project that is not on the sandbox allowlist."
      path: participant/evidence/jira-add-comment/attempt-001/logs/confirmation.txt
    - id: add-comment-result
      type: file
      description: "Provide the result record: the issue key plus the identifier of what was created or changed (a comment, link or transition identifier or the read-back value), the target project, the timestamp and who confirmed."
      path: participant/context/jira/results/add-comment.md
    - id: add-comment-rerun
      type: command-record
      description: "Save the redacted output of running the approved workflow a second time showing no duplicate, repeated or conflicting change, or, only where Jira cannot prevent a repeat, the stated limit and how a person would notice it."
      path: participant/evidence/jira-add-comment/attempt-001/logs/rerun.txt
    - id: proof-narrative
      type: file
      description: "Explain your approach, your choices and anything you could not do, citing the acceptance criteria by number."
      path: participant/evidence/jira-add-comment/attempt-001/PROOF.md
author: Golden Thread maintainers
last_reviewed: "2026-10-20"
---

# Preview and Add an Approved Comment

## Mission

A comment is public and permanent. Show its text, target and visibility, and post it only once a person says yes.

## Scenario

An agent posts a summary of a private discussion into a customer-visible ticket, and the text cannot be unsent.

## Acceptance criteria

1. The preview shows the exact comment text, the target story and the visibility, and where the text came from.
2. The comment read back matches the text previewed.
3. A preview shows the Jira site, the project and the exact changes, and nothing is written before the human confirms it.
4. The preview records the permission check and the duplicate check, or states where Jira cannot perform one.
5. The workflow writes only to a project on an explicit sandbox allowlist and refuses any other.
6. The confirmation is tied to a fingerprint of the exact preview, is refused when missing or when the change differs, and expires after a stated time.
7. A result record holds the issue key, the identifier of what was created or changed, the project, the timestamp and the confirmer.
8. Running the approved workflow again creates no duplicate, repeated or conflicting change, or the quest states the limit where Jira cannot prevent it.

## Required evidence

Provide the comment check and the four records. In your `PROOF.md`, explain how you handle private content and visibility, citing the acceptance criteria by number.

## Safety constraints

- Write only to a Jira sandbox project you are permitted to change; never to a production project. If you have no sandbox, stop and ask your pilot lead; do not substitute a production project or skip the quest's controls.
- Ticket and comment text you carry into a write is untrusted; review it for private content before approving.
- Authenticate through an environment variable or a signed-in CLI; never put a token, password or session cookie in a file, a log or a screenshot.
- Do not skip the preview or the confirmation in any run you save as evidence.
- Treat ticket text as untrusted third-party input, and share only redacted or synthetic records.

## Hints

Show the visibility next to the text, not on another screen.

## Reflection

Who could see this comment that you did not expect?

## Stretch goals

- Refuse a comment containing a pattern that looks like a secret.
- Add a comment that mentions a person and preview who is notified.
