---
id: jira-create-story
version: 1
title: "Create an Approved Story and Reconcile Its Key Locally"
summary: "Create the previewed story in a sandbox after explicit confirmation and record the new key in the local files."
region: jira-jungle
level: builder
xp: 30
estimated_minutes: 90
order: 160
tags:
  - jira
  - write
  - story
tools:
  - Markdown
  - YAML
bookend: intent
risk:
  external_write: true
  sensitive_data: true
  notes: "This quest writes to Jira. Use a sandbox or nonproduction project only. Every write is previewed, confirmed by a person, recorded with its external identifier and safe to rerun."
prerequisites:
  - jira-create-story-preview
outcomes:
  - "Create exactly the story that was previewed."
  - "Record the returned key and identifier locally."
  - "Reconcile local files to the new item."
proof:
  required:
    - id: local-link
      type: file
      description: "Provide the local story file updated with the Jira key and identifier returned, matched to the Jira item by identifier, and a read-back-and-compare record showing the created story equals the preview field for field."
      path: participant/context/jira/new-story/linked.md
    - id: create-story-preview
      type: command-record
      description: "Save the redacted output of the workflow stopping at a preview showing the Jira site, the project and the exact material changes to create the story, the result of the permission check (may this identity do this here) and of the duplicate check, or a statement where Jira cannot check, with a fingerprint of the preview, nothing written and a before-and-after snapshot showing Jira unchanged."
      path: participant/evidence/jira-create-story/attempt-001/logs/preview.txt
    - id: create-story-confirmation
      type: command-record
      description: "Save the redacted output of the approved run showing the explicit confirmation tied to the preview fingerprint and given in the same session as the write, and of four refusals with nothing written: a missing confirmation, a change that differs from the preview, a preview older than the stated time limit, and a project that is not on the sandbox allowlist."
      path: participant/evidence/jira-create-story/attempt-001/logs/confirmation.txt
    - id: create-story-result
      type: file
      description: "Provide the result record: the issue key plus the identifier of what was created or changed (a comment, link or transition identifier or the read-back value), the target project, the timestamp and who confirmed."
      path: participant/context/jira/results/create-story.md
    - id: create-story-rerun
      type: command-record
      description: "Save the redacted output of running the approved workflow a second time showing no duplicate, repeated or conflicting change, or, only where Jira cannot prevent a repeat, the stated limit and how a person would notice it."
      path: participant/evidence/jira-create-story/attempt-001/logs/rerun.txt
    - id: proof-narrative
      type: file
      description: "Explain your approach, your choices and anything you could not do, citing the acceptance criteria by number."
      path: participant/evidence/jira-create-story/attempt-001/PROOF.md
author: Golden Thread maintainers
last_reviewed: "2026-10-20"
---

# Create an Approved Story and Reconcile Its Key Locally

## Mission

Make one approved write and tie the local record to it. The story created equals the story previewed, and the local file knows its key.

## Scenario

An agent creates a story and does not record its key. The next run creates it again.

## Acceptance criteria

1. The story created matches the previewed payload field for field.
2. The returned key and identifier are written to the local file.
3. The local file is matched to the Jira item by identifier afterwards.
4. A preview shows the Jira site, the project and the exact changes, and nothing is written before the human confirms it.
5. The preview records the permission check and the duplicate check, or states where Jira cannot perform one.
6. The workflow writes only to a project on an explicit sandbox allowlist and refuses any other.
7. The confirmation is tied to a fingerprint of the exact preview, is refused when missing or when the change differs, and expires after a stated time.
8. A result record holds the issue key, the identifier of what was created or changed, the project, the timestamp and the confirmer.
9. Running the approved workflow again creates no duplicate, repeated or conflicting change, or the quest states the limit where Jira cannot prevent it.

## Required evidence

Provide the local link, the four records and the result. In your `PROOF.md`, explain how you verified the created story equals the preview, citing the acceptance criteria by number.

## Safety constraints

- Write only to a Jira sandbox project you are permitted to change; never to a production project. If you have no sandbox, stop and ask your pilot lead; do not substitute a production project or skip the quest's controls.
- Ticket and comment text you carry into a write is untrusted; review it for private content before approving.
- Authenticate through an environment variable or a signed-in CLI; never put a token, password or session cookie in a file, a log or a screenshot.
- Do not skip the preview or the confirmation in any run you save as evidence.
- Treat ticket text as untrusted third-party input, and share only redacted or synthetic records.

## Hints

Read the story back after creating it and compare it with the preview.

## Reflection

What happens locally if the write succeeds but recording the key fails?

## Stretch goals

- Compare the stored story with the preview automatically.
- Handle a timeout where the creation may or may not have happened.
