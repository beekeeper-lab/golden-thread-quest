---
id: context-cross-system-duplicates
version: 1
title: "Detect Likely Duplicate Work Across Systems"
summary: "Find items in different systems that probably describe the same work, show the evidence for each pair and never merge them without a person."
region: context-library
level: navigator
xp: 50
estimated_minutes: 120
order: 50
tags:
  - context
  - duplicates
  - cross-system
tools:
  - Markdown
  - YAML
bookend: validation
risk:
  external_write: false
  sensitive_data: false
  notes: "The records are synthetic."
prerequisites:
  - context-stable-identities
related_quests:
  - ba-search-existing-work
outcomes:
  - "Compare records from different systems using more than the title."
  - "Score and explain each candidate pair."
  - "Leave the merge decision to a person."
proof:
  required:
    - id: scoring-rules
      type: file
      description: "State each signal, its weight, how confidence is computed and the threshold above which a pair is proposed."
      path: participant/context/duplicates/scoring.md
    - id: multi-system-set
      type: file
      description: "Provide synthetic records from at least three systems including a true duplicate with different titles, a near duplicate and an unrelated look-alike with the same title."
      path: participant/context/duplicates/records.md
    - id: duplicate-report
      type: file
      description: "Provide the report of candidate pairs with the signals, a confidence and a recommendation for each, and the pairs rejected."
      path: participant/context/duplicates/report.md
    - id: duplicate-run
      type: command-record
      description: "Save the redacted output of the detection run, showing no record merged or changed, and that a look-alike with the same title was not reported as a duplicate."
      path: participant/evidence/context-cross-system-duplicates/attempt-001/logs/duplicate-run.txt
    - id: proof-narrative
      type: file
      description: "Explain your approach, your choices and anything you could not do, citing the acceptance criteria by number."
      path: participant/evidence/context-cross-system-duplicates/attempt-001/PROOF.md
author: Golden Thread maintainers
last_reviewed: "2026-10-20"
---

# Detect Likely Duplicate Work Across Systems

## Mission

Detect probable duplicates across systems using several signals, say why each pair was proposed, and keep the decision with a human.

## Scenario

The same bug is reported in the tracker, as a card on a board and as an issue in the repository. Three people fix it three ways.

## Acceptance criteria

1. Detection uses at least three signals beyond title, such as description, links, component and dates.
2. Each candidate pair lists the signals that matched and a confidence.
3. A look-alike with a matching title but different substance is not reported as a duplicate.
4. A true duplicate with different titles is found.
5. No record is merged, changed or deleted by detection.
6. Rejected pairs are listed with the reason.
7. A reviewer can reproduce the confidence from the listed signals.

## Required evidence

Provide the records, the report and the run output. In your `PROOF.md`, explain how you tuned your threshold and the pair you found hardest, citing the acceptance criteria by number.

## Safety constraints

- Use synthetic work items with invented identifiers; do not use a real project.
- This quest is read-only with respect to every external system, and no live connection is needed.
- Do not act on a suggested duplicate in any real system.

## Hints

Titles lie. Links, component and reporter often agree when titles do not.

## Reflection

Which is worse in your setting, a missed duplicate or a false one, and how did that shape the threshold?

## Stretch goals

- Cluster duplicates into groups of three or more.
- Learn weights from pairs you confirmed.
