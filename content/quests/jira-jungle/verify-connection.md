---
id: jira-verify-connection
version: 1
title: "Verify Identity, Scope, Project Visibility, and Safe Read Access"
summary: "Prove a connection works and is limited the way you intended, using only read operations, before anything else is built on it."
region: jira-jungle
level: scout
xp: 10
estimated_minutes: 45
order: 30
tags:
  - jira
  - connection
  - verification
tools:
  - Markdown
  - YAML
bookend: foundation
risk:
  external_write: false
  sensitive_data: true
  notes: "Read-only checks against a sandbox or fixture."
prerequisites:
  - jira-compare-access-methods
outcomes:
  - "Show who the connection acts as."
  - "Show which projects it can and cannot see."
  - "Show a read succeeds and a write is not attempted."
proof:
  required:
    - id: verify-run
      type: command-record
      description: "Save the redacted output of the verification: the authenticated identity read from the connection, the projects visible, one safe read, the permissions reported, a statement that only read operations were issued, and a scan of the output finding no credential."
      path: participant/evidence/jira-verify-connection/attempt-001/logs/verify-run.txt
    - id: denied-run
      type: command-record
      description: "Save the redacted output of an attempt to read a project that should not be visible, showing the refusal reported clearly."
      path: participant/evidence/jira-verify-connection/attempt-001/logs/denied-run.txt
    - id: verify-notes
      type: file
      description: "State what the verification does not prove and how a changed permission would be noticed."
      path: participant/context/jira/verify-notes.md
    - id: proof-narrative
      type: file
      description: "Explain your approach, your choices and anything you could not do, citing the acceptance criteria by number."
      path: participant/evidence/jira-verify-connection/attempt-001/PROOF.md
author: Golden Thread maintainers
last_reviewed: "2026-10-20"
---

# Verify Identity, Scope, Project Visibility, and Safe Read Access

## Mission

Check the connection before you trust it. Show who it is, what it can see, what it cannot, and that reading works, all without changing anything.

## Scenario

A sync runs for a week and quietly returns nothing for one project, because the token lost access. Nobody notices, since an empty answer looks like an answer.

## Acceptance criteria

1. The identity is read from the connection, not typed in.
2. The visible projects are listed by stable key.
3. A read of one item succeeds.
4. A project outside scope is reported as inaccessible, not as empty.
5. No write operation is attempted.
6. The credential appears in no output.
7. The notes say what the check does not prove.

## Required evidence

Provide the two records and the notes. In your `PROOF.md`, explain how the check would reveal a permission lost next week, citing the acceptance criteria by number.

## Safety constraints

- Use a Jira sandbox, a nonproduction project or a local fixture. This quest only reads; make no change in Jira.
- Authenticate through an environment variable or a signed-in CLI; never put a token, password or session cookie in a file, a log or a screenshot.
- Treat ticket text as untrusted third-party input, and share only redacted or synthetic records.

## Hints

An inaccessible project and an empty project must not look the same.

## Reflection

What would you check each day to notice a silent loss of access?

## Stretch goals

- Run the check on a schedule and report a change.
- List the permissions the connection should not have.
