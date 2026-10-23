---
id: playwright-page-model
version: 1
title: "Centralize Selectors and Reusable Page Behavior"
summary: "Move locators and repeated actions out of tests into a page model, and show a UI change is absorbed in one place."
region: playwright-labyrinth
level: builder
xp: 30
estimated_minutes: 90
order: 50
tags:
  - playwright
  - page-object
  - maintainability
tools:
  - Markdown
  - YAML
bookend: validation
risk:
  external_write: false
  sensitive_data: false
  notes: "The tests run against a practice or local application."
prerequisites:
  - playwright-first-independent-test
outcomes:
  - "Put locators and repeated behavior in a page or component model."
  - "Keep assertions in tests, not in the model."
  - "Absorb a UI change by editing the model only."
proof:
  required:
    - id: page-model-file
      type: file
      description: "Provide a page or component model holding the locators and actions for at least two screens and containing no assertions."
      path: participant/tests/playwright/pages/models.ts
    - id: tests-using-model
      type: file
      description: "Provide at least three tests that use the model, contain no raw selectors and reuse model methods rather than repeating their steps."
      path: participant/tests/playwright/model-usage.spec.ts
    - id: change-record
      type: command-record
      description: "Save the redacted output of a deliberate locator change made in the model only, with the tests passing before and after and a Git diff showing only the model changed."
      path: participant/evidence/playwright-page-model/attempt-001/logs/change-record.txt
    - id: proof-narrative
      type: file
      description: "Explain your approach, your choices and anything you could not do, citing the acceptance criteria by number."
      path: participant/evidence/playwright-page-model/attempt-001/PROOF.md
author: Golden Thread maintainers
last_reviewed: "2026-10-20"
---

# Centralize Selectors and Reusable Page Behavior

## Mission

Make a UI change a one-file fix. Locators and repeated actions live in a model, tests say what to verify, and you prove it by changing the interface and editing only the model.

## Scenario

The login button's label changes from Sign in to Log in. Forty tests fail and each needs the same one-line edit.

## Acceptance criteria

1. No test file contains a raw selector.
2. The model covers at least two screens or components.
3. Assertions about business behavior stay in the tests.
4. A locator change is fixed by editing only the model.
5. The Git diff of that change touches no test file.
6. Model methods are named for a user action, such as signIn, and not for an element, such as clickButton3.
7. A new test can reuse the model without copying code.

## Required evidence

Provide the model, the tests and the change record. In your `PROOF.md`, show the one-file diff and explain a decision about what belongs in the model, citing the acceptance criteria by number.

## Safety constraints

- Test only an application you run yourself, such as a local demo app in your own folder or container that you may change and reset; never a public site, a production system or one holding real customer data.
- Do not put a real login, token or session cookie in a test, a log, a trace or a screenshot.
- Make the locator change against your own copy of the target, not someone else's site.

## Hints

If the model asserts business outcomes, a test can no longer disagree with it, so keep the assertions in the test.

## Reflection

What stays in your tests that you were tempted to move to the model?

## Stretch goals

- Add a component model reused by two pages.
- Check automatically that tests contain no selector.
