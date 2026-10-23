---
id: playwright-data-isolation
version: 1
title: "Make Tests Order-Neutral and Responsible for Their Own Data"
summary: "Make each test create and clean up its own data so tests pass in any order and in parallel, and prove it by shuffling and by running twice."
region: playwright-labyrinth
level: navigator
xp: 50
estimated_minutes: 120
order: 70
tags:
  - playwright
  - isolation
  - test-data
tools:
  - Markdown
  - YAML
bookend: validation
risk:
  external_write: false
  sensitive_data: false
  notes: "The target is an application where you may create and delete test data."
prerequisites:
  - playwright-first-independent-test
outcomes:
  - "Create the data a test needs inside that test."
  - "Clean up without affecting other data."
  - "Show order and parallelism do not change results."
proof:
  required:
    - id: coupled-tests
      type: file
      description: "Provide a pair of tests that depend on each other's data or order, and the failure that shows it."
      path: participant/tests/playwright/coupled.spec.ts
    - id: isolated-tests
      type: file
      description: "Provide the tests rewritten so each creates uniquely named data and removes only what it created."
      path: participant/tests/playwright/isolated.spec.ts
    - id: shuffle-run
      type: command-record
      description: "Save the redacted output of running the isolated tests in forward, reversed and randomized order and in parallel, all passing, and of the coupled tests failing in reversed order."
      path: participant/evidence/playwright-data-isolation/attempt-001/logs/shuffle-run.txt
    - id: cleanup-check
      type: command-record
      description: "Save the output showing that after the runs no test data remains and that no data that existed before was removed."
      path: participant/evidence/playwright-data-isolation/attempt-001/logs/cleanup-check.txt
    - id: check-script
      type: file
      description: "Provide the script that produced the check output, so a reviewer can read what it tests."
      path: participant/tests/playwright/tools/data-isolation-check.ts
    - id: proof-narrative
      type: file
      description: "Explain your approach, your choices and anything you could not do, citing the acceptance criteria by number."
      path: participant/evidence/playwright-data-isolation/attempt-001/PROOF.md
author: Golden Thread maintainers
last_reviewed: "2026-10-20"
---

# Make Tests Order-Neutral and Responsible for Their Own Data

## Mission

Give every test sole responsibility for the data it needs. It makes it, uses it, removes it and touches nothing else, so no test can break another.

## Scenario

Tests pass alone and in the nightly run, and fail when two testers run them at once because both created a customer called Test User.

## Acceptance criteria

1. Each test creates the data it needs.
2. Created data has a name that cannot collide with another run.
3. A test removes only the data it created.
4. The tests pass in forward, reversed and random order.
5. The tests pass when run in parallel.
6. The coupled version is shown failing under reordering.
7. No data present before the run is altered or removed.

## Required evidence

Provide both versions and the two records. In your `PROOF.md`, explain how you make names unique and how cleanup behaves when a test fails halfway, citing the acceptance criteria by number.

## Safety constraints

- Test only an application you run yourself, such as a local demo app in your own folder or container that you may change and reset; never a public site, a production system or one holding real customer data.
- Do not put a real login, token or session cookie in a test, a log, a trace or a screenshot.
- Never run cleanup against data you did not create; filter by a marker unique to the run.

## Hints

Cleanup that runs only after a pass leaves debris exactly when you need the evidence.

## Reflection

What data could a test still leak that your cleanup does not know about?

## Stretch goals

- Run the suite twice in parallel against the same environment.
- Add a check that reports leftover data.
