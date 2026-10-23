---
id: context-decision-log
version: 1
title: "Distinguish Approved Decisions, Proposals, and Questions"
summary: "Keep one log in which every entry is clearly an approved decision, an open proposal or an unanswered question, with its source and approver."
region: context-library
level: explorer
xp: 20
estimated_minutes: 60
order: 110
tags:
  - context
  - decisions
  - traceability
tools:
  - Markdown
  - YAML
bookend: intent
risk:
  external_write: false
  sensitive_data: false
  notes: "The log is synthetic."
prerequisites:
  - base-camp-repository-safety
related_quests:
  - ba-extract-decisions
outcomes:
  - "Classify each entry by status."
  - "Record who approved a decision and where."
  - "Move an entry between states without losing its history."
proof:
  required:
    - id: decision-log
      type: file
      description: "Provide a log of at least ten entries across the three statuses, each with source, date and, for decisions, the approver, including at least one superseded decision linked to its replacement and a current-decisions view listing only decisions not superseded."
      path: participant/context/decisions/log.md
    - id: log-rules
      type: file
      description: "State what makes an entry a decision, how a proposal becomes one and how a decision is superseded."
      path: participant/context/decisions/rules.md
    - id: log-check
      type: command-record
      description: "Save the redacted output of a check that every decision has an approver and source, that no proposal is presented as decided and that a status change kept the earlier entry."
      path: participant/evidence/context-decision-log/attempt-001/logs/log-check.txt
    - id: proof-narrative
      type: file
      description: "Explain your approach, your choices and anything you could not do, citing the acceptance criteria by number."
      path: participant/evidence/context-decision-log/attempt-001/PROOF.md
author: Golden Thread maintainers
last_reviewed: "2026-10-20"
---

# Distinguish Approved Decisions, Proposals, and Questions

## Mission

Keep a log where the status of every entry is explicit, an approval is recorded with who and where, and a status change leaves a trail.

## Scenario

A proposal in a document is quoted in a ticket as the decision. Nobody approved it, but it now has three downstream stories.

## Acceptance criteria

1. Every entry has exactly one status: decision, proposal or question.
2. A decision records its approver and where it was approved.
3. A proposal is never shown as a decision.
4. Promoting a proposal to a decision adds an entry and keeps the history.
5. A superseded decision links to the one that replaced it.
6. Each entry cites its source.
7. A reader can find the current decisions without reading the history.

## Required evidence

Provide the log, the rules and the check. In your `PROOF.md`, explain how you tell an approval from agreement in conversation, citing the acceptance criteria by number.

## Safety constraints

- Use synthetic work items with invented identifiers; do not use a real project.
- This quest is read-only with respect to every external system, and no live connection is needed.
- Do not record a decision on someone's behalf.

## Hints

Agreement in a meeting is not the same as an approval. Decide what your project counts.

## Reflection

Which decision in your log would you least want to be asked about?

## Stretch goals

- Link decisions to the work items they affect.
- Report decisions with no downstream work.
