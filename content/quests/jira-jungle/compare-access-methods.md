---
id: jira-compare-access-methods
version: 1
title: "Compare CLI, REST API, MCP, and Managed Connector Access"
summary: "Compare four ways an agent can reach Jira and choose one for a stated purpose, with the trade-offs written down."
region: jira-jungle
level: scout
xp: 10
estimated_minutes: 45
order: 20
tags:
  - jira
  - access
  - decision
tools:
  - Markdown
  - YAML
bookend: foundation
risk:
  external_write: false
  sensitive_data: false
  notes: "No connection is made; the quest is a written comparison."
prerequisites:
  - base-camp-repository-safety
outcomes:
  - "Describe how each access method authenticates, what it can reach and what it logs."
  - "Compare them on security, reliability and effort."
  - "Choose one and record the reason."
proof:
  required:
    - id: comparison
      type: file
      description: "Provide a table comparing the four methods on authentication, whom actions are attributed to, scope of access, what is logged and where, rate limits, maintenance, failure behavior and one named risk each."
      path: participant/context/jira/access-comparison.md
    - id: decision
      type: file
      description: "Provide the decision record naming the method chosen for a stated purpose, the reason and what would make you change it."
      path: participant/context/jira/access-decision.md
    - id: proof-narrative
      type: file
      description: "Explain your approach, your choices and anything you could not do, citing the acceptance criteria by number."
      path: participant/evidence/jira-compare-access-methods/attempt-001/PROOF.md
author: Golden Thread maintainers
last_reviewed: "2026-10-20"
---

# Compare CLI, REST API, MCP, and Managed Connector Access

## Mission

Understand the choices before connecting anything. Compare how each method proves identity, how much it can reach, what it records and how it fails, and choose one for a purpose you state.

## Scenario

A team connects an agent to Jira using a colleague's personal token because it was quickest. Every change the agent makes is attributed to the colleague, and the token cannot be revoked without breaking the colleague's own work.

## Acceptance criteria

1. The comparison covers CLI, REST API, MCP and a managed connector.
2. Each method states how it authenticates and who the actions are attributed to.
3. Each method states the scope of access it grants.
4. Each method states what is logged and where.
5. The decision names a purpose and the method chosen for it.
6. The decision gives the reason and what would change it.
7. The comparison names a risk of each method.

## Required evidence

Provide the comparison and the decision. In your `PROOF.md`, explain the method you rejected most firmly, citing the acceptance criteria by number.

## Safety constraints

- No connection is made in this quest.
- Authenticate through an environment variable or a signed-in CLI; never put a token, password or session cookie in a file, a log or a screenshot.
- Do not paste a real token or an internal URL.

## Hints

Ask whose name appears on the action and how you would revoke access without breaking someone else.

## Reflection

Which method would you choose if the agent could only be trusted a little?

## Stretch goals

- Add a fifth method and compare it.
- Say how each method behaves during a Jira outage.
