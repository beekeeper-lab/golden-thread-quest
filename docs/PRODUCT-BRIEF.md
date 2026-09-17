# Product Brief

## Product name

**The Golden Thread Quest**

Part of **The AI Context Engineer Journey**.

## Product promise

Give an aspiring AI Context Engineer a structured, self-paced path for building and demonstrating the agentic skills that connect human intent to verified software delivery.

## Role definition

An AI Context Engineer owns the two bookends of software delivery:

- **Intent bookend:** captures conversations, decisions, requirements, and constraints; structures local context; creates or updates actionable work; supports planning and prioritization.
- **Validation bookend:** translates intent into validation; creates manual and automated tests; evaluates failures; preserves evidence; communicates remaining risk.

The engineer protects the traceable connection between the two bookends.

## Primary users

### Participant

A business analyst, manual tester, Scrum facilitator, QA professional, developer, or technical analyst learning to build practical agentic workflows.

The participant needs to:

- understand the next useful challenge;
- work at an individual pace;
- build real repository artifacts;
- collect credible evidence;
- resume after interruption;
- distinguish completion from verified mastery;
- share a reviewable body of work.

### Reviewer or Questmaster

A facilitator, mentor, peer reviewer, or program owner who evaluates evidence.

The reviewer needs to:

- understand what the quest required;
- see the submitted artifacts and validation results;
- reproduce important behaviors;
- request changes with reasons;
- approve or reject verified completion;
- avoid handling participant secrets or unnecessary private data.

### Curriculum maintainer

A person adding quests, regions, badges, validators, or wording without changing UI code.

## Core user outcomes

1. A participant can discover an appropriate next quest.
2. A participant can understand success without needing hidden facilitator knowledge.
3. A participant can produce repo-native proof that survives beyond a screenshot.
4. The application can validate objective requirements without pretending to replace human review.
5. A reviewer can distinguish attempted, built, locally validated, submitted, and verified work.
6. A maintainer can add or revise curriculum through content files alone.
7. Participants can receive upstream curriculum updates without overwriting their work.

## Experience principles

### Professional before playful

Quest language should make progress memorable, but the application must look appropriate in a professional consulting or enterprise training environment.

### Evidence over checkboxes

A checked box is an assertion. Repository artifacts, reproducible instructions, validator results, demonstrations, and review decisions are evidence.

### Local-first and inspectable

Participant work remains in ordinary files and Git. The application enhances the repository; it does not imprison work in a database.

### Safe by default

Read-only operations are preferred. External writes are previewed. Secrets are never placed in curriculum, evidence, logs, or source control.

### Content drives presentation

Templates understand generic components, not individual quests. Valid content automatically appears everywhere it should.

### Progress remains honest

Claimed progress, automated validation, submission, and human verification are related but different states.

## Quest regions

The initial journey is organized into expandable regions:

1. **Base Camp** — Git, local context, security, auditability, and safe agent operation.
2. **Jira Jungle** — repeatable Jira read, synchronize, create, update, and reconcile workflows.
3. **Trello Islands** — the same conceptual workflows expressed through Trello's domain model.
4. **GitHub Caverns** — issue, pull request, repository, and delivery traceability.
5. **Context Library** — normalized local Markdown, cross-system reconciliation, search, and “what next?” reasoning.
6. **BA Ruins** — meeting-to-requirement analysis, ambiguity detection, story creation, and change impact.
7. **Scrum Village** — stand-ups, sprint health, refinement, retrospectives, and stakeholder reporting.
8. **Playwright Labyrinth** — risk-based tests, maintainable automation, evidence, triage, and test repair.

The names are labels, not separate hardcoded application features.

## Progress model

Quest progress uses these states:

- **Locked:** prerequisites are not satisfied.
- **Available:** prerequisites are satisfied; work has not started.
- **In progress:** participant began the quest.
- **Evidence ready:** participant assembled the required proof.
- **Locally validated:** automated validators passed.
- **Submitted:** participant requested review.
- **Needs changes:** reviewer found required corrections.
- **Verified:** reviewer approved the evidence.

XP may be displayed in two totals:

- **Earned/claimed XP:** based on participant progress.
- **Verified XP:** awarded only by a valid review decision.

## Proof hierarchy

The preferred proof order is:

1. Repository artifact
2. Reproducible instructions
3. Automated execution evidence
4. Peer demonstration
5. Reviewer approval

Screenshots are supporting evidence, not the default proof of implementation.

## First-release scope

The first release must provide:

- content loading and schema validation;
- generated HTML pages;
- Home, Map, Region/Catalog, Quest Detail, Evidence, Passport, Environment Health, and Reviewer views;
- local participant progress;
- evidence workspace creation;
- allowlisted validator execution;
- Git-aware status information;
- claimed and verified progress calculations;
- accessible and responsive presentation;
- sample content and authoring documentation;
- tests and audit documentation.

## Success measures

- A maintainer can add a quest without editing Python, templates, JavaScript, or CSS.
- Invalid curriculum fails with an actionable message before generation.
- A participant can resume work after restarting the local application.
- A validator cannot write outside its approved paths.
- A reviewer can reproduce an evidence package from repository instructions.
- Another person can clone the repository and run the application using the documented setup.
- Participant-owned files survive an upstream curriculum update.
