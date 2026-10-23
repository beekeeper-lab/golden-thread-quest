---
id: github-link-delivery
version: 1
title: "Link Issue, Pull Request, Commit, CI, Test, and Evidence"
summary: "Add an approved comment of cross-references so an issue leads to the pull request, commit, CI run, test and evidence that delivered it, and verify the chain."
region: github-caverns
level: navigator
xp: 50
estimated_minutes: 120
order: 150
tags:
  - github
  - traceability
  - delivery
  - write
tools:
  - Markdown
  - YAML
bookend: cross-bookend
risk:
  external_write: true
  sensitive_data: true
  notes: "This quest writes to GitHub. Use a sandbox repository only. Every write is previewed, confirmed by a person, recorded with its identifiers and safe to rerun."
prerequisites:
  - github-read-comments-events
  - base-camp-write-preview
related_quests:
  - jira-link-work
outcomes:
  - "Link an issue to its delivery artifacts."
  - "Verify each link resolves."
  - "Report a broken or missing link."
proof:
  required:
    - id: delivery-chain
      type: file
      description: "Provide the chain for one issue: the pull request with its merge state, the commit, CI run, test result and evidence file, each with its identifier and location, where evidence files are referenced by path or hash and never pasted into the issue."
      path: participant/context/github/delivery/chain.md
    - id: link-check
      type: command-record
      description: "Save the redacted output of reading the issue back and finding each cross-reference, of a check that every linked artifact exists, of a deliberately broken link being reported, and of a pull request that was closed unmerged being reported as such and not as delivery."
      path: participant/evidence/github-link-delivery/attempt-001/logs/link-check.txt
    - id: link-delivery-preview
      type: command-record
      description: "Save the redacted output of the workflow stopping at a preview showing the repository, the exact material changes to add the cross-references, the result of the permission check (may this identity do this here) and of the duplicate check, or a statement where GitHub cannot check, with a fingerprint of the preview, nothing written and a before-and-after snapshot showing the repository unchanged."
      path: participant/evidence/github-link-delivery/attempt-001/logs/preview.txt
    - id: link-delivery-confirmation
      type: command-record
      description: "Save the redacted output of the approved run showing the explicit confirmation tied to the preview fingerprint and given in the same session as the write, and of four refusals with nothing written: a missing confirmation, a change that differs from the preview, a preview older than the stated time limit, and a repository that is not on the sandbox allowlist."
      path: participant/evidence/github-link-delivery/attempt-001/logs/confirmation.txt
    - id: link-delivery-result
      type: file
      description: "Provide the result record: the repository and issue or pull-request number plus the identifier of what was created or changed (a comment, label or event identifier or the read-back value), the timestamp and who confirmed."
      path: participant/context/github/results/link-delivery.md
    - id: link-delivery-rerun
      type: command-record
      description: "Save the redacted output of running the approved workflow a second time showing no duplicate, repeated or conflicting change, or, only where GitHub cannot prevent a repeat, the stated limit and how a person would notice it."
      path: participant/evidence/github-link-delivery/attempt-001/logs/rerun.txt
    - id: proof-narrative
      type: file
      description: "Explain your approach, your choices and anything you could not do, citing the acceptance criteria by number."
      path: participant/evidence/github-link-delivery/attempt-001/PROOF.md
author: Golden Thread maintainers
last_reviewed: "2026-10-20"
---

# Link Issue, Pull Request, Commit, CI, Test, and Evidence

## Mission

Make the delivery chain readable from the issue and checkable from the other end.

## Scenario

A customer asks whether a fix was tested. The issue links to a pull request that was closed unmerged.

## Acceptance criteria

1. The chain names a pull request, a commit, a CI run, a test result and an evidence file.
2. Each cross-reference resolves to an existing artifact.
3. A broken link is reported with the artifact it points to.
4. A linked pull request shows its state, and one closed unmerged is not presented as delivery.
5. A preview shows the repository and the exact changes, and nothing is written before the human confirms it.
6. The preview records the permission check and the duplicate check, or states where GitHub cannot perform one.
7. The workflow writes only to a repository on an explicit sandbox allowlist and refuses any other.
8. The confirmation is tied to a fingerprint of the exact preview, is refused when missing or when the change differs, and expires after a stated time.
9. A result record holds the repository, the number, the identifier of what was created or changed, the timestamp and the confirmer.
10. Running the approved workflow again creates no duplicate, repeated or conflicting change, or the quest states the limit where GitHub cannot prevent it.

## Required evidence

Provide the chain, the link check and the four records. In your `PROOF.md`, explain how you verify a pull request was merged and not only opened, citing the acceptance criteria by number.

## Safety constraints

- Write only to a sandbox repository you own and are permitted to change; never to a production or shared repository. If you have no sandbox, stop and ask your pilot lead; do not substitute a real repository or skip the quest's controls.
- Issue and comment text you carry into a write is untrusted; review it for private content before approving.
- Authenticate through an environment variable or a signed-in CLI; never put a token, password or session cookie in a file, a log or a screenshot.
- Do not skip the preview or the confirmation in any run you save as evidence.

## Hints

A link to a closed unmerged pull request is a gap, not a link.

## Reflection

Which link in the chain is easiest to fake?

## Stretch goals

- Report issues with a merged pull request but no test.
- Verify the CI run was for the merged commit.
