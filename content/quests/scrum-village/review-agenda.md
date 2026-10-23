---
id: scrum-review-agenda
version: 1
title: "Build a Demonstration Agenda from Completed, Evidenced Outcomes"
summary: "Assemble a sprint review agenda from finished work that has evidence of being finished, and list finished work that has none."
region: scrum-village
level: explorer
xp: 20
estimated_minutes: 60
order: 50
tags:
  - scrum
  - sprint-review
  - evidence
tools:
  - Markdown
  - YAML
bookend: validation
risk:
  external_write: false
  sensitive_data: false
  notes: "The sprint data and evidence are synthetic."
prerequisites:
  - base-camp-repository-safety
related_quests:
  - scrum-release-notes
outcomes:
  - "Include only work that is done and has linked evidence."
  - "Order items by what stakeholders care about."
  - "Report done items with no evidence as a gap."
proof:
  required:
    - id: completed-work
      type: file
      description: "Provide a synthetic list of work items, completed and unfinished, some completed ones with linked evidence files in a synthetic evidence folder and some without."
      path: participant/context/scrum/review/completed.md
    - id: review-agenda
      type: file
      description: "Provide the agenda listing each demonstrable outcome, its evidence link and a minutes allowance, the time box, the ordering rule, what was left out, and a separate section for done work lacking evidence."
      path: participant/context/scrum/review/agenda.md
    - id: agenda-check
      type: command-record
      description: "Save the redacted output of a check that every agenda item has an evidence link that exists and that no unfinished item appears."
      path: participant/evidence/scrum-review-agenda/attempt-001/logs/agenda-check.txt
    - id: proof-narrative
      type: file
      description: "Explain your approach, your choices and anything you could not do, citing the acceptance criteria by number."
      path: participant/evidence/scrum-review-agenda/attempt-001/PROOF.md
author: Golden Thread maintainers
last_reviewed: "2026-10-20"
---

# Build a Demonstration Agenda from Completed, Evidenced Outcomes

## Mission

Build a review agenda from facts. Only finished work with evidence is on it. Finished work with no evidence is listed apart, so the team can fix the gap rather than skip it.

## Scenario

A review demonstrates a feature that was not finished, and skips one that was, because nobody could show it. Stakeholders leave with the wrong picture.

## Acceptance criteria

1. Every agenda item is a completed work item.
2. Every agenda item links evidence that exists.
3. Done items without evidence appear in a separate gap section.
4. Unfinished or partly finished items do not appear on the agenda.
5. The agenda fits a stated time box and says what was left out.
6. Items are ordered by a stated rule.
7. The agenda opens with a one-line summary of the outcomes it covers.

## Required evidence

Provide the completed list, the agenda and the check. In your `PROOF.md`, explain how you treated a partly finished item, citing the acceptance criteria by number.

## Safety constraints

- Use synthetic data with invented names, dates and work items.
- Nothing in this exercise is posted to a tracker, chat channel or email.
- Do not link real internal systems.

## Hints

Done with no evidence is a finding, not a failure to hide.

## Reflection

Which outcome would be hardest to demonstrate, and what does that tell you about how it was built?

## Stretch goals

- Suggest a demonstrator for each item from the assignee field.
- Add a short script of what to show.
