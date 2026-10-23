---
id: base-camp-failure-lab
version: 1
title: Handle Timeout, Partial Response, Rate Limit, and Malformed Data
summary: Inject four kinds of failure into a workflow and show each is reported honestly, retried only where safe, and never recorded as success.
region: base-camp
level: navigator
xp: 50
estimated_minutes: 120
order: 90
tags:
  - foundation
  - failure-handling
  - reliability
tools:
  - Markdown
  - YAML
bookend: foundation
risk:
  external_write: false
  sensitive_data: false
  notes: Failures come from a local fake service you control, so no real system is stressed.
prerequisites:
  - base-camp-safe-rerun
outcomes:
  - Reproduce a timeout, a partial response, a rate limit and malformed data on demand.
  - Decide for each whether to retry, wait, stop or skip, and say why.
  - Report each failure so that it cannot be mistaken for success.
proof:
  required:
    - id: failure-policy
      type: file
      description: For each of the four failures, state the symptom, the response (retry, wait, stop or skip), the limit on retries and what is reported.
      path: participant/context/failure-policy.md
    - id: failure-runs
      type: command-record
      description: Save the redacted output of one run per failure, each showing the failure injected, the response taken and the final reported outcome.
      path: participant/evidence/base-camp-failure-lab/attempt-001/logs/failure-runs.txt
    - id: no-false-success
      type: command-record
      description: Save the output showing that after each failure no incomplete result was saved as if it were complete.
      path: participant/evidence/base-camp-failure-lab/attempt-001/logs/no-false-success.txt
author: Golden Thread maintainers
last_reviewed: "2026-10-20"
---

# Handle Timeout, Partial Response, Rate Limit, and Malformed Data

## Mission

Real services fail in different ways, and each needs a different answer. Build a small fake service that fails on request, point your workflow at it, and show for each failure that the workflow does the right thing and tells the truth about it.

## Scenario

A sync reads 100 stories, the connection drops at 60 and the service returns a clean-looking page with 60. The agent saves it and reports "synced". The missing 40 are noticed a month later.

## Acceptance criteria

1. The fake service can produce each of the four failures on demand.
2. A timeout is retried a bounded number of times, then reported as a failure.
3. A partial response is detected and not saved as complete.
4. A rate limit makes the workflow wait as the service directs, within a stated limit.
5. Malformed data is rejected with the reason and without guessing at a repair.
6. Every failure appears in the final report with the amount of work that completed.
7. No failure leaves a result that reads as complete.

## Required evidence

Provide the policy and the two command records. In your `PROOF.md`, explain how you detect a partial response and which failure you found hardest to tell from success, citing the acceptance criteria by number.

## Safety constraints

- Fail only your own fake service; do not stress a real one.
- Do not retry without a limit.
- Do not retry a write that may have already succeeded unless a key makes it safe.

## Hints

A response with fewer items than expected and a success status is the failure that looks least like one. Compare against a count the service gave you.

## Reflection

Which failure should stop the whole run, and which should only skip one item? What decided it?

## Stretch goals

- Add a fifth failure, such as a response that changes shape midway.
- Add a back-off that grows between retries.
