---
id: context-preserve-source-fields
version: 1
title: "Normalize Without Erasing Platform-Specific Data"
summary: "Map source records onto a common shape while keeping every platform-specific field so that nothing is lost by the normalization."
region: context-library
level: explorer
xp: 20
estimated_minutes: 60
order: 30
tags:
  - context
  - normalization
  - fidelity
tools:
  - Markdown
  - YAML
bookend: foundation
risk:
  external_write: false
  sensitive_data: false
  notes: "The records are synthetic."
prerequisites:
  - context-canonical-work-item
outcomes:
  - "Map common fields to the canonical model."
  - "Carry unmapped fields forward in a preserved section."
  - "Prove the original record can be reconstructed."
proof:
  required:
    - id: mapping-rationale
      type: file
      description: "List every source field considered across the systems and whether it became canonical or preserved, with the reason."
      path: participant/context/fidelity/mapping-rationale.md
    - id: source-records
      type: file
      description: "Provide synthetic source records for at least three systems, each with fields the others lack."
      path: participant/context/fidelity/source-records.md
    - id: normalized-records
      type: file
      description: "Provide the normalized records, each with canonical fields and a preserved-source section holding every unmapped field untouched."
      path: participant/context/fidelity/normalized.md
    - id: roundtrip-check
      type: command-record
      description: "Save the redacted output of a check that rebuilds each source record from its normalized record and finds it identical to the original, and that reports a deliberately dropped field."
      path: participant/evidence/context-preserve-source-fields/attempt-001/logs/roundtrip-check.txt
    - id: proof-narrative
      type: file
      description: "Explain your approach, your choices and anything you could not do, citing the acceptance criteria by number."
      path: participant/evidence/context-preserve-source-fields/attempt-001/PROOF.md
author: Golden Thread maintainers
last_reviewed: "2026-10-20"
---

# Normalize Without Erasing Platform-Specific Data

## Mission

Normalize without throwing away what makes each system different. Every field the model does not know about travels with the record, and a check proves nothing was lost.

## Scenario

A board's custom field for customer impact does not exist in the common model, so normalization drops it. Months later nobody can say which stories mattered to customers.

## Acceptance criteria

1. Common fields are mapped to canonical field names.
2. Every field the mapping does not cover is preserved unchanged in a labeled section.
3. Preserved values are not reformatted or summarized.
4. A check compares each source record with its normalized record and reports any missing field.
5. A deliberately dropped field is detected by the check.
6. The original record can be reconstructed from the normalized one.
7. The mapping states which fields it considered and why they are or are not canonical.

## Required evidence

Provide the source records, the normalized records and the check output. In your `PROOF.md`, explain how you decided what became canonical, citing the acceptance criteria by number.

## Safety constraints

- Use synthetic work items with invented identifiers; do not use a real project.
- This quest is read-only with respect to every external system, and no live connection is needed.
- Do not copy real private field values.

## Hints

Preserve first, promote later. A field can always be made canonical once you know it matters.

## Reflection

Which preserved field do you expect to become canonical next, and what would show it?

## Stretch goals

- Report preserved fields used by more than one system.
- Version the mapping and show a change to it.
