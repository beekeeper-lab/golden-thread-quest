---
id: base-camp-repository-safety
version: 1
title: Establish a Safe Local Quest Repository
summary: Create the ownership, secret-handling, audit, and recovery foundations needed for trustworthy agentic work.
region: base-camp
level: explorer
xp: 20
estimated_minutes: 60
order: 10
tags:
  - foundation
  - git
  - safety
  - audit
tools:
  - Git
  - Markdown
bookend: foundation
risk:
  external_write: false
  sensitive_data: true
  notes: The exercise must prove that credentials and private raw responses remain outside Git.
outcomes:
  - Separate program-owned, participant-owned, and generated files.
  - Keep credentials and raw private responses outside source control.
  - Record agent actions and recover safely after interruption.
proof:
  required:
    - id: ownership-document
      type: file
      description: Document the repository ownership zones and the files each actor may modify.
      path: participant/context/repository-ownership.md
    - id: audit-log
      type: file
      description: Provide a human-readable audit log containing at least one read action and one previewed write action.
      path: participant/context/audit-log.md
    - id: repository-foundation-validation
      type: validator
      description: Run the registered repository-foundation validator successfully.
      validator: validate-repository-foundation
  optional:
    - id: recovery-demonstration
      type: demonstration
      description: Demonstrate stopping and safely resuming an agent workflow without duplicate output.
validators:
  - validate-repository-foundation
author: Golden Thread maintainers
last_reviewed: "2026-09-16"
---

# Establish a Safe Local Quest Repository

## Mission

Create a local, Git-based workspace that an AI agent can use without confusing curriculum files, participant work, generated output, private runtime data, and credentials.

## Scenario

You are preparing to build skills that connect to Jira, Trello, GitHub, meeting transcripts, and test systems. Before any integration begins, a reviewer must be able to tell what the agent may read, what it may change, what should be committed, and how an interrupted operation will be recovered.

## Acceptance criteria

1. The repository documents program-owned, participant-owned, and generated areas.
2. Credentials come from environment variables, an authenticated CLI, or an approved credential store.
3. Generated output and private runtime responses are ignored by Git.
4. External writes are previewed and require explicit human confirmation.
5. The audit log identifies time, action, target, initiating actor, outcome, and whether a write was confirmed.
6. Rerunning the demonstrated workflow does not duplicate the simulated external item.
7. Another person can understand the structure without asking the AI to explain it.

## Required evidence

Document the structure and safety rules, add representative audit entries, and run the registered validator. In your `PROOF.md`, explain how you tested interruption and rerun behavior.

## Safety constraints

- Use fake or sandbox targets.
- Never commit a real token, session cookie, raw authenticated response, or private transcript.
- Do not demonstrate cleanup with a recursive command aimed at an unresolved environment variable.

## Hints

Prefer narrow, explicit paths. A strong solution makes the safe path easy and an unsafe write visibly difficult.

## Reflection

Which safety rule is enforced by code, which is enforced by repository structure, and which still depends on human judgment?

## Stretch goals

- Add a pre-commit secret scan.
- Add a test proving cleanup cannot delete participant files.
- Add a dry-run transcript showing the exact external write that would occur.
