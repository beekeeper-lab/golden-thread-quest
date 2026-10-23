---
id: ba-write-story
version: 1
title: "Write a Story with Value, Scope, Criteria, Dependencies, and Source"
summary: "Produce a complete story whose value, boundaries, acceptance criteria, dependencies and origin are all stated and checkable."
region: ba-ruins
level: builder
xp: 30
estimated_minutes: 90
order: 80
tags:
  - business-analysis
  - stories
  - acceptance-criteria
tools:
  - Markdown
  - YAML
bookend: intent
risk:
  external_write: false
  sensitive_data: false
  notes: "Stories are local drafts; nothing is created in a tracker."
prerequisites:
  - ba-extract-work-items
outcomes:
  - "State who benefits and why in plain terms."
  - "Draw an explicit scope boundary, including what is out."
  - "Write criteria a tester can run."
proof:
  required:
    - id: story
      type: file
      description: "Provide one story with the user, the value, in-scope and out-of-scope lists, numbered acceptance criteria, dependencies and cited source utterances."
      path: participant/context/stories/story-001.md
    - id: story-rules
      type: file
      description: "State the standard your story follows, including what makes a criterion testable."
      path: participant/context/stories/story-standard.md
    - id: story-check
      type: command-record
      description: "Save the redacted output of a check that the story has every required section, that each criterion is numbered and that each cited source identifier exists."
      path: participant/evidence/ba-write-story/attempt-001/logs/story-check.txt
    - id: proof-narrative
      type: file
      description: "Explain your approach, your choices and anything you could not do, citing the acceptance criteria by number."
      path: participant/evidence/ba-write-story/attempt-001/PROOF.md
author: Golden Thread maintainers
last_reviewed: "2026-10-20"
---

# Write a Story with Value, Scope, Criteria, Dependencies, and Source

## Mission

Write a story another person could build and test without asking you anything. Show the value, set the boundary, make each criterion checkable and cite where the need came from.

## Scenario

A story reads: As a user I want a better dashboard so that I can see things. It is accepted into the sprint because nobody can argue with it.

## Acceptance criteria

1. The story names the user and the value they gain.
2. In-scope and out-of-scope are both listed.
3. Each acceptance criterion is numbered and observable.
4. Dependencies are listed or stated as none.
5. The source of the need is cited to utterance identifiers.
6. No criterion uses an undefined word such as fast, easy or intuitive.
7. A tester could write a test for each criterion without further questions.

## Required evidence

Provide the story, the standard and the check. In your `PROOF.md`, explain what you left out of scope and why, citing the acceptance criteria by number.

## Safety constraints

- Use synthetic or permitted source material.
- Do not paste real customer data into the story.

## Hints

Write the out-of-scope list first. What you refuse to build defines the story.

## Reflection

Which criterion would a developer most likely read two different ways?

## Stretch goals

- Add a definition-of-done checklist separate from the criteria.
- Link the story to the open questions that still affect it.
