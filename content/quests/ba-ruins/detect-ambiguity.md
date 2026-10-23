---
id: ba-detect-ambiguity
version: 1
title: "Identify Vague, Incomplete, Contradictory, and Untestable Requirements"
summary: "Review a requirements set for four kinds of defect and show each finding with the words that cause it and why a tester could not proceed."
region: ba-ruins
level: navigator
xp: 50
estimated_minutes: 120
order: 50
tags:
  - business-analysis
  - requirements
  - quality
tools:
  - Markdown
  - YAML
bookend: validation
risk:
  external_write: false
  sensitive_data: false
  notes: "Use a synthetic requirements set so that no real project's weaknesses are published."
prerequisites:
  - base-camp-repository-safety
outcomes:
  - "Classify a defect as vague, incomplete, contradictory or untestable."
  - "Quote the words responsible and say what is missing."
  - "Avoid flagging requirements that are fine."
proof:
  required:
    - id: requirements-set
      type: file
      description: "Provide a synthetic requirements set containing at least eight requirements, including some that are sound and at least one of each defect type, with a contradiction that spans two requirements."
      path: participant/context/ambiguity/requirements.md
    - id: findings
      type: file
      description: "Provide the findings, each with the requirement, the defect type, the quoted words and the question that would resolve it."
      path: participant/context/ambiguity/findings.md
    - id: false-positive-check
      type: command-record
      description: "Save the redacted output of running the review and the list of requirements it left unflagged, with a note on why each is sound."
      path: participant/evidence/ba-detect-ambiguity/attempt-001/logs/review-run.txt
    - id: proof-narrative
      type: file
      description: "Explain your approach, your choices and anything you could not do, citing the acceptance criteria by number."
      path: participant/evidence/ba-detect-ambiguity/attempt-001/PROOF.md
author: Golden Thread maintainers
last_reviewed: "2026-10-20"
---

# Identify Vague, Incomplete, Contradictory, and Untestable Requirements

## Mission

Review a requirements set for ambiguity. For every finding, show exactly which words fail and what the author would have to say for a tester to proceed. Leave the sound requirements alone.

## Scenario

A requirement says the page must load quickly. Everyone nods. The developer builds to two seconds, the tester expects half a second, and the customer meant on a hotel wifi connection.

## Acceptance criteria

1. Each finding names one of the four defect types.
2. Each finding quotes the specific words that cause it.
3. Each finding states what a tester could not decide.
4. A contradiction cites both requirements.
5. Sound requirements are listed as unflagged with a reason.
6. No finding rewrites the requirement; it asks the question that would resolve it.
7. A reviewer can reproduce the classification from the file alone.

## Required evidence

Provide the requirements set, the findings and the run output. In your `PROOF.md`, explain how you avoided flagging sound requirements and give one finding you removed on a second look, citing the acceptance criteria by number.

## Safety constraints

- Use only a synthetic requirements set.
- Do not criticize a named person's wording.

## Hints

Ask whether two testers would write the same test. If not, the requirement is vague or incomplete.

## Reflection

What fraction of your findings would a stakeholder call nitpicking, and how would you tell?

## Stretch goals

- Score each requirement by how much work it would take to make it testable.
- Detect contradictions across two documents.
