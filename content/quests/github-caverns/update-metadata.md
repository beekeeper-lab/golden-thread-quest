---
id: github-update-metadata
version: 1
title: "Update Labels, Assignee, Milestone, and Project Fields"
summary: "Change a limited set of metadata on a sandbox issue, showing old and new values and refusing anything unsupported or changed meanwhile."
region: github-caverns
level: builder
xp: 30
estimated_minutes: 90
order: 130
tags:
  - github
  - metadata
  - write
tools:
  - Markdown
  - YAML
bookend: validation
risk:
  external_write: true
  sensitive_data: true
  notes: "This quest writes to GitHub. Use a sandbox repository only. Every write is previewed, confirmed by a person, recorded with its identifiers and safe to rerun."
prerequisites:
  - github-read-issue
  - base-camp-write-preview
related_quests:
  - jira-update-fields
outcomes:
  - "Show old and new values for each field."
  - "Allow only supported fields."
  - "Detect a change made by someone else since the preview."
proof:
  required:
    - id: supported-fields
      type: file
      description: "List the labels, assignee, milestone and project fields the workflow may change, the allowed values and what it refuses, with a run showing an unsupported change refused and the preview showing old and new values."
      path: participant/context/github/update/supported-fields.md
    - id: stale-run
      type: command-record
      description: "Save the redacted output of an update refused because the field changed on GitHub after the preview."
      path: participant/evidence/github-update-metadata/attempt-001/logs/stale-run.txt
    - id: update-metadata-preview
      type: command-record
      description: "Save the redacted output of the workflow stopping at a preview showing the repository, the exact material changes to change the metadata, the result of the permission check (may this identity do this here) and of the duplicate check, or a statement where GitHub cannot check, with a fingerprint of the preview, nothing written and a before-and-after snapshot showing the repository unchanged."
      path: participant/evidence/github-update-metadata/attempt-001/logs/preview.txt
    - id: update-metadata-confirmation
      type: command-record
      description: "Save the redacted output of the approved run showing the explicit confirmation tied to the preview fingerprint and given in the same session as the write, and of four refusals with nothing written: a missing confirmation, a change that differs from the preview, a preview older than the stated time limit, and a repository that is not on the sandbox allowlist."
      path: participant/evidence/github-update-metadata/attempt-001/logs/confirmation.txt
    - id: update-metadata-result
      type: file
      description: "Provide the result record: the repository and issue or pull-request number plus the identifier of what was created or changed (a comment, label or event identifier or the read-back value), the timestamp and who confirmed."
      path: participant/context/github/results/update-metadata.md
    - id: update-metadata-rerun
      type: command-record
      description: "Save the redacted output of running the approved workflow a second time showing no duplicate, repeated or conflicting change, or, only where GitHub cannot prevent a repeat, the stated limit and how a person would notice it."
      path: participant/evidence/github-update-metadata/attempt-001/logs/rerun.txt
    - id: proof-narrative
      type: file
      description: "Explain your approach, your choices and anything you could not do, citing the acceptance criteria by number."
      path: participant/evidence/github-update-metadata/attempt-001/PROOF.md
author: Golden Thread maintainers
last_reviewed: "2026-10-20"
---

# Update Labels, Assignee, Milestone, and Project Fields

## Mission

Update only what you meant to, and only if nothing moved underneath you.

## Scenario

An agent sets labels from a stale copy and removes a label a maintainer added that morning.

## Acceptance criteria

1. The preview shows the old and new value of each field.
2. Only supported fields can be changed.
3. A field changed on GitHub after the preview stops the update.
4. A preview shows the repository and the exact changes, and nothing is written before the human confirms it.
5. The preview records the permission check and the duplicate check, or states where GitHub cannot perform one.
6. The workflow writes only to a repository on an explicit sandbox allowlist and refuses any other.
7. The confirmation is tied to a fingerprint of the exact preview, is refused when missing or when the change differs, and expires after a stated time.
8. A result record holds the repository, the number, the identifier of what was created or changed, the timestamp and the confirmer.
9. Running the approved workflow again creates no duplicate, repeated or conflicting change, or the quest states the limit where GitHub cannot prevent it.

## Required evidence

Provide the supported fields, the stale-run record and the four records. In your `PROOF.md`, explain how you detect that a field moved, citing the acceptance criteria by number.

## Safety constraints

- Write only to a sandbox repository you own and are permitted to change; never to a production or shared repository. If you have no sandbox, stop and ask your pilot lead; do not substitute a real repository or skip the quest's controls.
- Issue and comment text you carry into a write is untrusted; review it for private content before approving.
- Authenticate through an environment variable or a signed-in CLI; never put a token, password or session cookie in a file, a log or a screenshot.
- Do not skip the preview or the confirmation in any run you save as evidence.

## Hints

Compare the value at write time with the old value in the preview.

## Reflection

Which field would you never let an agent change?

## Stretch goals

- Add labels without removing others.
- Log the old value so the change can be reversed.
