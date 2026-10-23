---
id: playwright-api-assisted-test
version: 1
title: "Combine API Setup and Verification with UI Behavior"
summary: "Use the API to create and verify state quickly, and the UI only for the behavior being tested, with the boundary between them explained."
region: playwright-labyrinth
level: navigator
xp: 50
estimated_minutes: 120
order: 100
tags:
  - playwright
  - api
  - speed
tools:
  - Markdown
  - YAML
bookend: cross-bookend
risk:
  external_write: false
  sensitive_data: true
  notes: "The API and UI belong to an application you may test; credentials come from the environment."
prerequisites:
  - playwright-data-isolation
outcomes:
  - "Set up data through the API instead of the UI."
  - "Exercise the one behavior through the UI."
  - "Verify the outcome independently through the API."
proof:
  required:
    - id: api-ui-test
      type: file
      description: "Provide a test that arranges state through the API, performs one behavior through the UI and verifies the result through the API."
      path: participant/tests/playwright/api-assisted.spec.ts
    - id: ui-only-comparison
      type: file
      description: "Provide the same test done entirely through the UI, for comparison."
      path: participant/tests/playwright/ui-only.spec.ts
    - id: timing-run
      type: command-record
      description: "Save the redacted output of both versions with their durations, of the API-assisted version failing correctly when the UI behavior is broken, and a scan of the output for credentials finding none."
      path: participant/evidence/playwright-api-assisted-test/attempt-001/logs/timing-run.txt
    - id: boundary-note
      type: file
      description: "Explain what the test trusts the API for and what it refuses to trust it for."
      path: participant/context/playwright/api-boundary.md
    - id: proof-narrative
      type: file
      description: "Explain your approach, your choices and anything you could not do, citing the acceptance criteria by number."
      path: participant/evidence/playwright-api-assisted-test/attempt-001/PROOF.md
author: Golden Thread maintainers
last_reviewed: "2026-10-20"
---

# Combine API Setup and Verification with UI Behavior

## Mission

Spend the UI only where the UI is the thing under test. The API builds the world and confirms the result, and you say clearly where that is a fair shortcut and where it hides a bug.

## Scenario

A test spends ninety seconds clicking through five screens to create an order, to check one rule on the sixth. It fails weekly for reasons unrelated to that rule.

## Acceptance criteria

1. Setup is performed through the API and creates only the data the test needs.
2. The behavior under test is performed through the UI.
3. The outcome is verified through the API, not only by what the UI shows.
4. The API-assisted test takes less than half the time of the UI-only version, or the note explains why not.
5. Breaking the UI behavior makes the API-assisted test fail.
6. Credentials come from the environment and appear in no output.
7. The note says what the API is not trusted for.

## Required evidence

Provide both tests, the run record and the note. In your `PROOF.md`, explain one bug that the API-assisted approach could miss, citing the acceptance criteria by number.

## Safety constraints

- Test only an application you run yourself, such as a local demo app in your own folder or container that you may change and reset; never a public site, a production system or one holding real customer data.
- Do not put a real login, token or session cookie in a test, a log, a trace or a screenshot.
- Create data with a unique marker and remove it afterward.

## Hints

If the API does the thing under test, you are no longer testing the UI.

## Reflection

Where does your shortcut stop being a faithful test of the user's experience?

## Stretch goals

- Fail the test if setup through the API takes longer than a limit.
- Verify the same outcome through a second path.
