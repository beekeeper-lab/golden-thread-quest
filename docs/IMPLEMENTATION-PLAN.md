# Claude Code Implementation Plan

## How to use this file

This file is both the implementation backlog and restart point.

Claude must:

1. Work from the earliest incomplete stage.
2. Complete only one stage at a time.
3. Check an item only after its acceptance behavior and tests pass.
4. Update the stage log before stopping.
5. Audit the stage before advancing.
6. Fix blocking and high findings.
7. Rerun the audit and record the final result.

Do not check the stage heading until its audit passes.

## Global implementation rules

- [ ] Work occurs in a feature branch, never directly on `main`.
- [ ] Existing participant-owned files are preserved.
- [ ] Changes remain within the current stage unless a documented prerequisite requires otherwise.
- [ ] Every behavior change includes appropriate tests.
- [ ] No test is weakened or deleted merely to obtain a passing build.
- [ ] No generated file becomes an undocumented source of truth.
- [ ] No external write occurs without preview and explicit confirmation.
- [ ] Every architecture deviation is recorded in `docs/DECISIONS.md`.

---

## Stage 0 — Planning and feasibility audit

**Goal:** Confirm that this package is internally consistent, feasible, safe, and specific enough to implement.

### Tasks

- [x] Read the files listed in `CLAUDE.md` in order.
- [x] Inspect all schemas, examples, fixtures, and prototype screens.
- [x] Compare every required screen to the component catalog.
- [x] Compare content examples to schema requirements.
- [x] Identify duplicated, contradictory, missing, or untestable requirements.
- [x] Identify security assumptions needing proof or revision.
- [x] Confirm the Python/Jinja/local-service approach satisfies the first-release scope.
- [x] Recommend final package choices for Python versions, schema library, Markdown renderer, local service, test runner, formatter, and linter.
- [x] Record accepted choices in `docs/DECISIONS.md`.
- [x] Create `docs/audits/stage-00-planning-audit.md`.
- [x] Correct the planning package or document approved deviations.

### Audit gate

- [x] No unresolved blocking finding.
- [x] No unresolved high-severity contradiction.
- [x] Every deferred implementation choice has an owner and decision point.
- [x] The prototype and written specification agree on primary behavior.
- [x] Audit rerun result is `pass` or `pass-with-advisories`.

### Stage completion

- [x] **Stage 0 complete and audited**

---

## Stage 1 — Repository and engineering foundation

**Goal:** Establish a reproducible, secure Python project without implementing product behavior prematurely.

### Tasks

- [x] Create the production package structure described in `docs/ARCHITECTURE.md`. (`participant/` deferred to Stage 4 — see audit L5.)
- [x] Create `pyproject.toml` with supported Python range and pinned-compatible dependencies.
- [x] Configure formatting, linting, type checking, and tests.
- [x] Configure a task runner or documented commands for setup, lint, test, build, and serve.
- [x] Add `.gitignore` entries for generated output, runtime data, credentials, caches, raw API responses, and common secret files.
- [x] Add a safe example environment file containing no secrets.
- [x] Add pre-commit or equivalent local checks without making setup opaque.
- [x] Add CI that runs format verification, lint, type checks, unit tests, schema tests, and secret scanning.
- [x] Add contributor and local setup documentation.
- [x] Add a test proving participant-owned fixture paths are not removed by cleanup/build tasks.

### Required tests

- [x] Clean-environment dependency installation succeeds.
- [x] All quality commands can run from the repository root.
- [x] Secret scanner detects a seeded fake secret fixture and ignores safe examples appropriately.
- [x] Cleanup removes only documented generated paths.

### Stage audit

- [x] Review dependency necessity and license compatibility.
- [x] Review scripts for destructive or overly broad filesystem behavior.
- [x] Review `.gitignore` and example configuration for secret leakage.
- [x] Verify CI matches documented local commands.
- [x] Create and resolve `docs/audits/stage-01-foundation-audit.md`.

### Stage completion

- [x] **Stage 1 complete and audited**

---

## Stage 2 — Content contracts and loading

**Goal:** Load and validate authored curriculum and participant state before presentation exists.

### Tasks

- [ ] Finalize versioned schemas without weakening supplied constraints.
- [ ] Implement safe YAML parsing.
- [ ] Implement Markdown front-matter parsing.
- [ ] Disable or sanitize raw HTML according to security policy.
- [ ] Implement typed normalized content models.
- [ ] Implement content discovery with stable deterministic ordering.
- [ ] Validate schema errors with filename and field path.
- [ ] Implement duplicate-ID and broken-reference checks.
- [ ] Implement prerequisite-cycle detection.
- [ ] Implement validator, badge, region, track, and related-quest reference checks.
- [ ] Implement progress and review integrity validation.
- [ ] Implement content hashes and supported-version checks.
- [ ] Add a `validate-content` command producing human and machine-readable output.

### Required tests

- [ ] Every supplied valid example passes.
- [ ] Every seeded invalid fixture fails for the intended reason.
- [ ] Duplicate IDs and circular prerequisites fail.
- [ ] Unknown references fail with suggestions when a close stable ID exists.
- [ ] Unsafe path and raw-HTML fixtures are rejected or sanitized as specified.
- [ ] Verified progress without valid approval fails integrity checks.

### Stage audit

- [ ] Trace every content field to a consumer or mark it intentionally reserved.
- [ ] Review parser behavior with malformed and adversarial input.
- [ ] Confirm templates will receive normalized models rather than raw dictionaries.
- [ ] Create and resolve `docs/audits/stage-02-content-audit.md`.

### Stage completion

- [ ] **Stage 2 complete and audited**

---

## Stage 3 — Deterministic site generation

**Goal:** Generate a complete, browseable, accessible static experience from valid content and fixture state.

### Tasks

- [ ] Implement route helpers based on stable IDs.
- [ ] Implement normalized page view models.
- [ ] Implement Jinja2 environment with autoescaping.
- [ ] Implement base layout and reusable components.
- [ ] Implement Home, Map, Region, Catalog, Quest Detail, Evidence, Passport, Environment, Validation Result, Reviewer, and Content Error pages.
- [ ] Generate tag, region, search, relationship, and build-manifest indexes.
- [ ] Implement static assets using design tokens.
- [ ] Implement no-JavaScript-readable core pages.
- [ ] Implement limited JavaScript enhancements for navigation, filtering, and disclosures.
- [ ] Implement atomic output replacement and last-known-good behavior.
- [ ] Ensure build output does not contain secrets or absolute developer paths.

### Required tests

- [ ] Clean build succeeds from fixture content and participant state.
- [ ] Routes and links contain no broken internal targets.
- [ ] Golden tests cover normalized view models and key components.
- [ ] Two builds from identical inputs are equivalent under the documented deterministic-output policy.
- [ ] A failed build leaves the prior valid output intact.
- [ ] Adding a fixture quest updates every required index without UI-code changes.

### Stage audit

- [ ] Compare every screen with `docs/ui/SCREEN-SPECS.md`.
- [ ] Compare reusable elements with `docs/ui/COMPONENT-CATALOG.md`.
- [ ] Search for quest-specific strings in templates and rendering code.
- [ ] Review escaping, Markdown sanitization, CSP, and external-link behavior.
- [ ] Create and resolve `docs/audits/stage-03-generation-audit.md`.

### Stage completion

- [ ] **Stage 3 complete and audited**

---

## Stage 4 — Participant state and loopback service

**Goal:** Safely persist participant actions and rebuild the site through a local-only service.

### Tasks

- [ ] Implement loopback-only service configuration.
- [ ] Implement per-run token and state-changing request protection.
- [ ] Implement typed APIs for health, start quest, update allowed participant fields, create evidence package, and rebuild.
- [ ] Implement state-transition rules.
- [ ] Implement atomic progress writes and recovery.
- [ ] Implement content-version awareness for attempts.
- [ ] Implement participant-visible mutation audit records.
- [ ] Implement service-unavailable UI behavior and CLI alternatives.
- [ ] Implement request size, path, and allowed-origin protections.
- [ ] Implement narrow Git status inspection without mutation.

### Required tests

- [ ] Service refuses non-loopback binding by default.
- [ ] Missing/invalid token and unexpected origin are rejected.
- [ ] Invalid transitions are rejected without state corruption.
- [ ] Traversal and symbolic-link escape attempts fail.
- [ ] Interrupted writes recover to a valid prior or new state.
- [ ] Application restart restores participant state.
- [ ] Service-unavailable pages remain useful and honest.

### Stage audit

- [ ] Review every route's read/write authority.
- [ ] Review canonical-path and symbolic-link handling.
- [ ] Review error responses for secret or path leakage.
- [ ] Create and resolve `docs/audits/stage-04-service-audit.md`.

### Stage completion

- [ ] **Stage 4 complete and audited**

---

## Stage 5 — Evidence workspaces and validator framework

**Goal:** Create reproducible evidence packages and execute only registered, constrained validators.

### Tasks

- [ ] Implement evidence-directory templates and manifest creation.
- [ ] Implement proof requirement detection.
- [ ] Implement validator registry with typed parameters.
- [ ] Implement process execution without shell command strings.
- [ ] Implement working-directory, environment, timeout, output, and path policies.
- [ ] Implement interruption and child-process cleanup.
- [ ] Implement structured validation results using the published schema.
- [ ] Implement result classification: pass, fail, warning, environment failure, and inconclusive.
- [ ] Implement output redaction and truncation.
- [ ] Implement secret scan before evidence-ready and submission transitions.
- [ ] Implement evidence staleness detection from artifact hashes.
- [ ] Implement at least three sample validators: file proof, Markdown proof quality, and a safe command-backed validator.

### Required tests

- [ ] Unknown validator IDs cannot execute.
- [ ] Metacharacters and attacker-controlled arguments remain ordinary arguments.
- [ ] Validators cannot write outside approved fixture roots.
- [ ] Timeouts terminate the full validator process tree.
- [ ] Large output is bounded and marked truncated.
- [ ] Secret-like output is redacted.
- [ ] A validator pass cannot create reviewer verification.

### Stage audit

- [ ] Threat-model the validator framework.
- [ ] Attempt path, command, environment, output, and timeout attacks.
- [ ] Review every sample validator for false-positive and false-negative behavior.
- [ ] Create and resolve `docs/audits/stage-05-validator-audit.md`.

### Stage completion

- [ ] **Stage 5 complete and audited**

---

## Stage 6 — Complete participant UI and interaction polish

**Goal:** Deliver the full participant workflow at production quality.

### Tasks

- [ ] Match the approved information hierarchy and design tokens.
- [ ] Complete responsive navigation.
- [ ] Implement deterministic recommended-next scoring and rationale.
- [ ] Implement map, region, and catalog filters with URL-preserved state where practical.
- [ ] Implement quest start/continue and version notices.
- [ ] Implement evidence actions and validation result detail.
- [ ] Implement Passport, badge states, capability breadth, and sanitized public-progress preview.
- [ ] Implement Environment Health checks and remediation guidance.
- [ ] Implement empty, error, locked, needs-changes, service-unavailable, and loading states.
- [ ] Implement polite/urgent live-region behavior.
- [ ] Respect reduced-motion preferences.
- [ ] Verify no essential workflow requires hover.

### Required tests

- [ ] Playwright covers the primary participant journey.
- [ ] Playwright covers locked, failed-validation, needs-changes, and service-unavailable states.
- [ ] Automated accessibility checks report no serious or critical findings.
- [ ] Keyboard-only navigation and actions work.
- [ ] Pages work at required desktop, tablet, narrow, and 200%-zoom conditions.
- [ ] No-JavaScript browsing preserves core content.

### Stage audit

- [ ] Complete `docs/ui/PROTOTYPE-REVIEW.md` against production UI.
- [ ] Compare text, states, authority labels, and actions to specification.
- [ ] Review responsive screenshots and keyboard flow.
- [ ] Create and resolve `docs/audits/stage-06-ui-audit.md`.

### Stage completion

- [ ] **Stage 6 complete and audited**

---

## Stage 7 — Submission and reviewer integrity

**Goal:** Support evidence review without allowing participant or automation to impersonate reviewer authority.

### Tasks

- [ ] Implement submission readiness checks.
- [ ] Implement submission record creation.
- [ ] Implement Reviewer View.
- [ ] Implement structured findings and decisions.
- [ ] Require explicit verification statement for approval.
- [ ] Require at least one finding for needs-changes or rejection.
- [ ] Implement changed-evidence detection.
- [ ] Implement review history.
- [ ] Implement verified XP and badge calculations from valid approval only.
- [ ] Document first-release reviewer provenance limitations.
- [ ] Implement Git/PR-oriented handoff instructions without automatic push or merge.

### Required tests

- [ ] Participant-created `verified` state is rejected.
- [ ] Approval for another attempt does not verify the current attempt.
- [ ] Changed evidence marks prior approval stale according to policy.
- [ ] Needs-changes returns the quest to an actionable participant state without deleting evidence.
- [ ] Verified XP and badges are calculated correctly.

### Stage audit

- [ ] Attempt to forge, reuse, and mismatch review records.
- [ ] Review language for false claims about cryptographic identity.
- [ ] Verify reviewer actions are distinct from participant actions.
- [ ] Create and resolve `docs/audits/stage-07-review-audit.md`.

### Stage completion

- [ ] **Stage 7 complete and audited**

---

## Stage 8 — Fork updates, versioning, and migrations

**Goal:** Allow participants to receive upstream improvements without losing their work.

### Tasks

- [ ] Document canonical upstream and participant-origin setup.
- [ ] Implement update preflight checks.
- [ ] Require or create a recoverable backup branch before automated update assistance.
- [ ] Display release and migration notes.
- [ ] Implement versioned participant-state migrations.
- [ ] Validate state before and after migration.
- [ ] Preserve in-progress attempts on older quest versions unless the participant opts into migration.
- [ ] Add tests proving `participant/` is never replaced wholesale.
- [ ] Document manual recovery when merge conflicts occur.

### Required tests

- [ ] Dirty working tree produces a safe stop with guidance.
- [ ] Backup branch exists before migration changes.
- [ ] Participant fixture files survive representative upstream updates.
- [ ] Failed migration restores or preserves pre-migration state.
- [ ] Historical verified attempts remain readable.

### Stage audit

- [ ] Review Git operations for destructive behavior.
- [ ] Simulate update conflicts in program and participant zones.
- [ ] Review every migration for reversibility and version guards.
- [ ] Create and resolve `docs/audits/stage-08-update-audit.md`.

### Stage completion

- [ ] **Stage 8 complete and audited**

---

## Stage 9 — Documentation, hardening, and release candidate

**Goal:** Make the application reproducible, supportable, and ready for a pilot cohort.

### Tasks

- [ ] Complete participant setup and operating guide.
- [ ] Complete curriculum-author guide.
- [ ] Complete validator-author guide.
- [ ] Complete reviewer guide.
- [ ] Complete update, backup, and recovery guide.
- [ ] Complete security and privacy guide reflecting actual behavior.
- [ ] Add troubleshooting for common setup, build, service, Git, and validation failures.
- [ ] Run performance checks with a representative large quest catalog.
- [ ] Run full security and accessibility test suites.
- [ ] Create release notes and known limitations.
- [ ] Create `docs/IMPLEMENTATION-DETAILS.md` based on actual code.
- [ ] Create `docs/TRACEABILITY.md` mapping requirements to code and tests.

### Required tests

- [ ] A clean-clone installation test succeeds using only documented steps.
- [ ] A new quest can be added without application-code changes.
- [ ] A second person can run a quest, assemble proof, validate it, and review it.
- [ ] Representative catalog build time and page size meet documented budgets.
- [ ] All prior stage tests pass together.

### Stage audit

- [ ] Audit documentation against actual commands and behavior.
- [ ] Audit implementation details against Git diff and architecture.
- [ ] Audit traceability for missing or unsupported claims.
- [ ] Create and resolve `docs/audits/stage-09-release-candidate-audit.md`.

### Stage completion

- [ ] **Stage 9 complete and audited**

---

## Stage 10 — Final independent audit and release decision

**Goal:** Decide whether the release candidate is ready for a pilot without relying on the implementation context that created it.

### Tasks

- [ ] Review the original product brief, acceptance criteria, architecture, and UI specification.
- [ ] Review implementation details and traceability.
- [ ] Inspect the complete change set.
- [ ] Run all automated checks from a clean environment.
- [ ] Perform primary participant and reviewer workflows manually.
- [ ] Review unresolved advisories and known limitations.
- [ ] Confirm no secrets, private evidence, or machine-specific paths are included.
- [ ] Create `docs/audits/final-audit.md`.
- [ ] Produce a release recommendation: `release`, `release-with-advisories`, or `do-not-release`.
- [ ] Fix blocking/high findings and rerun the final audit.

### Release gate

- [ ] No unresolved blocking or high findings.
- [ ] All release acceptance criteria are checked or explicitly deferred with approval.
- [ ] Implementation details describe what exists rather than what was planned.
- [ ] Clean-clone reproduction succeeds.
- [ ] Pilot limitations are visible to participants and reviewers.

### Stage completion

- [ ] **Stage 10 complete and final release decision recorded**

---

## Restart log

Update this section whenever work pauses.

| Date/time | Branch | Current stage | Last completed item | Next action | Blockers |
|---|---|---:|---|---|---|
| 2026-09-16 | feature/golden-thread-implementation | 0 | Stage 0 audit: pass-with-advisories | Begin Stage 1 foundation |  |
| 2026-09-16 | feature/golden-thread-implementation | 1 | Stage 1 audit: fail → fixed → pass-with-advisories | Complete Stage 2 content loading | `participant/` creation deferred to Stage 4 |
| 2026-09-16 | feature/golden-thread-implementation | 2 | Stage 2 built and committed (93e91cd); independent audit commissioned | Record the Stage 2 audit in `docs/audits/stage-02-content-audit.md`, fix blocking/high findings, then finish Stage 3 | Stage 2 audit result not yet recorded |
| 2026-09-16 | feature/golden-thread-implementation | 2 | Stage 2 audit recorded: **fail** (1 blocking, 6 high) in `docs/audits/stage-02-content-audit.md` | Fix B1, H1-H6 in that document, then rerun the Stage 2 audit before Stage 3 resumes | Stage 3 is partly built and must not advance until Stage 2 passes |
| 2026-09-16 | feature/golden-thread-implementation | 3 | Partial (blocked by the Stage 2 audit): design tokens, app.css, app.js, routes.py, progress_calc.py, recommend.py, view_models.py, base layout, 7 component macros, home/map/catalog/region pages (e845d3c) | Write quest-detail, evidence, validation-result, passport, health, review and content-error pages; then `quest_app/build.py` (atomic output, last-known-good, indexes, manifest); then Stage 3 tests and audit | Stage 3 has no `build.py` yet, so `make build` does not run |

## Deferred work register

| ID | Description | Reason deferred | Target | Owner | Approval |
|---|---|---|---|---|---|
| D1 | Glossary content type (`content/glossary/`) | No schema, no sample, no screen renders one | Post-release | Curriculum maintainer | Stage 0 audit F5 |
| D2 | Coverage reporting | `pytest-cov` was installed with nothing configured; half-configured is worse than absent | Stage 9 | Implementation | Stage 1 audit L1 |
| D3 | `attempts[].validation_result_ids` and `submission_id` consumers | Submission records are Stage 7 | Stage 7 | Implementation | Stage 2 audit M6 |
| D4 | `review.evidence_hash`, `review.quest_version` comparison, `hashing.hash_directory()` caller | Changed-evidence detection is Stage 7 | Stage 7 | Implementation | Stage 2 audit M6 |
| D5 | Validator-registry and submission schemas | Authored with the stages that use them | Stages 5 and 7 | Implementation | Stage 0 audit F7 |
| D6 | Presentation-only reserved fields (`quest.tools`, `author`, `last_reviewed`, `risk.notes`, `region.icon`, `badge.icon`, `track.focus_tags`, `site.professional_role`) | Consumed by pages that arrive in Stage 3 and Stage 6 | Stages 3 and 6 | Implementation | Stage 2 audit M6 |
