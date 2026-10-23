---
id: trap-false-victory
version: 1
title: "The False Victory: A Proposed Repair Weakens the Assertion"
summary: "Review a repair that turns a failing test green by weakening what it checks, and show you catch it and prove the test no longer protects the rule."
region: trap-cards
level: boss
xp: 100
estimated_minutes: 240
order: 80
tags:
  - trap
  - test-repair
  - validation
tools:
  - Markdown
  - YAML
bookend: validation
risk:
  external_write: false
  sensitive_data: false
  notes: "The application, the tests and the repairs are local."
prerequisites:
  - playwright-repair-test
outcomes:
  - "Recognize a repair that weakens validation."
  - "Prove it by breaking the rule."
  - "Produce an honest repair."
proof:
  required:
    - id: original-and-repairs
      type: file
      description: "Provide a test that protects a business rule, an intended change to the application's behavior that makes the test fail, and three proposed repairs that turn it green (one honest, which updates the expected value and keeps every business assertion, one that loosens the assertion and one that makes the check conditional), written by a different person or a fresh session so that you review them blind."
      path: participant/context/traps/false-victory/repairs.md
    - id: review-findings
      type: file
      description: "Provide your review of each repair: whether it weakens the test, the evidence from the diff, whether the business rule is still protected, and a before-and-after list of the business assertions for each repair."
      path: participant/context/traps/false-victory/review.md
    - id: mutation-run
      type: command-record
      description: "Save the redacted output of each repaired test run against the application with the business rule deliberately broken, showing the honest repair failing and the two weakened repairs passing."
      path: participant/evidence/trap-false-victory/attempt-001/logs/mutation-run.txt
    - id: weakening-check
      type: command-record
      description: "Save the output of a check that flags the two weakened repairs and passes the honest one."
      path: participant/evidence/trap-false-victory/attempt-001/logs/weakening-check.txt
    - id: proof-narrative
      type: file
      description: "Explain your approach, your choices and anything you could not do, citing the acceptance criteria by number."
      path: participant/evidence/trap-false-victory/attempt-001/PROOF.md
author: Golden Thread maintainers
last_reviewed: "2026-10-20"
---

# The False Victory: A Proposed Repair Weakens the Assertion

## Mission

Be the reviewer who does not trust a green test. Prove which repairs keep their teeth by breaking the rule on purpose.

## Scenario

A pull request fixes a red test. The test goes green because it now asserts that the total is a number. Nothing checks the total any more, and the pricing bug is back by Friday.

## Acceptance criteria

1. The three repairs were written by someone other than you, and include one honest repair and two that weaken the test.
2. The review explains each weakening from the diff.
3. With the rule broken, the honest repair fails.
4. With the rule broken, each weakened repair passes, showing it no longer protects the rule.
5. The weakening check flags both weakened repairs and passes the honest one.
6. The review says what each repair gives up in terms of the business rule.
7. The honest repair keeps every business assertion of the original.

## Required evidence

Provide the repairs, the review and the two records. In your `PROOF.md`, say which weakening was hardest to spot in the diff, citing the acceptance criteria by number.

## Safety constraints

- Break the business rule only in your own copy of the application.
- Never make a failing test pass by skipping it, adding a retry or loosening an assertion in the repair you submit as honest.
- Nothing in this challenge is sent to, or written to, an external system.

## Hints

Mutation is the lie detector: a test that still passes when the rule is broken is not testing the rule.

## Reflection

What review habit would have caught the weakened repair without running anything?

## Stretch goals

- Add a third kind of weakening and extend the check.
- Run the weakening check in the repository's review process.
