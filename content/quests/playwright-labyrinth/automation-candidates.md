---
id: playwright-automation-candidates
version: 1
title: "Explain What Should and Should Not Be Automated"
summary: "Judge a list of test ideas against stated criteria and defend both the ones you automate and the ones you leave manual."
region: playwright-labyrinth
level: explorer
xp: 20
estimated_minutes: 60
order: 30
tags:
  - playwright
  - automation
  - judgment
tools:
  - Markdown
  - YAML
bookend: intent
risk:
  external_write: false
  sensitive_data: false
  notes: "No application is touched."
prerequisites:
  - playwright-risk-strategy
outcomes:
  - "State criteria for automating a test."
  - "Apply them to a list of ideas."
  - "Defend the manual choices as clearly as the automated ones."
proof:
  required:
    - id: criteria
      type: file
      description: "State the criteria you use to decide whether a test is worth automating, such as repeatability, stability, value, cost and frequency."
      path: participant/context/playwright/automation-criteria.md
    - id: candidate-decisions
      type: file
      description: "Provide a list of at least twelve test ideas, each with a decision (automate, keep manual or drop), the criteria that drove it, the reason, and for a manual decision how the check will be done instead."
      path: participant/context/playwright/candidate-decisions.md
    - id: decision-check
      type: command-record
      description: "Save the redacted output of a check that every idea has a decision, a reason and at least one named criterion, that at least three are not automated, that no decision rests on ease of automation alone, and a second person's independent decisions on at least six of the ideas, with the share that match."
      path: participant/evidence/playwright-automation-candidates/attempt-001/logs/decision-check.txt
    - id: check-script
      type: file
      description: "Provide the script that produced the check output, so a reviewer can read what it tests."
      path: participant/tests/playwright/tools/automation-candidates-check.ts
    - id: proof-narrative
      type: file
      description: "Explain your approach, your choices and anything you could not do, citing the acceptance criteria by number."
      path: participant/evidence/playwright-automation-candidates/attempt-001/PROOF.md
author: Golden Thread maintainers
last_reviewed: "2026-10-20"
---

# Explain What Should and Should Not Be Automated

## Mission

Make the decision visible. For each idea, say whether it earns automation, and say why in terms that someone could dispute.

## Scenario

A manager asks for everything to be automated by the end of the quarter. Two months later the suite is full of tests for a screen that is changing every sprint.

## Acceptance criteria

1. The criteria are written and used consistently.
2. Every idea has a decision of automate, manual or drop.
3. Every decision names at least one criterion.
4. At least three ideas are not automated.
5. A manual decision says how it will be checked instead.
6. A reviewer reapplying the criteria reaches the same decision for at least three of every four ideas.
7. No decision relies only on how easy it is to automate.

## Required evidence

Provide the criteria, the decisions and the check. In your `PROOF.md`, explain the decision you were least sure of, citing the acceptance criteria by number.

## Safety constraints

- This quest touches no application.
- Use ideas for a feature you may discuss.
- Do not paste confidential requirements.

## Hints

Easy to automate and worth automating are different questions.

## Reflection

Which test did you keep manual that a colleague would want automated, and what would change your mind?

## Stretch goals

- Score each idea numerically and compare with your gut decision.
- Revisit the decisions after a month and record what changed.
