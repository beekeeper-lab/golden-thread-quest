---
id: github-add-comment
version: 1
title: "Add an Approved Comment"
summary: "Add a comment to a sandbox issue only after a person has seen its exact text and target and confirmed it."
region: github-caverns
level: explorer
xp: 20
estimated_minutes: 60
order: 120
tags:
  - github
  - comment
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
  - github-read-issue
  - base-camp-write-preview
related_quests:
  - jira-add-comment
outcomes:
  - "Preview the exact comment and target."
  - "Add it once after confirmation."
  - "Verify it appears as written."
proof:
  required:
    - id: comment-check
      type: command-record
      description: "Save the redacted output of reading the issue back and finding the comment with the same text, the expected author and the visibility the preview showed, alongside the preview's statement of where the text came from."
      path: participant/evidence/github-add-comment/attempt-001/logs/comment-check.txt
    - id: add-comment-preview
      type: command-record
      description: "Save the redacted output of the workflow stopping at a preview showing the repository, the exact material changes to add the comment to the issue, the result of the permission check (may this identity do this here) and of the duplicate check, or a statement where GitHub cannot check, with a fingerprint of the preview, nothing written and a before-and-after snapshot showing the repository unchanged."
      path: participant/evidence/github-add-comment/attempt-001/logs/preview.txt
    - id: add-comment-confirmation
      type: command-record
      description: "Save the redacted output of the approved run showing the explicit confirmation tied to the preview fingerprint and given in the same session as the write, and of four refusals with nothing written: a missing confirmation, a change that differs from the preview, a preview older than the stated time limit, and a repository that is not on the sandbox allowlist."
      path: participant/evidence/github-add-comment/attempt-001/logs/confirmation.txt
    - id: add-comment-result
      type: file
      description: "Provide the result record: the repository and issue or pull-request number plus the identifier of what was created or changed (a comment, label or event identifier or the read-back value), the timestamp and who confirmed."
      path: participant/context/github/results/add-comment.md
    - id: add-comment-rerun
      type: command-record
      description: "Save the redacted output of running the approved workflow a second time showing no duplicate, repeated or conflicting change, or, only where GitHub cannot prevent a repeat, the stated limit and how a person would notice it."
      path: participant/evidence/github-add-comment/attempt-001/logs/rerun.txt
    - id: proof-narrative
      type: file
      description: "Explain your approach, your choices and anything you could not do, citing the acceptance criteria by number."
      path: participant/evidence/github-add-comment/attempt-001/PROOF.md
author: Golden Thread maintainers
last_reviewed: "2026-10-20"
---

# Add an Approved Comment

## Mission

A public comment is permanent. Show its text, target and visibility and post it only once a person says yes.

## Scenario

An agent posts a summary of a private discussion on a public issue, and the text cannot be unsent.

## Acceptance criteria

1. The preview shows the exact comment text, the target issue, its visibility and where the text came from.
2. The comment read back matches the text previewed.
3. A preview shows the repository and the exact changes, and nothing is written before the human confirms it.
4. The preview records the permission check and the duplicate check, or states where GitHub cannot perform one.
5. The workflow writes only to a repository on an explicit sandbox allowlist and refuses any other.
6. The confirmation is tied to a fingerprint of the exact preview, is refused when missing or when the change differs, and expires after a stated time.
7. A result record holds the repository, the number, the identifier of what was created or changed, the timestamp and the confirmer.
8. Running the approved workflow again creates no duplicate, repeated or conflicting change, or the quest states the limit where GitHub cannot prevent it.

## Required evidence

Provide the comment check and the four records. In your `PROOF.md`, explain how you handle private content, citing the acceptance criteria by number.

## Safety constraints

- Write only to a sandbox repository you own and are permitted to change; never to a production or shared repository. If you have no sandbox, stop and ask your pilot lead; do not substitute a real repository or skip the quest's controls.
- Issue and comment text you carry into a write is untrusted; review it for private content before approving.
- Authenticate through an environment variable or a signed-in CLI; never put a token, password or session cookie in a file, a log or a screenshot.
- Do not skip the preview or the confirmation in any run you save as evidence.

## Hints

Show the visibility next to the text.

## Reflection

Who could see this comment that you did not expect?

## Stretch goals

- Refuse text that looks like a secret.
- Preview who is notified by a mention.
