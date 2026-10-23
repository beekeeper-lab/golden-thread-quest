---
id: ba-nonfunctional-analysis
version: 1
title: "Identify Applicable Quality and Operational Requirements"
summary: "Work out which quality and operational requirements apply to a story, state each in measurable terms, and justify what does not apply."
region: ba-ruins
level: navigator
xp: 50
estimated_minutes: 120
order: 110
tags:
  - business-analysis
  - non-functional
  - quality
tools:
  - Markdown
  - YAML
bookend: validation
risk:
  external_write: false
  sensitive_data: false
  notes: "Use a synthetic story and invented numbers."
prerequisites:
  - ba-write-story
outcomes:
  - "Walk a checklist of quality areas against a real story."
  - "State applicable requirements with a measure."
  - "Record why an area does not apply."
proof:
  required:
    - id: nfr-story
      type: file
      description: "Provide the synthetic story the analysis is about, with numbered criteria."
      path: participant/context/nfr/story.md
    - id: nfr-checklist
      type: file
      description: "Provide the checklist of quality and operational areas you use, such as performance, accessibility, security, privacy, availability, auditability and supportability."
      path: participant/context/nfr/checklist.md
    - id: nfr-analysis
      type: file
      description: "Provide the analysis of one story: for each area, either a measurable requirement or a reasoned not-applicable."
      path: participant/context/nfr/analysis.md
    - id: nfr-check
      type: command-record
      description: "Save the redacted output of a check that every area on the checklist has an entry and that every applicable requirement has a number or a testable condition."
      path: participant/evidence/ba-nonfunctional-analysis/attempt-001/logs/nfr-check.txt
    - id: proof-narrative
      type: file
      description: "Explain your approach, your choices and anything you could not do, citing the acceptance criteria by number."
      path: participant/evidence/ba-nonfunctional-analysis/attempt-001/PROOF.md
author: Golden Thread maintainers
last_reviewed: "2026-10-20"
---

# Identify Applicable Quality and Operational Requirements

## Mission

Go beyond what the story says the system does. For each quality area, decide whether it applies, state it so a test could fail it, and record why you set aside the ones that do not apply.

## Scenario

A feature ships on time and works, then fails its first real day because nobody wrote down how many users, how fast, or what happens when the service is down.

## Acceptance criteria

1. Every checklist area has an entry for the story.
2. Each applicable requirement has a measure, a limit or a testable condition.
3. Each not-applicable entry gives a reason.
4. Where a number is unknown, it is marked as a question with an owner, not invented.
5. Requirements are tied to the story's criteria or flagged as new.
6. The analysis does not restate functional criteria.
7. A reviewer can see which requirements a tester must verify.

## Required evidence

Provide the checklist, the analysis and the check. In your `PROOF.md`, explain how you handled an area where you did not know the number, citing the acceptance criteria by number.

## Safety constraints

- Use a synthetic story and invented figures.
- Do not assert a real system's performance or compliance.

## Hints

Fast is not a requirement. Under two seconds for ninety-five percent of requests on the stated load is.

## Reflection

Which area did you want to mark not applicable only because it was hard?

## Stretch goals

- Link each requirement to the test that would verify it.
- Rank requirements by the cost of discovering them late.
