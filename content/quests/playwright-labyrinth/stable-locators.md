---
id: playwright-stable-locators
version: 1
title: "Replace Generated IDs and Brittle DOM Paths"
summary: "Find fragile locators in a test, replace them with stable ones and show the test survives a layout change that broke the original."
region: playwright-labyrinth
level: explorer
xp: 20
estimated_minutes: 60
order: 60
tags:
  - playwright
  - locators
  - stability
tools:
  - Markdown
  - YAML
bookend: validation
risk:
  external_write: false
  sensitive_data: false
  notes: "The target is a practice or local application you can change."
prerequisites:
  - playwright-first-independent-test
outcomes:
  - "Recognize a brittle locator."
  - "Replace it with a role, label or test-id locator."
  - "Show the replacement survives a change that broke the old one."
proof:
  required:
    - id: brittle-test
      type: file
      description: "Provide a test using at least four brittle locators, such as generated class names, positional paths and text that changes, each labeled with its kind in a comment."
      path: participant/tests/playwright/brittle.spec.ts
    - id: stable-test
      type: file
      description: "Provide the same test with stable locators, and a note beside each change saying why the new locator is stable."
      path: participant/tests/playwright/stable.spec.ts
    - id: layout-change-run
      type: command-record
      description: "Save the redacted output of both tests before and after a layout change to the target, showing the brittle test failing and the stable test passing, and of a search of the stable test finding no generated class name, nth-child or index-based locator."
      path: participant/evidence/playwright-stable-locators/attempt-001/logs/layout-change.txt
    - id: proof-narrative
      type: file
      description: "Explain your approach, your choices and anything you could not do, citing the acceptance criteria by number."
      path: participant/evidence/playwright-stable-locators/attempt-001/PROOF.md
author: Golden Thread maintainers
last_reviewed: "2026-10-20"
---

# Replace Generated IDs and Brittle DOM Paths

## Mission

Replace locators that depend on how the page is built with ones that depend on what the user sees or what the team has promised not to change, and prove the difference.

## Scenario

A designer reorders the page. The product works the same, and sixty tests fail because they counted elements from the top of the page.

## Acceptance criteria

1. At least four brittle locators are identified and named by kind.
2. Each is replaced by a locator based on role, label, visible text that the user reads and the team has agreed to keep, or a dedicated test id.
3. Each replacement has a stated reason it is stable.
4. The same business assertion is kept in both tests.
5. After a layout change the brittle test fails and the stable one passes.
6. A search of the stable test finds no generated class name, nth-child or index-based locator.
7. Another tester can follow the reason for each replacement.

## Required evidence

Provide the two tests and the run output. In your `PROOF.md`, explain which replacement you trust least and why, citing the acceptance criteria by number.

## Safety constraints

- Test only an application you run yourself, such as a local demo app in your own folder or container that you may change and reset; never a public site, a production system or one holding real customer data.
- Do not put a real login, token or session cookie in a test, a log, a trace or a screenshot.
- Change the layout only in a copy you control.

## Hints

Ask what the user would still recognize if the page were rebuilt.

## Reflection

Which locator can you not make stable without help from developers?

## Stretch goals

- Propose the test ids a developer should add.
- Count how many locators each approach needs to change.
