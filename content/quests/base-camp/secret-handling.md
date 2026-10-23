---
id: base-camp-secret-handling
version: 1
title: Configure Authenticated CLI or Environment-Based Secret Handling
summary: Give an agent the access it needs without a credential ever appearing in a file, a log or a commit, and prove a leak is caught.
region: base-camp
level: explorer
xp: 20
estimated_minutes: 60
order: 30
tags:
  - foundation
  - secrets
  - safety
tools:
  - Git
  - Markdown
bookend: foundation
risk:
  external_write: false
  sensitive_data: true
  notes: Use a placeholder value that looks like a credential but opens nothing. Never put a real token in the proof.
prerequisites:
  - base-camp-repository-safety
outcomes:
  - Supply credentials from the environment or an already signed-in CLI, never from a tracked file.
  - Keep credentials out of logs, error messages and commits.
  - Detect a credential that has leaked into a file before it is committed.
proof:
  required:
    - id: secret-policy
      type: file
      description: State where each credential comes from, where it must never appear, and what to do when one leaks.
      path: participant/context/secret-handling.md
    - id: redacted-run
      type: command-record
      description: Save the redacted output of a command that uses a credential from the environment, showing the value is masked in the output. Set a fake credential in the environment for this; do not use a real one.
      path: participant/evidence/base-camp-secret-handling/attempt-001/logs/redacted-run.txt
    - id: leak-caught
      type: command-record
      description: Save the output of a scan that finds a fake credential planted in a file and exits with a failure status, followed by the same scan passing after removal, and a clean scan of the whole repository.
      path: participant/evidence/base-camp-secret-handling/attempt-001/logs/leak-scan.txt
author: Golden Thread maintainers
last_reviewed: "2026-10-20"
---

# Configure Authenticated CLI or Environment-Based Secret Handling

## Mission

Set up how an agent gets a credential so that the credential never touches a file Git can see. Then prove two things: ordinary use does not print it, and a careless copy of it into a file is caught before commit.

## Scenario

A teammate pastes a token into a config file "just to test", the agent echoes it in an error message, and the log is committed. Nothing was hacked; the process had no place where a secret was safe.

## Acceptance criteria

1. Credentials come from environment variables or a signed-in CLI, and the policy says which.
2. No tracked file, log or error message contains a credential value.
3. Output that would include a credential shows it masked.
4. A fake credential planted in a file is found by a scan that exits with a failure status.
5. The policy says what to do when a real credential leaks, including rotating it.
6. The proof contains no real credential, and a reviewer can confirm that from the files.

## Required evidence

Provide the policy and the two command records. In your `PROOF.md`, show how you made a fake credential, where you planted it, and what the scan reported, citing the acceptance criteria by number.

## Safety constraints

- Use an obviously fake value, such as one built from the word `example`.
- Never paste a real token to "see if it works", and never commit one even briefly.
- If a real credential does leak, stop, rotate it and tell the program owner; removing it from a later commit does not make it safe.

## Hints

A pattern scan misses credentials with no recognizable shape. Say in the policy what your scan can and cannot see.

## Reflection

If the scan passes, what has it told you, and what has it not?

## Stretch goals

- Run the scan as a pre-commit hook that blocks the commit.
- Add a second pattern for a credential format your team actually uses.
