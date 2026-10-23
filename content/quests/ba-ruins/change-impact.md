---
id: ba-change-impact
version: 1
title: "Trace Change Impact Across Requirements, Code, Tests, Docs, and Release"
summary: "Given a proposed change, trace what it touches in requirements, code, tests, documentation and release, and flag what you could not trace."
region: ba-ruins
level: navigator
xp: 50
estimated_minutes: 120
order: 120
tags:
  - business-analysis
  - impact-analysis
  - traceability
tools:
  - Markdown
  - YAML
bookend: cross-bookend
risk:
  external_write: false
  sensitive_data: false
  notes: "Use a small synthetic repository; do not analyze a real one."
prerequisites:
  - base-camp-repository-safety
outcomes:
  - "Trace a change through requirements, code, tests, docs and release."
  - "Cite where each impact was found."
  - "Report what could not be traced instead of assuming it is unaffected."
proof:
  required:
    - id: sample-repo
      type: directory
      description: "Provide a small synthetic repository with requirements, a little code, tests, docs and a release note, linked by identifiers."
      path: participant/context/impact/sample-repo
    - id: impact-report
      type: file
      description: "Provide the impact report for one proposed change, listing for each area the affected items, the evidence for each and the items that could not be traced."
      path: participant/context/impact/impact-report.md
    - id: trace-run
      type: command-record
      description: "Save the redacted output of the trace, including a check that every listed impact cites a file and that untraced areas are reported."
      path: participant/evidence/ba-change-impact/attempt-001/logs/trace-run.txt
    - id: proof-narrative
      type: file
      description: "Explain your approach, your choices and anything you could not do, citing the acceptance criteria by number."
      path: participant/evidence/ba-change-impact/attempt-001/PROOF.md
author: Golden Thread maintainers
last_reviewed: "2026-10-20"
---

# Trace Change Impact Across Requirements, Code, Tests, Docs, and Release

## Mission

Trace a proposed change across the places a project keeps its truth. For each place, show what is affected and how you know, and say plainly where the trace stops.

## Scenario

A rule about guest limits changes. The code is updated and the tests pass, but the printed guide still states the old limit and a requirement elsewhere contradicts the new one.

## Acceptance criteria

1. The report covers requirements, code, tests, documentation and release.
2. Each affected item cites the file where it was found.
3. A place with no impact states how that was checked.
4. Items that could not be traced are listed, not assumed unaffected.
5. Links rely on identifiers, not only on text search.
6. The trace does not change any file in the repository.
7. A reviewer can reproduce the trace from the sample repository.

## Required evidence

Provide the repository, the report and the trace output. In your `PROOF.md`, explain which link was hardest to find and which you could not trace, citing the acceptance criteria by number.

## Safety constraints

- Use only your synthetic repository.
- The trace is read-only.

## Hints

A trace that finds nothing is either a clean change or a weak search. Say which and why you believe it.

## Reflection

Where in a real project would this trace be weakest, and what would make it stronger?

## Stretch goals

- Estimate the work in each affected area.
- Show the trace from a test back to the requirement.
