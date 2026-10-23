---
id: scrum-refinement-agenda
version: 1
title: "Prioritize Ambiguous, Risky, Dependent, or Oversized Work for Refinement"
summary: "Build a refinement agenda that puts the work most in need of discussion first and says why each item is on it."
region: scrum-village
level: explorer
xp: 20
estimated_minutes: 60
order: 40
tags:
  - scrum
  - refinement
  - prioritization
tools:
  - Markdown
  - YAML
bookend: intent
risk:
  external_write: false
  sensitive_data: false
  notes: "The backlog is synthetic."
prerequisites:
  - base-camp-repository-safety
related_quests:
  - ba-detect-ambiguity
outcomes:
  - "Score backlog items on ambiguity, risk, dependency and size using recorded signals."
  - "Order the agenda and justify the order."
  - "Leave ready items off the agenda."
proof:
  required:
    - id: backlog
      type: file
      description: "Provide a synthetic backlog of at least fifteen items, some ready and some needing refinement for different reasons."
      path: participant/context/scrum/refinement/backlog.md
    - id: agenda
      type: file
      description: "Provide the generated agenda, ordered, with each item's reasons and the signal values behind each reason, the weighting used, the time box and what was left out."
      path: participant/context/scrum/refinement/agenda.md
    - id: agenda-run
      type: command-record
      description: "Save the redacted output of generating the agenda twice with identical results, and of the items it excluded as ready."
      path: participant/evidence/scrum-refinement-agenda/attempt-001/logs/agenda-run.txt
    - id: proof-narrative
      type: file
      description: "Explain your approach, your choices and anything you could not do, citing the acceptance criteria by number."
      path: participant/evidence/scrum-refinement-agenda/attempt-001/PROOF.md
author: Golden Thread maintainers
last_reviewed: "2026-10-20"
---

# Prioritize Ambiguous, Risky, Dependent, or Oversized Work for Refinement

## Mission

Choose what the team should spend refinement time on. Rank by what the work most needs, show the signals, and keep ready work off the list.

## Scenario

Refinement runs forty minutes on the first two items because they were next in the list. The one that blocks the sprint is eleventh and never reached.

## Acceptance criteria

1. Each item on the agenda lists at least one reason.
2. Each reason names the recorded signal behind it, such as missing criteria, an unresolved dependency or an estimate above a stated limit.
3. The order and its weighting are stated.
4. Items that meet the stated readiness standard are excluded.
5. The agenda fits a stated time box and says what was left out.
6. Generating the agenda twice gives the same order.
7. Each item shows the signal values that put it in its position.

## Required evidence

Provide the backlog, the agenda and the run output. In your `PROOF.md`, explain your readiness standard and one item you moved after a second look, citing the acceptance criteria by number.

## Safety constraints

- Use synthetic data with invented names, dates and work items.
- Nothing in this exercise is posted to a tracker, chat channel or email.
- Do not rank real people's work.

## Hints

An item can be risky and clear, or vague and low risk. Decide which should be discussed first and say so.

## Reflection

What would make the team stop trusting the ordering?

## Stretch goals

- Allow the team to pin an item and show the effect on the rest.
- Estimate the minutes each item needs.
