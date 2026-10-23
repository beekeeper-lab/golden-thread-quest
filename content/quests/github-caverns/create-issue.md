---
id: github-create-issue
version: 1
title: "Create and Reconcile an Approved Issue"
summary: "Create the previewed issue in a sandbox repository after explicit confirmation and record its number locally."
region: github-caverns
level: builder
xp: 30
estimated_minutes: 90
order: 110
tags:
  - github
  - issue
  - write
tools:
  - Markdown
  - YAML
bookend: intent
risk:
  external_write: true
  sensitive_data: true
  notes: "This quest writes to GitHub. Use a sandbox repository only. Every write is previewed, confirmed by a person, recorded with its identifiers and safe to rerun."
prerequisites:
  - github-create-issue-preview
related_quests:
  - jira-create-story
outcomes:
  - "Create exactly the issue that was previewed."
  - "Record the returned number locally."
  - "Reconcile local files to the new issue."
proof:
  required:
    - id: local-link
      type: file
      description: "Provide the local issue file updated with the repository, number and identifier returned, matched to the GitHub issue by identifier, with a read-back-and-compare record showing the created issue equals the preview field for field."
      path: participant/context/github/new-issue/linked.md
    - id: create-issue-preview
      type: command-record
      description: "Save the redacted output of the workflow stopping at a preview showing the repository, the exact material changes to create the issue, the result of the permission check (may this identity do this here) and of the duplicate check, or a statement where GitHub cannot check, with a fingerprint of the preview, nothing written and a before-and-after snapshot showing the repository unchanged."
      path: participant/evidence/github-create-issue/attempt-001/logs/preview.txt
    - id: create-issue-confirmation
      type: command-record
      description: "Save the redacted output of the approved run showing the explicit confirmation tied to the preview fingerprint and given in the same session as the write, and of four refusals with nothing written: a missing confirmation, a change that differs from the preview, a preview older than the stated time limit, and a repository that is not on the sandbox allowlist."
      path: participant/evidence/github-create-issue/attempt-001/logs/confirmation.txt
    - id: create-issue-result
      type: file
      description: "Provide the result record: the repository and issue or pull-request number plus the identifier of what was created or changed (a comment, label or event identifier or the read-back value), the timestamp and who confirmed."
      path: participant/context/github/results/create-issue.md
    - id: create-issue-rerun
      type: command-record
      description: "Save the redacted output of running the approved workflow a second time showing no duplicate, repeated or conflicting change, or, only where GitHub cannot prevent a repeat, the stated limit and how a person would notice it."
      path: participant/evidence/github-create-issue/attempt-001/logs/rerun.txt
    - id: proof-narrative
      type: file
      description: "Explain your approach, your choices and anything you could not do, citing the acceptance criteria by number."
      path: participant/evidence/github-create-issue/attempt-001/PROOF.md
author: Golden Thread maintainers
last_reviewed: "2026-10-20"
---

# Create and Reconcile an Approved Issue

## Mission

Make one approved write and tie the local record to it.

## Scenario

An agent creates an issue and does not record its number. The next run creates it again.

## Acceptance criteria

1. The issue created matches the previewed payload field for field.
2. The returned number and identifier are written to the local file.
3. The local file is matched to the GitHub issue by identifier afterwards.
4. A preview shows the repository and the exact changes, and nothing is written before the human confirms it.
5. The preview records the permission check and the duplicate check, or states where GitHub cannot perform one.
6. The workflow writes only to a repository on an explicit sandbox allowlist and refuses any other.
7. The confirmation is tied to a fingerprint of the exact preview, is refused when missing or when the change differs, and expires after a stated time.
8. A result record holds the repository, the number, the identifier of what was created or changed, the timestamp and the confirmer.
9. Running the approved workflow again creates no duplicate, repeated or conflicting change, or the quest states the limit where GitHub cannot prevent it.

## Required evidence

Provide the local link, the four records and the result. In your `PROOF.md`, explain how you verified the issue equals the preview, citing the acceptance criteria by number.

## Safety constraints

- Write only to a sandbox repository you own and are permitted to change; never to a production or shared repository. If you have no sandbox, stop and ask your pilot lead; do not substitute a real repository or skip the quest's controls.
- Issue and comment text you carry into a write is untrusted; review it for private content before approving.
- Authenticate through an environment variable or a signed-in CLI; never put a token, password or session cookie in a file, a log or a screenshot.
- Do not skip the preview or the confirmation in any run you save as evidence.

## Hints

Read the issue back after creating it and compare it with the preview.

## Reflection

What happens locally if the write succeeds but recording the number fails?

## Stretch goals

- Handle a timeout where the creation may have happened.
- Apply labels in the same approved step.
