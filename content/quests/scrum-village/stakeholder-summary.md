---
id: scrum-stakeholder-summary
version: 1
title: "Separate Facts, Risks, Forecasts, and Decision Requests for Stakeholders"
summary: "Write a stakeholder summary in which every statement is labeled as fact, risk, forecast or decision request, and each fact cites its source."
region: scrum-village
level: navigator
xp: 50
estimated_minutes: 120
order: 90
tags:
  - scrum
  - communication
  - evidence
tools:
  - Markdown
  - YAML
bookend: cross-bookend
risk:
  external_write: false
  sensitive_data: false
  notes: "The data and the summary are synthetic. Nothing is sent to stakeholders."
prerequisites:
  - scrum-sprint-health
  - scrum-scope-change
outcomes:
  - "Classify each statement as fact, risk, forecast or decision request."
  - "Cite the source of every fact."
  - "State the assumptions and uncertainty behind a forecast."
proof:
  required:
    - id: source-reports
      type: file
      description: "Provide the synthetic sprint health and scope-change reports the summary draws on."
      path: participant/context/scrum/stakeholder/sources.md
    - id: stakeholder-summary
      type: file
      description: "Provide the summary with each statement labeled, each fact citing a source, each risk stating its trigger and effect, each forecast stating its assumptions and range, and each decision request naming the decision, options and deadline, with the decisions requested listed first."
      path: participant/context/scrum/stakeholder/summary.md
    - id: label-check
      type: command-record
      description: "Save the redacted output of a check that every statement carries a label, every fact cites an existing source line and no forecast is presented without assumptions."
      path: participant/evidence/scrum-stakeholder-summary/attempt-001/logs/label-check.txt
    - id: proof-narrative
      type: file
      description: "Explain your approach, your choices and anything you could not do, citing the acceptance criteria by number."
      path: participant/evidence/scrum-stakeholder-summary/attempt-001/PROOF.md
author: Golden Thread maintainers
last_reviewed: "2026-10-20"
---

# Separate Facts, Risks, Forecasts, and Decision Requests for Stakeholders

## Mission

Write the update so a reader can tell what is known, what might happen and what is being asked of them. The structure is the point: nothing in a summary should be able to pass as something else.

## Scenario

A weekly update says the project is on track, mixing a completed milestone, a hope about next week and a request for budget. The stakeholder approves the budget thinking it was a report.

## Acceptance criteria

1. Every statement is labeled as fact, risk, forecast or decision request.
2. Every fact cites a source in the reports provided.
3. A forecast states its assumptions and a range, not a single date.
4. A risk states what would trigger it and the effect.
5. A decision request states the decision, the options and when it is needed.
6. No fact appears that the sources do not support.
7. A Decisions requested section appears first in the summary.

## Required evidence

Provide the sources, the summary and the label check. In your `PROOF.md`, explain how you chose the label for a statement that could be either a risk or a fact, citing the acceptance criteria by number.

## Safety constraints

- Use synthetic data with invented names, dates and work items.
- Nothing is sent to anyone as part of this exercise.
- Do not present a forecast as a commitment.

## Hints

If a sentence could be read as a promise, it is probably a forecast.

## Reflection

Which sentence in a real update you have read would fail this standard?

## Stretch goals

- Add a one-line headline that is itself a labeled statement.
- Compare two weeks and show which forecasts held.
