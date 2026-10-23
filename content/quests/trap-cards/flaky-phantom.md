---
id: trap-flaky-phantom
version: 1
title: "The Flaky Phantom: A Test Fails Nondeterministically"
summary: "Build a test that fails only sometimes for a real reason, and find the cause from evidence instead of retrying until it passes."
region: trap-cards
level: navigator
xp: 50
estimated_minutes: 120
order: 70
tags:
  - trap
  - flaky-tests
  - diagnosis
tools:
  - Markdown
  - YAML
bookend: validation
risk:
  external_write: false
  sensitive_data: false
  notes: "The application and the test are local and you control both."
prerequisites:
  - playwright-failure-triage
outcomes:
  - "Reproduce a failure that depends on timing or order."
  - "Diagnose it from collected evidence."
  - "Fix the cause rather than the symptom."
proof:
  required:
    - id: fix-diff
      type: file
      description: "Provide the diff of the fix to the application and the Playwright configuration, showing no retry, sleep, longer timeout or skip was added."
      path: participant/evidence/trap-flaky-phantom/attempt-001/fix.diff
    - id: phantom-test
      type: file
      description: "Provide a test and a local application with a genuine race or order dependence that makes the test fail between one run in five and one in three."
      path: participant/tests/playwright/phantom.spec.ts
    - id: failure-rate-run
      type: command-record
      description: "Save the redacted output of at least thirty runs before the fix showing the failure rate and the evidence kept from failing runs."
      path: participant/evidence/trap-flaky-phantom/attempt-001/logs/failure-rate-run.txt
    - id: phantom-diagnosis
      type: file
      description: "Write the diagnosis: the cause, the evidence from a failing run that shows it, why retries would have hidden it, and what separates it from a test defect or an environment problem."
      path: participant/context/traps/phantom/diagnosis.md
    - id: fixed-run
      type: command-record
      description: "Save the redacted output of at least one hundred runs after fixing the cause, with no failure and with no retry or longer wait added, and of the failure returning when the fix is reverted."
      path: participant/evidence/trap-flaky-phantom/attempt-001/logs/fixed-run.txt
    - id: proof-narrative
      type: file
      description: "Explain your approach, your choices and anything you could not do, citing the acceptance criteria by number."
      path: participant/evidence/trap-flaky-phantom/attempt-001/PROOF.md
author: Golden Thread maintainers
last_reviewed: "2026-10-20"
---

# The Flaky Phantom: A Test Fails Nondeterministically

## Mission

Make a flake and then run it to ground. The goal is a cause you can show, not a pass you cannot explain.

## Scenario

A checkout test fails once a day in the pipeline. The team sets retries to three and the dashboard goes green. The bug it was catching, a race in the basket total, ships.

## Acceptance criteria

1. The test fails at a measured rate between one in five and one in three over at least thirty runs.
2. Evidence is kept from failing runs.
3. The diagnosis names a cause and cites the evidence that shows it.
4. The diagnosis says why retries would have hidden the cause.
5. The fix adds no retry, sleep or longer timeout.
6. One hundred runs after the fix show no failure.
7. Reverting the fix brings the failure back.

## Required evidence

Provide the test, the two run records and the diagnosis. In your `PROOF.md`, explain how you ruled out a test defect and an environment problem, citing the acceptance criteria by number.

## Safety constraints

- Run the application locally and only against data you created.
- Do not hide the failure with a retry, a sleep or a skip.
- Nothing in this challenge is sent to, or written to, an external system.

## Hints

A failure that depends on order or timing leaves a trace. Capture what ran before it and what the page was doing.

## Reflection

What would you have concluded if you had run it only three times, and why is a hundred more convincing than thirty?

## Stretch goals

- Find the failure rate under parallel load.
- Add a check that fails the build when a test needs a retry.
