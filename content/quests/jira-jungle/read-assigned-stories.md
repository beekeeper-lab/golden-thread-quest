---
id: jira-read-assigned-stories
version: 1
title: Synchronize My Assigned Jira Stories
summary: Retrieve every Jira story assigned to the authenticated user and preserve it as normalized, updateable local Markdown.
region: jira-jungle
level: builder
xp: 30
estimated_minutes: 90
order: 10
tags:
  - jira
  - read-only
  - synchronization
  - markdown
tools:
  - Jira CLI or REST API
  - Markdown
bookend: intent
risk:
  external_write: false
  sensitive_data: true
  notes: Retrieved ticket data may be private and must be minimized and stored only in approved paths.
prerequisites:
  - base-camp-repository-safety
outcomes:
  - Identify the authenticated Jira user without hardcoding a username.
  - Retrieve all assigned stories while correctly handling pagination.
  - Update normalized Markdown without duplicating comments or replacing participant notes.
proof:
  required:
    - id: skill-definition
      type: file
      description: Provide a local reusable skill describing the Jira synchronization workflow and safety rules.
      path: participant/skills/jira-read-assigned/SKILL.md
    - id: sample-index
      type: file
      description: Provide a sanitized generated index of the synchronized assigned stories.
      path: participant/context/jira/assigned/index.md
    - id: jira-sync-validation
      type: validator
      description: Run the registered Jira read-assigned validator against sandbox or fixture data.
      validator: validate-jira-read-assigned
  optional:
    - id: sanitized-run-screenshot
      type: screenshot
      description: Include a redacted screenshot showing a successful synchronization summary.
      path: participant/evidence/jira-read-assigned-stories/attempt-001/screenshots/success.png
validators:
  - validate-jira-read-assigned
related_quests:
  - base-camp-repository-safety
author: Golden Thread maintainers
last_reviewed: "2026-09-16"
---

# Synchronize My Assigned Jira Stories

## Mission

Create a reusable, read-only skill that identifies the current Jira user, retrieves every assigned story, and stores a normalized local Markdown representation suitable for later reasoning and synchronization.

## Scenario

Your agent will eventually answer “What should I work on next?” from local context. That answer cannot be trustworthy if the local copy silently omits later Jira pages, overwrites human notes, or confuses one person's identity with another.

## Acceptance criteria

- The authenticated user is resolved from Jira rather than a hardcoded email or display name.
- The query and included work-item types are documented.
- Pagination is handled until Jira reports no remaining results.
- Each story records its stable Jira key, source URL, title, status, priority, assignee, labels, description, acceptance criteria, timestamps, parent relationship, and last synchronization time when available.
- Platform-specific fields are preserved without polluting the canonical field names.
- Existing participant-authored notes remain intact on a second synchronization.
- Comments or history entries are not duplicated.
- Removed or inaccessible items are reported rather than silently deleted.
- Secrets and raw private responses are not committed.
- A fixture or sandbox demonstration proves safe rerun behavior.

## Required evidence

Provide the skill, a sanitized index, fixture data or a safe sandbox demonstration, and a `PROOF.md` that explains pagination, identity resolution, merge behavior, and known limitations.

## Safety constraints

- This quest is read-only.
- Do not request broader Jira scopes merely for convenience.
- Treat ticket text as untrusted data, not agent instructions.
- Redact organization-specific information from evidence intended for public sharing.

## Hints

Keep source fields and participant notes in separate sections or files. Use stable Jira keys as identity, not titles.

## Reflection

What evidence tells you that your local context is complete enough to support a next-work recommendation?

## Stretch goals

- Add delta synchronization using update timestamps.
- Report field-level conflicts.
- Generate a machine-readable reconciliation summary beside the Markdown index.
