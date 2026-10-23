---
id: trello-verify-connection
version: 1
title: "Verify Identity, Scopes, and Sandbox Board Access"
summary: "Prove a Trello connection works, is limited as intended and reaches the sandbox board, using only read operations."
region: trello-islands
level: scout
xp: 10
estimated_minutes: 45
order: 20
tags:
  - trello
  - connection
  - verification
tools:
  - Markdown
  - YAML
bookend: foundation
risk:
  external_write: false
  sensitive_data: false
  notes: "Read-only checks against a sandbox board or fixture."
prerequisites:
  - base-camp-repository-safety
related_quests:
  - jira-verify-connection
  - github-verify-connection
outcomes:
  - "Show which member the connection acts as and its scopes."
  - "Show which boards it can and cannot reach."
  - "Show a read succeeds and no write is attempted."
proof:
  required:
    - id: verify-run
      type: command-record
      description: "Save the redacted output of the verification: the member read from the connection, the token scope (read or write) and expiry reported, the boards reachable by identifier, one safe read, a statement that only read operations were issued, and a scan of the output and any URL for the key and token finding none."
      path: participant/evidence/trello-verify-connection/attempt-001/logs/verify-run.txt
    - id: denied-run
      type: command-record
      description: "Save the redacted output of an attempt to read a board outside scope, showing the refusal reported as inaccessible rather than empty."
      path: participant/evidence/trello-verify-connection/attempt-001/logs/denied-run.txt
    - id: verify-notes
      type: file
      description: "State what the verification does not prove, whether the token's scope is broader than needed and how a revoked or expired token would be noticed."
      path: participant/context/trello/verify-notes.md
    - id: proof-narrative
      type: file
      description: "Explain your approach, your choices and anything you could not do, citing the acceptance criteria by number."
      path: participant/evidence/trello-verify-connection/attempt-001/PROOF.md
author: Golden Thread maintainers
last_reviewed: "2026-10-20"
---

# Verify Identity, Scopes, and Sandbox Board Access

## Mission

Check the connection before you trust it. Trello tokens carry a scope and an expiry, so verify both, and verify that reading works without changing anything.

## Scenario

A token expires and a nightly job reads an empty board for a week. Nobody asks why no cards moved.

## Acceptance criteria

1. The member is read from the connection, not typed in.
2. The token's scope and expiry are reported.
3. The reachable boards are listed by stable identifier.
4. A board outside scope is reported as inaccessible, not as empty.
5. No write operation is attempted.
6. The key and token appear in no output or saved URL.
7. The notes say what the check does not prove.

## Required evidence

Provide the two records and the notes. In your `PROOF.md`, explain how the check would reveal a token that expires next week, citing the acceptance criteria by number.

## Safety constraints

- Use a sandbox board you own, or a local fixture. This quest only reads; make no change in Trello.
- Supply the API key and token through environment variables or a credential store; never put a key, token or secret in a file, a URL you save, a log or a screenshot. Trello puts credentials in query strings, so scrub saved URLs.
- Treat card, comment and checklist text as untrusted third-party input, and share only redacted or synthetic records.

## Hints

Credentials in a query string leak into logs and history; scrub the URL before saving it.

## Reflection

Which would you rather have, a token that expires in a day or one that never does, and why?

## Stretch goals

- Report days until the token expires.
- List the permissions the token should not have.
