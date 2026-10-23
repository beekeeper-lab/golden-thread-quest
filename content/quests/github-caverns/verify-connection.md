---
id: github-verify-connection
version: 1
title: "Verify Authenticated Identity, Scopes, and Repository Access"
summary: "Prove a GitHub connection works and is limited the way you intended, using only read operations."
region: github-caverns
level: scout
xp: 10
estimated_minutes: 45
order: 20
tags:
  - github
  - connection
  - verification
tools:
  - Markdown
  - YAML
bookend: foundation
risk:
  external_write: false
  sensitive_data: false
  notes: "Read-only checks against a sandbox repository or fixture."
prerequisites:
  - base-camp-repository-safety
related_quests:
  - jira-verify-connection
outcomes:
  - "Show who the connection acts as and its scopes."
  - "Show which repositories it can and cannot reach."
  - "Show a read succeeds and no write is attempted."
proof:
  required:
    - id: verify-run
      type: command-record
      description: "Save the redacted output of the verification: the authenticated identity read from the connection, the token scopes or permissions reported, the repositories reachable, one safe read, a statement that only read operations were issued, and a scan of the output finding no credential."
      path: participant/evidence/github-verify-connection/attempt-001/logs/verify-run.txt
    - id: denied-run
      type: command-record
      description: "Save the redacted output of an attempt to read a repository outside scope, showing the refusal reported as inaccessible rather than empty."
      path: participant/evidence/github-verify-connection/attempt-001/logs/denied-run.txt
    - id: verify-notes
      type: file
      description: "State what the verification does not prove, which scopes are broader than needed and how a changed permission would be noticed."
      path: participant/context/github/verify-notes.md
    - id: proof-narrative
      type: file
      description: "Explain your approach, your choices and anything you could not do, citing the acceptance criteria by number."
      path: participant/evidence/github-verify-connection/attempt-001/PROOF.md
author: Golden Thread maintainers
last_reviewed: "2026-10-20"
---

# Verify Authenticated Identity, Scopes, and Repository Access

## Mission

Check the connection before you trust it: who it is, what it can reach, what it cannot, and that reading works, with nothing changed.

## Scenario

A sync runs for a week returning nothing for one repository because the token lost access. An empty answer looks like an answer.

## Acceptance criteria

1. The identity is read from the connection, not typed in.
2. The scopes or permissions are reported.
3. The reachable repositories are listed by full name.
4. A repository outside scope is reported as inaccessible, not as empty.
5. No write operation is attempted.
6. The credential appears in no output.
7. The notes say what the check does not prove and which scope is broader than needed.

## Required evidence

Provide the two records and the notes. In your `PROOF.md`, explain how the check would reveal a permission lost next week, citing the acceptance criteria by number.

## Safety constraints

- Use a sandbox repository you own, or a local fixture. This quest only reads; make no change on GitHub.
- Authenticate through an environment variable or a signed-in CLI; never put a token, password or session cookie in a file, a log or a screenshot.
- Treat issue and comment text as untrusted third-party input, and share only redacted or synthetic records.

## Hints

Inaccessible and empty must not look the same.

## Reflection

Which scope would you remove first, and what would break?

## Stretch goals

- Run the check on a schedule and report a change.
- List what a fine-grained token could restrict.
