---
id: trap-three-system-hydra
version: 1
title: "The Three-System Hydra: Jira, Trello, and GitHub Disagree"
summary: "Make three systems tell three different stories about the same work, and show your workflow reports the contradiction without choosing a side."
region: trap-cards
level: boss
xp: 100
estimated_minutes: 240
order: 40
tags:
  - trap
  - conflicts
  - cross-system
tools:
  - Markdown
  - YAML
bookend: cross-bookend
risk:
  external_write: false
  sensitive_data: false
  notes: "All three systems are synthetic local fixtures."
prerequisites:
  - context-cross-system-conflicts
outcomes:
  - "Link the same work across three systems by identity."
  - "Surface every contradiction with sources and times."
  - "Refuse to resolve them silently."
proof:
  required:
    - id: hydra-fixture
      type: file
      description: "Provide fixtures for one piece of work in a Jira-style tracker, a Trello-style board and a GitHub-style repository, with a different status, owner and date in each, one system using a different identifier format and a changed title, and a fourth item that agrees everywhere."
      path: participant/context/traps/hydra/fixture.md
    - id: hydra-report
      type: file
      description: "Provide the report: for each contradiction the field, the value and time in each system and why it is a conflict, and the agreeing item listed apart."
      path: participant/context/traps/hydra/report.md
    - id: hydra-run
      type: command-record
      description: "Save the redacted output of the run, with checksums showing no fixture was changed, the same report on a second run, and an attempt to be told which system is right declining to pick one and listing what a person would need to decide."
      path: participant/evidence/trap-three-system-hydra/attempt-001/logs/hydra-run.txt
    - id: hydra-notes
      type: file
      description: "Explain how the work was linked across the systems and the contradiction that was hardest to see."
      path: participant/context/traps/hydra/notes.md
    - id: proof-narrative
      type: file
      description: "Explain your approach, your choices and anything you could not do, citing the acceptance criteria by number."
      path: participant/evidence/trap-three-system-hydra/attempt-001/PROOF.md
author: Golden Thread maintainers
last_reviewed: "2026-10-20"
---

# The Three-System Hydra: Jira, Trello, and GitHub Disagree

## Mission

Build the three-headed problem and make your workflow face all heads. Each system is a witness, and your workflow is not the judge.

## Scenario

The tracker says Done, the board says In Review and the repository issue is open with a failing build. The weekly report says the work shipped.

## Acceptance criteria

1. The same work is linked across all three fixtures by a stable identity, not a title.
2. Every field that differs is reported with the value and time from each system.
3. An item that agrees everywhere is not reported as a conflict.
4. No fixture is changed by the run.
5. Asked which system is right, the workflow declines and lists what a person would need to decide.
6. The same fixtures give the same report.
7. The notes name the contradiction that was hardest to see.

## Required evidence

Provide the fixtures, the report, the run and the notes. In your `PROOF.md`, say what you would need to know to resolve each conflict, citing the acceptance criteria by number.

## Safety constraints

- Build the trap from synthetic data with invented names and identifiers; never aim it at a real system, ticket or person.
- Nothing in this challenge is sent to, or written to, an external system.
- Do not pick a winner to make the report look tidy.

## Hints

A conflict report with one clear answer has probably decided something for you.

## Reflection

Which system would you trust for which field, and who should have to agree to that?

## Stretch goals

- Add a fourth system.
- Rank conflicts by the downstream work they affect.
