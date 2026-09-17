---
id: playwright-first-independent-test
version: 1
title: Build an Independent, Maintainable Playwright Test
summary: Automate one valuable business behavior with centralized page objects, stable locators, meaningful assertions, and reproducible evidence.
region: playwright-labyrinth
level: builder
xp: 30
estimated_minutes: 120
order: 10
tags:
  - playwright
  - testing
  - automation
  - read-only
tools:
  - Playwright
  - TypeScript
bookend: validation
risk:
  external_write: false
  sensitive_data: false
prerequisites:
  - base-camp-repository-safety
outcomes:
  - Express a business validation through a focused Playwright test.
  - Centralize selectors and page behavior using a maintainable page or component model.
  - Produce evidence that distinguishes meaningful validation from merely successful navigation.
proof:
  required:
    - id: playwright-test
      type: file
      description: Provide the independent Playwright test file in the participant test area.
      path: participant/tests/playwright/first-independent-test.spec.ts
    - id: page-model
      type: file
      description: Provide a centralized page or component model used by the test.
      path: participant/tests/playwright/pages/example-page.ts
    - id: playwright-quality-validation
      type: validator
      description: Run the registered Playwright quality validator successfully.
      validator: validate-playwright-quality
    - id: execution-record
      type: command-record
      description: Save the redacted execution summary for the tagged test run.
      path: participant/evidence/playwright-first-independent-test/attempt-001/logs/test-run.txt
  optional:
    - id: meaningful-success-screenshot
      type: screenshot
      description: Capture the state at the most important successful business assertion.
      path: participant/evidence/playwright-first-independent-test/attempt-001/screenshots/validated-state.png
validators:
  - validate-playwright-quality
related_quests:
  - base-camp-repository-safety
author: Golden Thread maintainers
last_reviewed: "2026-09-16"
---

# Build an Independent, Maintainable Playwright Test

## Mission

Choose one important, read-only business behavior and automate it as an independent Playwright test whose value and validation logic are obvious to another tester.

## Scenario

A passing browser script is not automatically a valuable test. This quest asks you to demonstrate stable selection, centralized page behavior, meaningful assertions, isolation, tagging, and useful evidence.

## Acceptance criteria

- The test title describes user behavior and expected outcome.
- The test can run alone and in any suite order.
- Selectors and reusable page behavior are centralized in a page or component model.
- Stable roles, labels, text, or agreed test IDs are preferred over generated IDs and brittle DOM paths.
- The test contains no arbitrary fixed sleep.
- Assertions validate the business outcome rather than only URL, visibility, or HTTP success when those are insufficient.
- Test data and preconditions are explicit.
- The test carries tags for feature, risk, read-only/write behavior, and expected duration.
- Failure evidence includes trace, screenshot, and a concise reproduction summary.
- Success evidence is captured at the meaningful validation point rather than on every step.
- Rerunning the test does not change application data.

## Required evidence

Provide the test, page model, tagged execution record, validator result, and a `PROOF.md` explaining the business risk and why the assertion proves the intended behavior.

## Safety constraints

- Use an approved nonproduction environment or a deterministic local fixture.
- Keep credentials out of test source and reports.
- Do not weaken assertions, add retries, or increase timeouts merely to make a failure disappear.

## Hints

A good test has one coherent business reason to fail. Page objects should centralize interaction mechanics without hiding every assertion.

## Reflection

If this test failed tomorrow, what decision could the team make from the evidence it produces?

## Stretch goals

- Add an API-assisted setup or verification step.
- Demonstrate tag combinations from the command line.
- Score the test from 0–100 using documented high-value-test criteria.
