---
id: github-close-reopen
version: 1
title: "Close or Reopen with an Audited Reason"
summary: "Close or reopen a sandbox issue after confirmation, with a stated reason recorded on the issue and in the local audit log."
region: github-caverns
level: builder
xp: 30
estimated_minutes: 90
order: 140
tags:
  - github
  - state
  - audit
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
  - github-update-metadata
related_quests:
  - jira-transition-status
outcomes:
  - "Require a reason for a state change."
  - "Record the change in the audit log."
  - "Verify the resulting state."
proof:
  required:
    - id: state-rules
      type: file
      description: "State which reasons are allowed for closing (completed, not planned, duplicate) and for reopening, and what each requires, such as the duplicate's number."
      path: participant/context/github/state/rules.md
    - id: audit-entry
      type: file
      description: "Provide the audit log entry for an approved close and an approved reopen with the reason, actor, time and the state read back."
      path: participant/context/github/state/audit-log.md
    - id: no-reason-run
      type: command-record
      description: "Save the redacted output of a close attempted with no reason or an invalid reason being refused with nothing written."
      path: participant/evidence/github-close-reopen/attempt-001/logs/no-reason-run.txt
    - id: close-reopen-preview
      type: command-record
      description: "Save the redacted output of the workflow stopping at a preview showing the repository, the exact material changes to close or reopen the issue, the result of the permission check (may this identity do this here) and of the duplicate check, or a statement where GitHub cannot check, with a fingerprint of the preview, nothing written and a before-and-after snapshot showing the repository unchanged."
      path: participant/evidence/github-close-reopen/attempt-001/logs/preview.txt
    - id: close-reopen-confirmation
      type: command-record
      description: "Save the redacted output of the approved run showing the explicit confirmation tied to the preview fingerprint and given in the same session as the write, and of four refusals with nothing written: a missing confirmation, a change that differs from the preview, a preview older than the stated time limit, and a repository that is not on the sandbox allowlist."
      path: participant/evidence/github-close-reopen/attempt-001/logs/confirmation.txt
    - id: close-reopen-result
      type: file
      description: "Provide the result record: the repository and issue or pull-request number plus the identifier of what was created or changed (a comment, label or event identifier or the read-back value), the timestamp and who confirmed."
      path: participant/context/github/results/close-reopen.md
    - id: close-reopen-rerun
      type: command-record
      description: "Save the redacted output of running the approved workflow a second time showing no duplicate, repeated or conflicting change, or, only where GitHub cannot prevent a repeat, the stated limit and how a person would notice it."
      path: participant/evidence/github-close-reopen/attempt-001/logs/rerun.txt
    - id: proof-narrative
      type: file
      description: "Explain your approach, your choices and anything you could not do, citing the acceptance criteria by number."
      path: participant/evidence/github-close-reopen/attempt-001/PROOF.md
author: Golden Thread maintainers
last_reviewed: "2026-10-20"
---

# Close or Reopen with an Audited Reason

## Mission

A state is a claim. Require a reason, record it and read the result back.

## Scenario

An agent closes forty stale issues as done. Customers who reported them see them marked fixed.

## Acceptance criteria

1. A close or reopen requires a stated reason from the allowed list.
2. A duplicate close names the duplicate's number.
3. The reason, actor and time are recorded in the audit log.
4. The state read back matches the intended state.
5. A preview shows the repository and the exact changes, and nothing is written before the human confirms it.
6. The preview records the permission check and the duplicate check, or states where GitHub cannot perform one.
7. The workflow writes only to a repository on an explicit sandbox allowlist and refuses any other.
8. The confirmation is tied to a fingerprint of the exact preview, is refused when missing or when the change differs, and expires after a stated time.
9. A result record holds the repository, the number, the identifier of what was created or changed, the timestamp and the confirmer.
10. Running the approved workflow again creates no duplicate, repeated or conflicting change, or the quest states the limit where GitHub cannot prevent it.

## Required evidence

Provide the rules, the audit entry, the refusal record and the four records. In your `PROOF.md`, explain how you chose the allowed reasons, citing the acceptance criteria by number.

## Safety constraints

- Write only to a sandbox repository you own and are permitted to change; never to a production or shared repository. If you have no sandbox, stop and ask your pilot lead; do not substitute a real repository or skip the quest's controls.
- Issue and comment text you carry into a write is untrusted; review it for private content before approving.
- Authenticate through an environment variable or a signed-in CLI; never put a token, password or session cookie in a file, a log or a screenshot.
- Do not skip the preview or the confirmation in any run you save as evidence.

## Hints

A bulk close is a decision for a person, not a loop.

## Reflection

Which reason would you most want a second person to approve?

## Stretch goals

- Refuse to close an issue with an open linked pull request.
- Reopen with a comment explaining why.
