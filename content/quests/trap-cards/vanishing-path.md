---
id: trap-vanishing-path
version: 1
title: "The Vanishing Path: An API Partially Succeeds and Then Fails"
summary: "Build a fake service that accepts part of a batch and then fails, and show your workflow reports exactly what happened and resumes without repeating or losing work."
region: trap-cards
level: boss
xp: 100
estimated_minutes: 240
order: 60
tags:
  - trap
  - failure-handling
  - idempotence
tools:
  - Markdown
  - YAML
bookend: foundation
risk:
  external_write: false
  sensitive_data: false
  notes: "The service and all writes are synthetic and local."
prerequisites:
  - base-camp-failure-lab
outcomes:
  - "Reproduce a batch that half-succeeds."
  - "Report which items did and did not happen."
  - "Resume without duplicates or losses."
proof:
  required:
    - id: partial-service
      type: file
      description: "Provide the runnable fake service script and a batch of at least ten items in which it accepts some, then fails with an ambiguous error, so that one item's outcome is unknown."
      path: participant/tools/traps/vanishing/service.py
    - id: partial-run
      type: command-record
      description: "Save the redacted output of the batch run showing the items confirmed done, the items confirmed not done, the item whose outcome is unknown and the final report refusing to say complete."
      path: participant/evidence/trap-vanishing-path/attempt-001/logs/partial-run.txt
    - id: resume-run
      type: command-record
      description: "Save the redacted output of the resumed run showing the unknown item checked before acting, only missing items done and a total in the service equal to the batch size with no duplicate."
      path: participant/evidence/trap-vanishing-path/attempt-001/logs/resume-run.txt
    - id: vanishing-notes
      type: file
      description: "Explain how an unknown outcome is resolved, what happens if resolving it fails and which design choice mattered most."
      path: participant/context/traps/vanishing/notes.md
    - id: proof-narrative
      type: file
      description: "Explain your approach, your choices and anything you could not do, citing the acceptance criteria by number."
      path: participant/evidence/trap-vanishing-path/attempt-001/PROOF.md
author: Golden Thread maintainers
last_reviewed: "2026-10-20"
---

# The Vanishing Path: An API Partially Succeeds and Then Fails

## Mission

Treat partial success as a first-class state. Say what is known, what is not and what you will not guess.

## Scenario

A batch of forty updates is sent. After twenty-six the service times out. The agent retries the whole batch, and twenty-six customers get a second email.

## Acceptance criteria

1. The service accepts some items and then fails with an ambiguous error.
2. The run lists items confirmed done, confirmed not done and unknown.
3. The final report does not claim completion.
4. The resumed run checks the unknown item before acting.
5. Only missing items are done on resume.
6. The service ends with exactly the batch size and no duplicate.
7. The notes say what happens if resolving the unknown item also fails.

## Required evidence

Provide the service, the two records and the notes. In your `PROOF.md`, explain how you keyed items, citing the acceptance criteria by number.

## Safety constraints

- Build the trap from synthetic data with invented names and identifiers; never aim it at a real system, ticket or person.
- Nothing in this challenge is sent to, or written to, an external system.
- Do not retry a write that may already have happened unless a key makes it safe.

## Hints

Give every item a key the service can look up. Ask before you repeat.

## Reflection

What would you do if the service could not tell you whether an item exists?

## Stretch goals

- Fail at three different points and show each recovers.
- Add a second failure during the resume.
