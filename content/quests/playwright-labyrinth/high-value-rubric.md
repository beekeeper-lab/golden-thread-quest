---
id: playwright-high-value-rubric
version: 1
title: "Define and Consistently Apply Valuable-Test Criteria"
summary: "Write a rubric for what makes a test valuable, score the suite with it, and show two scorers reach similar results."
region: playwright-labyrinth
level: navigator
xp: 50
estimated_minutes: 120
order: 150
tags:
  - playwright
  - quality
  - rubric
tools:
  - Markdown
  - YAML
bookend: validation
risk:
  external_write: false
  sensitive_data: false
  notes: "Scoring uses your own inventory."
prerequisites:
  - playwright-test-inventory
outcomes:
  - "Define criteria with levels and examples."
  - "Score every test."
  - "Measure agreement between two scorers."
proof:
  required:
    - id: rubric
      type: file
      description: "Provide the rubric: each criterion, its levels and one example of each level."
      path: participant/context/playwright/value-rubric.md
    - id: scores-a
      type: file
      description: "Provide the first scoring of at least fifteen tests, taken from your inventory or from a provided sample suite you add for the purpose, with a reason for each score."
      path: participant/context/playwright/scores-a.md
    - id: scores-b
      type: file
      description: "Provide an independent second scoring of the same tests by a different person or a fresh session that did not see the first, stating how it was kept blind."
      path: participant/context/playwright/scores-b.md
    - id: agreement-run
      type: command-record
      description: "Save the redacted output of a comparison showing the agreement between the two scorings and each test where they differ by more than one level, with for each a note saying whether the rubric was revised or why the disagreement stands."
      path: participant/evidence/playwright-high-value-rubric/attempt-001/logs/agreement-run.txt
    - id: proof-narrative
      type: file
      description: "Explain your approach, your choices and anything you could not do, citing the acceptance criteria by number."
      path: participant/evidence/playwright-high-value-rubric/attempt-001/PROOF.md
author: Golden Thread maintainers
last_reviewed: "2026-10-20"
---

# Define and Consistently Apply Valuable-Test Criteria

## Mission

Make valuable mean something specific. The rubric must be clear enough that two people scoring separately land in about the same place, and you measure that.

## Scenario

Two testers each call a test high value. One means it catches real bugs; the other means it is easy to run. The suite is pruned on opinion.

## Acceptance criteria

1. Each criterion has stated levels with an example.
2. Every test in the sample has a score and a reason.
3. The second scoring was made without seeing the first, and says how that was ensured.
4. The comparison reports agreement as the share of tests whose two scores differ by at most one level.
5. Tests where scorers differ by more than one level are listed.
6. The rubric is revised, or the disagreement explained, for each large difference.
7. Each level of each criterion has a worked example a third person can match a new test against.

## Required evidence

Provide the rubric, both scorings and the comparison. In your `PROOF.md`, explain what the disagreements taught you about the rubric, citing the acceptance criteria by number.

## Safety constraints

- Test only an application you run yourself, such as a local demo app in your own folder or container that you may change and reset; never a public site, a production system or one holding real customer data.
- Do not put a real login, token or session cookie in a test, a log, a trace or a screenshot.
- Do not delete tests on the strength of a score in this exercise.

## Hints

Disagreement is the useful output. A rubric that always agrees may be saying nothing.

## Reflection

Which criterion do you think is most often mistaken for value?

## Stretch goals

- Weight criteria and show how the ranking changes.
- Score a test before and after a repair.
