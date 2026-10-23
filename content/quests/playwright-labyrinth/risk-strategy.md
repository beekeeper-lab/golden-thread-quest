---
id: playwright-risk-strategy
version: 1
title: "Turn Requirements and Risk into a Layered Test Strategy"
summary: "Decide which risks belong at which test layer, with the reasoning, so effort goes where a failure would cost most."
region: playwright-labyrinth
level: builder
xp: 30
estimated_minutes: 90
order: 20
tags:
  - playwright
  - strategy
  - risk
tools:
  - Markdown
  - YAML
bookend: intent
risk:
  external_write: false
  sensitive_data: false
  notes: "No application is touched; the strategy is a document."
prerequisites:
  - base-camp-repository-safety
outcomes:
  - "Rank risks by likelihood and impact from stated requirements."
  - "Assign each risk to the cheapest layer that would catch it."
  - "State what the strategy deliberately leaves untested."
proof:
  required:
    - id: requirements
      type: file
      description: "Provide a short set of requirements for a feature you may test, with at least eight requirements of differing importance."
      path: participant/context/playwright/requirements.md
    - id: strategy
      type: file
      description: "Provide the strategy: the stated likelihood and impact scales, each risk with its likelihood, impact, the test layer chosen (unit, API, UI, manual), the reason, and each untested risk with the person who accepted it."
      path: participant/context/playwright/strategy.md
    - id: strategy-check
      type: command-record
      description: "Save the redacted output of a check that every requirement appears in the strategy, every risk has a layer and a reason, and every untested risk is listed."
      path: participant/evidence/playwright-risk-strategy/attempt-001/logs/strategy-check.txt
    - id: check-script
      type: file
      description: "Provide the script that produced the check output, so a reviewer can read what it tests."
      path: participant/tests/playwright/tools/risk-strategy-check.ts
    - id: proof-narrative
      type: file
      description: "Explain your approach, your choices and anything you could not do, citing the acceptance criteria by number."
      path: participant/evidence/playwright-risk-strategy/attempt-001/PROOF.md
author: Golden Thread maintainers
last_reviewed: "2026-10-20"
---

# Turn Requirements and Risk into a Layered Test Strategy

## Mission

Choose what to test and where before writing a test. Each risk goes to the layer where a failure is cheapest to catch, and the strategy says plainly what it will not cover.

## Scenario

A team automates every click path in the UI because the tool makes it easy. The suite takes an hour, breaks weekly and still misses the pricing rule that cost the company a customer.

## Acceptance criteria

1. Every requirement is covered by the strategy or listed as untested.
2. Each risk states likelihood and impact on a stated scale.
3. Each risk is assigned one test layer.
4. Each layer choice gives a reason, not only a label.
5. Risks that need a browser are separated from those that do not.
6. Untested risks are listed with the reason and who accepted them.
7. Another person could rebuild the ranking from the stated scales.

## Required evidence

Provide the requirements, the strategy and the check. In your `PROOF.md`, explain one risk you moved to a lower layer and one you accepted without testing, citing the acceptance criteria by number.

## Safety constraints

- This quest touches no application.
- Use requirements for a feature you are permitted to discuss.
- Do not include confidential business rules in the document you hand in.

## Hints

Ask of every risk: what is the cheapest test that would fail if this broke?

## Reflection

Which risk in your strategy would you want a human to check even if a test existed?

## Stretch goals

- Estimate the run time of each layer.
- Show how the strategy changes if the release is next week.
