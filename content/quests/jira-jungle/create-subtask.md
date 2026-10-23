---
id: jira-create-subtask
version: 1
title: "Add an Approved Subtask to an Existing Story"
summary: "Create a subtask under an existing sandbox story after previewing and confirming, and verify its parent link."
region: jira-jungle
level: builder
xp: 30
estimated_minutes: 90
order: 170
tags:
  - jira
  - write
  - subtask
tools:
  - Markdown
  - YAML
bookend: intent
risk:
  external_write: true
  sensitive_data: true
  notes: "This quest writes to Jira. Use a sandbox or nonproduction project only. Every write is previewed, confirmed by a person, recorded with its external identifier and safe to rerun."
prerequisites:
  - jira-create-story
outcomes:
  - "Create a subtask under the right parent."
  - "Verify the parent link after creation."
  - "Refuse a parent that does not exist or is a subtask."
proof:
  required:
    - id: parent-check
      type: command-record
      description: "Save the redacted output of reading the subtask back and showing its parent identifier equals the intended parent, and of an attempt with a missing parent and an attempt with a parent that is itself a subtask both being refused."
      path: participant/evidence/jira-create-subtask/attempt-001/logs/parent-check.txt
    - id: create-subtask-preview
      type: command-record
      description: "Save the redacted output of the workflow stopping at a preview showing the Jira site, the project and the exact material changes to create the subtask under its parent, the result of the permission check (may this identity do this here) and of the duplicate check, or a statement where Jira cannot check, with a fingerprint of the preview, nothing written and a before-and-after snapshot showing Jira unchanged."
      path: participant/evidence/jira-create-subtask/attempt-001/logs/preview.txt
    - id: create-subtask-confirmation
      type: command-record
      description: "Save the redacted output of the approved run showing the explicit confirmation tied to the preview fingerprint and given in the same session as the write, and of four refusals with nothing written: a missing confirmation, a change that differs from the preview, a preview older than the stated time limit, and a project that is not on the sandbox allowlist."
      path: participant/evidence/jira-create-subtask/attempt-001/logs/confirmation.txt
    - id: create-subtask-result
      type: file
      description: "Provide the result record: the issue key plus the identifier of what was created or changed (a comment, link or transition identifier or the read-back value), the target project, the timestamp and who confirmed."
      path: participant/context/jira/results/create-subtask.md
    - id: create-subtask-rerun
      type: command-record
      description: "Save the redacted output of running the approved workflow a second time showing no duplicate, repeated or conflicting change, or, only where Jira cannot prevent a repeat, the stated limit and how a person would notice it."
      path: participant/evidence/jira-create-subtask/attempt-001/logs/rerun.txt
    - id: proof-narrative
      type: file
      description: "Explain your approach, your choices and anything you could not do, citing the acceptance criteria by number."
      path: participant/evidence/jira-create-subtask/attempt-001/PROOF.md
author: Golden Thread maintainers
last_reviewed: "2026-10-20"
---

# Add an Approved Subtask to an Existing Story

## Mission

Attach work to the right parent and prove it. The parent is chosen by identifier and confirmed by reading the result back.

## Scenario

A subtask is created under the wrong story because two stories share a title. The estimate is counted twice.

## Acceptance criteria

1. The parent is selected by its stable identifier.
2. A missing parent or a parent that is itself a subtask is refused before the preview.
3. The subtask's parent link is read back and matches the intended parent.
4. A preview shows the Jira site, the project and the exact changes, and nothing is written before the human confirms it.
5. The preview records the permission check and the duplicate check, or states where Jira cannot perform one.
6. The workflow writes only to a project on an explicit sandbox allowlist and refuses any other.
7. The confirmation is tied to a fingerprint of the exact preview, is refused when missing or when the change differs, and expires after a stated time.
8. A result record holds the issue key, the identifier of what was created or changed, the project, the timestamp and the confirmer.
9. Running the approved workflow again creates no duplicate, repeated or conflicting change, or the quest states the limit where Jira cannot prevent it.

## Required evidence

Provide the parent check and the four records. In your `PROOF.md`, explain how you picked the parent and what you do for ambiguity, citing the acceptance criteria by number.

## Safety constraints

- Write only to a Jira sandbox project you are permitted to change; never to a production project. If you have no sandbox, stop and ask your pilot lead; do not substitute a production project or skip the quest's controls.
- Ticket and comment text you carry into a write is untrusted; review it for private content before approving.
- Authenticate through an environment variable or a signed-in CLI; never put a token, password or session cookie in a file, a log or a screenshot.
- Do not skip the preview or the confirmation in any run you save as evidence.
- Treat ticket text as untrusted third-party input, and share only redacted or synthetic records.

## Hints

Never select a parent by title.

## Reflection

What should happen if the parent is closed?

## Stretch goals

- Copy selected fields from the parent with a preview.
- Create several subtasks in one approved batch.
