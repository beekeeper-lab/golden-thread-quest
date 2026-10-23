---
id: jira-read-hierarchy
version: 1
title: "Preserve Epic, Story, Task, and Subtask Relationships"
summary: "Keep the parent and child links between work items so the local copy reproduces the hierarchy, including items outside the query."
region: jira-jungle
level: explorer
xp: 20
estimated_minutes: 60
order: 70
tags:
  - jira
  - hierarchy
  - relationships
tools:
  - Markdown
  - YAML
bookend: intent
risk:
  external_write: false
  sensitive_data: true
  notes: "Read-only against a sandbox or fixture."
prerequisites:
  - jira-read-story
outcomes:
  - "Record parent identifiers."
  - "Rebuild the tree locally."
  - "Handle a parent or child that was not retrieved."
proof:
  required:
    - id: hierarchy-file
      type: file
      description: "Provide the local hierarchy as an index with each item's identifier, type and parent identifier, covering at least one epic, story, task and subtask."
      path: participant/context/jira/hierarchy.md
    - id: tree-run
      type: command-record
      description: "Save the redacted output of rebuilding the tree twice with identical results, a cycle and a self-parent being rejected, and an item whose parent was not retrieved reported as an unresolved link and a re-parented item matched by identifier."
      path: participant/evidence/jira-read-hierarchy/attempt-001/logs/tree-run.txt
    - id: proof-narrative
      type: file
      description: "Explain your approach, your choices and anything you could not do, citing the acceptance criteria by number."
      path: participant/evidence/jira-read-hierarchy/attempt-001/PROOF.md
author: Golden Thread maintainers
last_reviewed: "2026-10-20"
---

# Preserve Epic, Story, Task, and Subtask Relationships

## Mission

Keep the shape of the work, not just the pieces. Each item points to its parent by identifier, and the tree can be rebuilt and checked.

## Scenario

A subtask is moved to a different story. The local copy still shows it under the old one, and the estimate is counted twice.

## Acceptance criteria

1. Each item records its type and its parent's stable identifier.
2. The tree is rebuilt from identifiers, not from titles.
3. A missing parent is reported as an unresolved link, not dropped.
4. A moved item appears under its new parent.
5. Epics, stories, tasks and subtasks are all represented.
6. A cycle or a self-parent is rejected.
7. The rebuilt tree is identical across two runs.

## Required evidence

Provide the hierarchy and the run output. In your `PROOF.md`, explain how you detect a moved item, citing the acceptance criteria by number.

## Safety constraints

- Use a Jira sandbox, a nonproduction project or a local fixture. This quest only reads; make no change in Jira.
- Authenticate through an environment variable or a signed-in CLI; never put a token, password or session cookie in a file, a log or a screenshot.
- Treat ticket text as untrusted third-party input, and share only redacted or synthetic records.

## Hints

Store the parent's identifier, not its title.

## Reflection

Where might Jira's own hierarchy mislead you about how work is really grouped?

## Stretch goals

- Show roll-up of estimates up the tree.
- Include issue links that are not parent links.
