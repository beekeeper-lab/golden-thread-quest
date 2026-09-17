# Curriculum Backlog

This is the planned content inventory, not a requirement that all quests ship with application release one. Each row is intended to become one independently reviewable quest content file.

## Base Camp

| Proposed ID | Quest | Level |
|---|---|---|
| `base-camp-repository-safety` | Establish a safe local quest repository | Explorer |
| `base-camp-ownership-zones` | Enforce program, participant, generated, and private-data boundaries | Scout |
| `base-camp-secret-handling` | Configure authenticated CLI or environment-based secret handling | Explorer |
| `base-camp-write-preview` | Build preview and explicit-confirmation behavior | Builder |
| `base-camp-audit-log` | Record read, preview, confirmed write, failure, and recovery events | Explorer |
| `base-camp-safe-rerun` | Demonstrate idempotent rerun behavior | Builder |
| `base-camp-interruption-recovery` | Stop and resume without corruption or duplication | Builder |
| `base-camp-prompt-injection` | Resist instructions embedded in untrusted work content | Navigator |
| `base-camp-failure-lab` | Handle timeout, partial response, rate limit, and malformed data | Navigator |

## Jira Jungle

| Proposed ID | Quest | Level |
|---|---|---|
| `jira-compare-access-methods` | Compare CLI, REST API, MCP, and managed connector access | Scout |
| `jira-verify-connection` | Verify identity, scope, project visibility, and safe read access | Scout |
| `jira-list-projects` | Retrieve visible projects and preserve stable IDs | Scout |
| `jira-read-story` | Save one complete story as normalized Markdown | Explorer |
| `jira-read-assigned-stories` | Synchronize every story assigned to the current user | Builder |
| `jira-query-stories` | Run a configurable saved query with pagination | Explorer |
| `jira-read-hierarchy` | Preserve epic, story, task, and subtask relationships | Explorer |
| `jira-read-comments-history` | Synchronize comments and material change history without duplication | Builder |
| `jira-read-attachments` | Preserve attachment metadata without unsafe automatic downloads | Explorer |
| `jira-build-index` | Generate an indexed local Jira context catalog | Explorer |
| `jira-delta-sync` | Update only changed work while preserving local analysis | Navigator |
| `jira-detect-conflicts` | Report local/source field conflicts without silently choosing | Navigator |
| `jira-reconciliation-report` | Explain synchronized, missing, stale, conflicted, and failed items | Builder |
| `jira-duplicate-search` | Search likely duplicates before work creation | Explorer |
| `jira-create-story-preview` | Preview a complete new story without writing | Explorer |
| `jira-create-story` | Create an approved story and reconcile its key locally | Builder |
| `jira-create-subtask` | Add an approved subtask to an existing story | Builder |
| `jira-add-comment` | Preview and add an approved comment | Explorer |
| `jira-update-fields` | Preview and update supported fields safely | Builder |
| `jira-transition-status` | Validate workflow transition before approved status change | Builder |
| `jira-link-work` | Create approved issue relationships and verify them | Builder |
| `jira-idempotent-create` | Prevent duplicate item creation after interruption | Navigator |
| `jira-next-work` | Recommend the next Jira item from synchronized local context | Navigator |

## Trello Islands

Repeat the Jira concepts through Trello's model rather than mechanically translating field names.

| Proposed ID | Quest | Level |
|---|---|---|
| `trello-verify-connection` | Verify identity, scopes, and sandbox board access | Scout |
| `trello-read-board` | Synchronize board, lists, and cards | Explorer |
| `trello-read-card` | Preserve card fields, members, dates, labels, comments, and checklist | Explorer |
| `trello-read-assigned-cards` | Synchronize cards assigned to the current member | Builder |
| `trello-read-attachment-metadata` | Preserve safe attachment metadata | Explorer |
| `trello-build-index` | Generate board/list/card Markdown indexes | Explorer |
| `trello-delta-sync` | Update changed cards without duplicating local notes | Navigator |
| `trello-reconciliation-report` | Map local records to board, list, and card IDs | Builder |
| `trello-duplicate-search` | Detect likely duplicate cards | Explorer |
| `trello-create-card-preview` | Preview card creation | Explorer |
| `trello-create-card` | Create and reconcile an approved card | Builder |
| `trello-add-checklist-item` | Add an approved checklist item | Explorer |
| `trello-add-comment` | Add an approved comment | Explorer |
| `trello-move-card` | Preview and move a card between lists | Builder |
| `trello-update-card` | Update supported card fields safely | Builder |
| `trello-idempotent-write` | Recover from partial card writes without duplication | Navigator |
| `trello-next-work` | Recommend the next card from local context | Navigator |

## GitHub Caverns

| Proposed ID | Quest | Level |
|---|---|---|
| `github-verify-connection` | Verify authenticated identity, scopes, and repository access | Scout |
| `github-read-issue` | Save one issue and its context as local Markdown | Explorer |
| `github-read-assigned-issues` | Synchronize all issues assigned to the current user | Builder |
| `github-query-issues` | Retrieve by label, milestone, project, assignee, or saved query | Explorer |
| `github-read-comments-events` | Preserve comments and material timeline events | Builder |
| `github-build-index` | Generate repository issue indexes | Explorer |
| `github-delta-sync` | Update changed issues while preserving analysis | Navigator |
| `github-reconciliation-report` | Map local work to repository and issue number | Builder |
| `github-duplicate-search` | Search likely duplicates before issue creation | Explorer |
| `github-create-issue-preview` | Preview an issue using repository conventions | Explorer |
| `github-create-issue` | Create and reconcile an approved issue | Builder |
| `github-add-comment` | Add an approved comment | Explorer |
| `github-update-metadata` | Update labels, assignee, milestone, and project fields | Builder |
| `github-close-reopen` | Close or reopen with an audited reason | Builder |
| `github-link-delivery` | Link issue, PR, commit, CI, test, and evidence | Navigator |
| `github-pr-acceptance-review` | Compare pull-request behavior with acceptance criteria | Navigator |
| `github-idempotent-write` | Recover from partial issue writes without duplication | Navigator |
| `github-next-work` | Recommend the next issue from local context | Navigator |

## Context Library

| Proposed ID | Quest | Level |
|---|---|---|
| `context-canonical-work-item` | Define a cross-platform work-item model | Builder |
| `context-stable-identities` | Map source IDs without relying on filenames or titles | Explorer |
| `context-preserve-source-fields` | Normalize without erasing platform-specific data | Explorer |
| `context-local-notes-boundary` | Preserve human notes across synchronization | Explorer |
| `context-cross-system-duplicates` | Detect likely duplicate work across systems | Navigator |
| `context-cross-system-conflicts` | Report contradictory state across systems | Navigator |
| `context-staleness` | Detect context too old for a reliable answer | Builder |
| `context-dependency-map` | Build work and decision dependency indexes | Builder |
| `context-next-work` | Rank next work from local Markdown with cited reasons | Navigator |
| `context-daily-plan` | Build a capacity-aware daily plan | Builder |
| `context-decision-log` | Distinguish approved decisions, proposals, and questions | Explorer |
| `context-traceability-matrix` | Link intent, decisions, work, implementation, tests, and outcomes | Navigator |

## BA Ruins

| Proposed ID | Quest | Level |
|---|---|---|
| `ba-ingest-transcript` | Preserve speakers, timestamps, and source identity | Explorer |
| `ba-extract-decisions` | Separate decisions from proposals and discussion | Builder |
| `ba-extract-work-items` | Extract work with source citations | Builder |
| `ba-open-questions` | Capture unresolved questions and owners | Explorer |
| `ba-detect-ambiguity` | Identify vague, incomplete, contradictory, or untestable requirements | Navigator |
| `ba-clarification-questions` | Produce focused questions that materially change implementation | Builder |
| `ba-search-existing-work` | Search for related and duplicate work before creation | Builder |
| `ba-write-story` | Produce a story with value, scope, criteria, dependencies, and source | Builder |
| `ba-slice-story` | Split oversized work into independently valuable increments | Navigator |
| `ba-gwt-examples` | Add useful Given/When/Then examples without obscuring business criteria | Explorer |
| `ba-nonfunctional-analysis` | Identify applicable quality and operational requirements | Navigator |
| `ba-change-impact` | Trace change impact across requirements, code, tests, docs, and release | Navigator |
| `ba-meeting-to-backlog` | Complete an approved meeting-to-work-item workflow | Boss |

## Scrum Village

| Proposed ID | Quest | Level |
|---|---|---|
| `scrum-standup-digest` | Produce an evidence-based stand-up digest | Explorer |
| `scrum-sprint-health` | Report progress, aging work, blockers, WIP, and dependency risk | Builder |
| `scrum-scope-change` | Detect work added, removed, or materially changed after sprint start | Builder |
| `scrum-refinement-agenda` | Prioritize ambiguous, risky, dependent, or oversized work | Explorer |
| `scrum-review-agenda` | Build a demonstration agenda from completed, evidenced outcomes | Explorer |
| `scrum-retro-analysis` | Convert transcript themes into experiments, owners, and dates | Builder |
| `scrum-retro-follow-through` | Reconcile retrospective actions without duplication | Builder |
| `scrum-release-notes` | Generate release notes and flag evidence gaps | Builder |
| `scrum-stakeholder-summary` | Separate facts, risks, forecasts, and decision requests | Navigator |

## Playwright Labyrinth

| Proposed ID | Quest | Level |
|---|---|---|
| `playwright-risk-strategy` | Turn requirements and risk into a layered test strategy | Builder |
| `playwright-automation-candidates` | Explain what should and should not be automated | Explorer |
| `playwright-project-setup` | Create a documented Playwright project | Builder |
| `playwright-first-independent-test` | Build an independent, maintainable test | Builder |
| `playwright-page-model` | Centralize selectors and reusable page behavior | Builder |
| `playwright-stable-locators` | Replace generated IDs and brittle DOM paths | Explorer |
| `playwright-data-isolation` | Make tests order-neutral and responsible for data | Navigator |
| `playwright-tagging` | Tag by feature, risk, read/write, layer, and duration | Explorer |
| `playwright-multi-tag-run` | Run single and combined tag selections | Explorer |
| `playwright-api-assisted-test` | Combine API setup/verification with UI behavior | Navigator |
| `playwright-failure-evidence` | Capture trace, screenshot, log, request, and error context | Builder |
| `playwright-success-evidence` | Capture evidence at meaningful validation points | Explorer |
| `playwright-html-report` | Produce a useful execution report | Builder |
| `playwright-test-inventory` | Document every test, purpose, tags, source, and value score | Navigator |
| `playwright-high-value-rubric` | Define and consistently apply valuable-test criteria | Navigator |
| `playwright-coverage-report` | Map requirements to covered, partial, uncovered, and manual validation | Navigator |
| `playwright-failure-triage` | Classify bug, test defect, environment, data, or inconclusive | Navigator |
| `playwright-maintenance-report` | Recommend changes before modifying a failed test | Builder |
| `playwright-repair-test` | Repair a test without weakening business validation | Navigator |
| `playwright-defect-ticket` | Create a traceable, deduplicated defect after approval | Navigator |

## Hidden and adversarial challenges

These may be revealed during workshops or included as optional trap cards.

| Proposed ID | Challenge | Level |
|---|---|---|
| `trap-mimic-ticket` | A duplicate request resembles new work | Navigator |
| `trap-stale-map` | Local context is materially out of date | Navigator |
| `trap-three-system-hydra` | Jira, Trello, and GitHub disagree | Boss |
| `trap-cursed-instruction` | A ticket contains prompt injection | Boss |
| `trap-vanishing-path` | An API partially succeeds and then fails | Boss |
| `trap-flaky-phantom` | A test fails nondeterministically | Navigator |
| `trap-false-victory` | A proposed repair weakens the assertion | Boss |
