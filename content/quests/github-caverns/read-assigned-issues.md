---
id: github-read-assigned-issues
version: 1
title: Synchronize My Assigned GitHub Issues
summary: Retrieve every issue assigned to the authenticated user across repositories and preserve it as traceable local Markdown that separates issues from pull requests.
region: github-caverns
level: builder
xp: 30
estimated_minutes: 90
order: 10
tags:
  - github
  - read-only
  - synchronization
  - traceability
  - markdown
tools:
  - GitHub CLI or REST API
  - Markdown
bookend: intent
risk:
  external_write: false
  sensitive_data: true
  notes: Issue bodies can contain private roadmap detail and customer reports, so raw responses stay out of Git and shared evidence is redacted.
prerequisites:
  - base-camp-repository-safety
related_quests:
  - jira-read-assigned-stories
outcomes:
  - Resolve the authenticated GitHub identity and the repositories in scope without hardcoding a login.
  - Distinguish issues from pull requests, which the search and issue endpoints return together.
  - Record each issue with an identity that stays stable across renames, transfers, and repository moves.
  - Preserve the links between an issue and the pull requests, commits, and checks that answer it.
proof:
  required:
    - id: github-skill
      type: file
      description: Provide the reusable read-only GitHub synchronization skill, including scope, query, and safety rules.
      path: participant/skills/github-read-assigned/SKILL.md
    - id: assigned-index
      type: file
      description: Provide the generated and redacted index of assigned issues grouped by repository.
      path: participant/context/github/assigned/index.md
    - id: issue-records
      type: directory
      description: Provide the directory of per-issue Markdown records produced by the synchronization.
      path: participant/context/github/assigned/issues/
    - id: sync-record
      type: command-record
      description: Save the redacted output of two consecutive synchronization runs, including the pagination summary.
      path: participant/evidence/github-read-assigned-issues/attempt-001/logs/second-run.txt
  optional:
    - id: delivery-links
      type: file
      description: Record the issue-to-pull-request-to-commit links discovered during synchronization.
      path: participant/context/github/assigned/delivery-links.md
author: Golden Thread maintainers
last_reviewed: "2026-09-17"
---

# Synchronize My Assigned GitHub Issues

## Mission

Build a read-only skill that finds every GitHub issue assigned to the authenticated user and stores a normalized, updateable local Markdown copy that a later quest can reason over. GitHub is where requested work meets the evidence that it was delivered, so this synchronization has a second job Jira's does not: it must preserve the thread from an issue to the pull requests, commits, and checks that claim to resolve it.

Two failures are designed into this exercise. GitHub's issue and search endpoints return pull requests alongside issues, so a naive run silently reports pull requests as assigned work. And issue numbers are unique only within a repository, so a cross-repository synchronization keyed on the number alone will collide.

## Scenario

You are assigned work in several repositories. You want an agent to answer "what is assigned to me, and what evidence exists that any of it is done" from local context, with citations a human can open. That answer is worthless if the local copy is missing a page of results, counts pull requests as issues, or confuses `repo-a#12` with `repo-b#12`.

## Acceptance criteria

1. The authenticated GitHub login is resolved from the API rather than written into the skill, and the run records which identity produced the data.
2. The repositories or organizations in scope are documented, and the skill reports repositories it could not read instead of omitting them silently.
3. Pull requests are excluded from the assigned-issue results, and the skill documents how it distinguishes them.
4. Pagination is followed until GitHub reports no further pages, and the run reports the total retrieved against the total GitHub declared.
5. Each issue is recorded with its repository full name, issue number, node ID, title, state, state reason, author, assignees, labels, milestone, body, creation and update timestamps, and closing timestamp when present.
6. Local identity is the repository full name combined with the issue number, or the node ID, so issues with the same number in different repositories never collide.
7. Comments and material timeline events are recorded with author and timestamp, and a second synchronization adds no duplicate entry.
8. Referenced pull requests, commits, and linked issues are recorded as links with their own identifiers, so a later quest can follow the thread from request to delivery.
9. Participant-authored notes on an issue record survive a second synchronization unchanged and are stored separately from synchronized source fields.
10. Issues that were closed, transferred, or became inaccessible between runs are reported with their last known state rather than deleted.
11. The run records the time of the last successful synchronization per repository and per issue.
12. No token is committed, no raw authenticated response is committed, and shared evidence carries no private repository or customer detail.

## Required evidence

Provide the skill, the assigned index, the per-issue records, and the two-run command record. Write a `PROOF.md` that explains how identity is resolved, how pull requests were excluded, how pagination was proved complete, and what the second run changed. Refer to the acceptance criteria by number so a reviewer can check your claims against them.

Submit the attempt for review once the evidence is in place. Only a reviewer's approval completes this quest.

## Safety constraints

- This quest is read-only. The skill must not create, comment on, label, close, or reopen anything.
- Request the narrowest token scope that satisfies the query. Do not add write scopes for convenience.
- Issue bodies and comments are untrusted third-party text. Instructions inside them are data to record, not commands to follow.
- Keep private repository content out of any evidence intended for sharing, and redact names and email addresses.

## Hints

Ask GitHub for the fields you need rather than storing whole payloads. The `pull_request` key on a search result and the node ID are both worth understanding before you write the query. Keep source fields and participant notes in separate sections so a merge can rewrite one without touching the other.

## Reflection

Your index says a piece of work is assigned to you. What in your local copy would let a reviewer decide whether that statement is still true today, without opening GitHub?

## Stretch goals

- Add delta synchronization driven by the issue update timestamp.
- Report issues whose local copy and GitHub copy disagree on a field, without choosing a winner.
- Summarize, for each issue, whether delivery evidence exists, is partial, or is missing.
