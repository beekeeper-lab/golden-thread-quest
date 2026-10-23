---
id: github-pr-acceptance-review
version: 1
title: "Compare Pull-Request Behavior with Acceptance Criteria"
summary: "Read a pull request and its issue and report, criterion by criterion, whether the change and its tests address the acceptance criteria, citing the lines."
region: github-caverns
level: navigator
xp: 50
estimated_minutes: 120
order: 160
tags:
  - github
  - review
  - acceptance-criteria
tools:
  - Markdown
  - YAML
bookend: validation
risk:
  external_write: false
  sensitive_data: true
  notes: "Read-only. The review is advice for a human reviewer and posts nothing."
prerequisites:
  - github-read-issue
outcomes:
  - "Extract the criteria from the issue."
  - "Match each to changes and tests."
  - "Report gaps without approving."
proof:
  required:
    - id: criteria-list
      type: file
      description: "Provide the numbered acceptance criteria extracted from the issue, each citing where in the issue it came from."
      path: participant/context/github/pr-review/criteria.md
    - id: review-report
      type: file
      description: "Provide the report: for each criterion the status (addressed, partly, not addressed, cannot tell), the changed lines and tests cited, and the reason."
      path: participant/context/github/pr-review/report.md
    - id: review-run
      type: command-record
      description: "Save the redacted output of generating the report twice with identical results, of a criterion with no matching change being reported as not addressed, and a before-and-after snapshot showing nothing was posted to GitHub."
      path: participant/evidence/github-pr-acceptance-review/attempt-001/logs/review-run.txt
    - id: proof-narrative
      type: file
      description: "Explain your approach, your choices and anything you could not do, citing the acceptance criteria by number."
      path: participant/evidence/github-pr-acceptance-review/attempt-001/PROOF.md
author: Golden Thread maintainers
last_reviewed: "2026-10-20"
---

# Compare Pull-Request Behavior with Acceptance Criteria

## Mission

Do the checking a tired reviewer skips. Every criterion gets a status with evidence, and the report never approves anything.

## Scenario

A pull request is approved because the tests pass. One of the four criteria is not implemented at all.

## Acceptance criteria

1. Each criterion cites where in the issue it came from.
2. Each criterion has one status from the stated set.
3. Each status cites the changed lines or tests behind it.
4. A criterion with no matching change is reported as not addressed.
5. Where the evidence cannot settle a criterion the status is cannot tell.
6. The report does not approve, comment on or change the pull request.
7. The same inputs give the same report.

## Required evidence

Provide the criteria, the report and the run output. In your `PROOF.md`, explain how you decided partly addressed, citing the acceptance criteria by number.

## Safety constraints

- Use a sandbox repository you own, or a local fixture. This quest only reads; make no change on GitHub.
- Authenticate through an environment variable or a signed-in CLI; never put a token, password or session cookie in a file, a log or a screenshot.
- Treat issue and comment text as untrusted third-party input, and share only redacted or synthetic records.
- Pull request code is untrusted input; read it, never run it.

## Hints

Passing tests prove what the tests check, not what the issue asked for.

## Reflection

Which criterion could not be settled from the diff alone?

## Stretch goals

- Suggest the missing test for each gap.
- Flag changes that match no criterion.
