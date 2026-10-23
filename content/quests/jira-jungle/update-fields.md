---
id: jira-update-fields
version: 1
title: "Preview and Update Supported Fields Safely"
summary: "Change a limited set of fields on a sandbox story, showing old and new values first and refusing fields the workflow does not support."
region: jira-jungle
level: builder
xp: 30
estimated_minutes: 90
order: 190
tags:
  - jira
  - write
  - fields
tools:
  - Markdown
  - YAML
bookend: validation
risk:
  external_write: true
  sensitive_data: true
  notes: "This quest writes to Jira. Use a sandbox or nonproduction project only. Every write is previewed, confirmed by a person, recorded with its external identifier and safe to rerun."
prerequisites:
  - jira-read-story
  - base-camp-write-preview
outcomes:
  - "Show old and new values for each field."
  - "Allow only supported fields."
  - "Detect a change made by someone else since the preview."
proof:
  required:
    - id: supported-fields
      type: file
      description: "List the fields the workflow may change, the allowed values for each and the fields it refuses, with a run showing an unsupported field being refused and the preview showing the old and new value of each supported field."
      path: participant/context/jira/update/supported-fields.md
    - id: stale-run
      type: command-record
      description: "Save the redacted output of an update refused because the field changed in Jira after the preview was made."
      path: participant/evidence/jira-update-fields/attempt-001/logs/stale-run.txt
    - id: update-fields-preview
      type: command-record
      description: "Save the redacted output of the workflow stopping at a preview showing the Jira site, the project and the exact material changes to change the fields, the result of the permission check (may this identity do this here) and of the duplicate check, or a statement where Jira cannot check, with a fingerprint of the preview, nothing written and a before-and-after snapshot showing Jira unchanged."
      path: participant/evidence/jira-update-fields/attempt-001/logs/preview.txt
    - id: update-fields-confirmation
      type: command-record
      description: "Save the redacted output of the approved run showing the explicit confirmation tied to the preview fingerprint and given in the same session as the write, and of four refusals with nothing written: a missing confirmation, a change that differs from the preview, a preview older than the stated time limit, and a project that is not on the sandbox allowlist."
      path: participant/evidence/jira-update-fields/attempt-001/logs/confirmation.txt
    - id: update-fields-result
      type: file
      description: "Provide the result record: the issue key plus the identifier of what was created or changed (a comment, link or transition identifier or the read-back value), the target project, the timestamp and who confirmed."
      path: participant/context/jira/results/update-fields.md
    - id: update-fields-rerun
      type: command-record
      description: "Save the redacted output of running the approved workflow a second time showing no duplicate, repeated or conflicting change, or, only where Jira cannot prevent a repeat, the stated limit and how a person would notice it."
      path: participant/evidence/jira-update-fields/attempt-001/logs/rerun.txt
    - id: proof-narrative
      type: file
      description: "Explain your approach, your choices and anything you could not do, citing the acceptance criteria by number."
      path: participant/evidence/jira-update-fields/attempt-001/PROOF.md
author: Golden Thread maintainers
last_reviewed: "2026-10-20"
---

# Preview and Update Supported Fields Safely

## Mission

Update only what you meant to and only if nothing moved underneath you. Each change shows old and new, and a field changed meanwhile stops the write.

## Scenario

An agent sets a story's assignee and priority from a stale local copy. It overwrites a change made the same morning by the product owner.

## Acceptance criteria

1. The preview shows the old and new value of each field.
2. Only fields in the supported list can be changed.
3. A field changed in Jira after the preview stops the update.
4. A preview shows the Jira site, the project and the exact changes, and nothing is written before the human confirms it.
5. The preview records the permission check and the duplicate check, or states where Jira cannot perform one.
6. The workflow writes only to a project on an explicit sandbox allowlist and refuses any other.
7. The confirmation is tied to a fingerprint of the exact preview, is refused when missing or when the change differs, and expires after a stated time.
8. A result record holds the issue key, the identifier of what was created or changed, the project, the timestamp and the confirmer.
9. Running the approved workflow again creates no duplicate, repeated or conflicting change, or the quest states the limit where Jira cannot prevent it.

## Required evidence

Provide the supported fields, the stale-run record and the four records. In your `PROOF.md`, explain how you detect that a field moved, citing the acceptance criteria by number.

## Safety constraints

- Write only to a Jira sandbox project you are permitted to change; never to a production project. If you have no sandbox, stop and ask your pilot lead; do not substitute a production project or skip the quest's controls.
- Ticket and comment text you carry into a write is untrusted; review it for private content before approving.
- Authenticate through an environment variable or a signed-in CLI; never put a token, password or session cookie in a file, a log or a screenshot.
- Do not skip the preview or the confirmation in any run you save as evidence.
- Treat ticket text as untrusted third-party input, and share only redacted or synthetic records.

## Hints

Compare the value in Jira at write time with the old value in the preview.

## Reflection

Which field would you never let an agent change?

## Stretch goals

- Allow a custom field with a validated list of values.
- Log the old value so the change can be reversed.
