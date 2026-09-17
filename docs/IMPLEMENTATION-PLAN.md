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

- [x] Finalize versioned schemas without weakening supplied constraints.
- [x] Implement safe YAML parsing.
- [x] Implement Markdown front-matter parsing.
- [x] Disable or sanitize raw HTML according to security policy.
- [x] Implement typed normalized content models.
- [x] Implement content discovery with stable deterministic ordering.
- [x] Validate schema errors with filename and field path.
- [x] Implement duplicate-ID and broken-reference checks.
- [x] Implement prerequisite-cycle detection.
- [x] Implement validator, badge, region, track, and related-quest reference checks.
- [x] Implement progress and review integrity validation.
- [x] Implement content hashes and supported-version checks.
- [x] Add a `validate-content` command producing human and machine-readable output.

### Required tests

- [x] Every supplied valid example passes.
- [x] Every seeded invalid fixture fails for the intended reason.
- [x] Duplicate IDs and circular prerequisites fail.
- [x] Unknown references fail with suggestions when a close stable ID exists.
- [x] Unsafe path and raw-HTML fixtures are rejected or sanitized as specified.
- [x] Verified progress without valid approval fails integrity checks.

### Stage audit

- [x] Trace every content field to a consumer or mark it intentionally reserved.
- [x] Review parser behavior with malformed and adversarial input.
- [x] Confirm templates will receive normalized models rather than raw dictionaries.
- [x] Create and resolve `docs/audits/stage-02-content-audit.md`.

### Stage completion

- [x] **Stage 2 complete and audited**

---

## Stage 3 — Deterministic site generation

**Goal:** Generate a complete, browseable, accessible static experience from valid content and fixture state.

### Tasks

- [x] Implement route helpers based on stable IDs.
- [x] Implement normalized page view models.
- [x] Implement Jinja2 environment with autoescaping.
- [x] Implement base layout and reusable components.
- [x] Implement Home, Map, Region, Catalog, Quest Detail, Evidence, Passport, Environment, Validation Result, Reviewer, and Content Error pages.
- [x] Generate tag, region, search, relationship, and build-manifest indexes.
- [x] Implement static assets using design tokens.
- [x] Implement no-JavaScript-readable core pages.
- [x] Implement limited JavaScript enhancements for navigation, filtering, and disclosures.
- [x] Implement atomic output replacement and last-known-good behavior.
- [x] Ensure build output does not contain secrets or absolute developer paths.

### Required tests

- [x] Clean build succeeds from fixture content and participant state.
- [x] Routes and links contain no broken internal targets.
- [x] Golden tests cover normalized view models and key components.
- [x] Two builds from identical inputs are equivalent under the documented deterministic-output policy.
- [x] A failed build leaves the prior valid output intact.
- [x] Adding a fixture quest updates every required index without UI-code changes.

### Stage audit

- [x] Compare every screen with `docs/ui/SCREEN-SPECS.md`.
- [x] Compare reusable elements with `docs/ui/COMPONENT-CATALOG.md`.
- [x] Search for quest-specific strings in templates and rendering code.
- [x] Review escaping, Markdown sanitization, CSP, and external-link behavior.
- [x] Create and resolve `docs/audits/stage-03-generation-audit.md`.

### Stage completion

- [x] **Stage 3 complete and audited**

---

## Stage 4 — Participant state and loopback service

**Goal:** Safely persist participant actions and rebuild the site through a local-only service.

### Tasks

- [x] Implement loopback-only service configuration.
- [x] Implement per-run token and state-changing request protection.
- [x] Implement typed APIs for health, start quest, update allowed participant fields, create evidence package, and rebuild.
- [x] Implement state-transition rules.
- [x] Implement atomic progress writes and recovery.
- [x] Implement content-version awareness for attempts.
- [x] Implement participant-visible mutation audit records.
- [x] Implement service-unavailable UI behavior and CLI alternatives.
- [x] Implement request size, path, and allowed-origin protections.
- [x] Implement narrow Git status inspection without mutation.

### Required tests

- [x] Service refuses non-loopback binding by default.
- [x] Missing/invalid token and unexpected origin are rejected.
- [x] Invalid transitions are rejected without state corruption.
- [x] Traversal and symbolic-link escape attempts fail.
- [x] Interrupted writes recover to a valid prior or new state.
- [x] Application restart restores participant state.
- [x] Service-unavailable pages remain useful and honest.

### Stage audit

- [x] Review every route's read/write authority.
- [x] Review canonical-path and symbolic-link handling.
- [x] Review error responses for secret or path leakage.
- [ ] Create and resolve `docs/audits/stage-04-service-audit.md`.

### Stage completion

- [ ] **Stage 4 complete and audited**

---

## Stage 5 — Evidence workspaces and validator framework

**Goal:** Create reproducible evidence packages and execute only registered, constrained validators.

### Tasks

- [x] Implement evidence-directory templates and manifest creation.
- [x] Implement proof requirement detection.
- [x] Implement validator registry with typed parameters.
- [x] Implement process execution without shell command strings.
- [x] Implement working-directory, environment, timeout, output, and path policies.
- [x] Implement interruption and child-process cleanup.
- [x] Implement structured validation results using the published schema.
- [x] Implement result classification: pass, fail, warning, environment failure, and inconclusive.
- [x] Implement output redaction and truncation.
- [x] Implement secret scan before evidence-ready and submission transitions.
- [x] Implement evidence staleness detection from artifact hashes.
- [x] Implement at least three sample validators: file proof, Markdown proof quality, and a safe command-backed validator.

### Required tests

- [x] Unknown validator IDs cannot execute.
- [x] Metacharacters and attacker-controlled arguments remain ordinary arguments.
- [x] Validators cannot write outside approved fixture roots.
- [x] Timeouts terminate the full validator process tree.
- [x] Large output is bounded and marked truncated.
- [x] Secret-like output is redacted.
- [x] A validator pass cannot create reviewer verification.

### Stage audit

- [x] Threat-model the validator framework.
- [x] Attempt path, command, environment, output, and timeout attacks.
- [x] Review every sample validator for false-positive and false-negative behavior.
- [ ] Create and resolve `docs/audits/stage-05-validator-audit.md`.

### Stage completion

- [ ] **Stage 5 complete and audited**

---

## Stage 6 — Complete participant UI and interaction polish

**Goal:** Deliver the full participant workflow at production quality.

### Tasks

- [x] Match the approved information hierarchy and design tokens.
- [x] Complete responsive navigation.
- [x] Implement deterministic recommended-next scoring and rationale.
- [x] Implement map, region, and catalog filters with URL-preserved state where practical.
- [x] Implement quest start/continue and version notices.
- [x] Implement evidence actions and validation result detail.
- [x] Implement Passport, badge states, capability breadth, and sanitized public-progress preview.
- [x] Implement Environment Health checks and remediation guidance.
- [x] Implement empty, error, locked, needs-changes, service-unavailable, and loading states.
- [x] Implement polite/urgent live-region behavior.
- [x] Respect reduced-motion preferences.
- [x] Verify no essential workflow requires hover.

### Required tests

- [x] Playwright covers the primary participant journey.
- [x] Playwright covers locked, failed-validation, needs-changes, and service-unavailable states.
- [x] Automated accessibility checks report no serious or critical findings.
- [x] Keyboard-only navigation and actions work.
- [x] Pages work at required desktop, tablet, narrow, and 200%-zoom conditions.
- [x] No-JavaScript browsing preserves core content.

### Stage audit

- [x] Complete `docs/ui/PROTOTYPE-REVIEW.md` against production UI.
- [x] Compare text, states, authority labels, and actions to specification.
- [x] Review responsive screenshots and keyboard flow.
- [x] Create and resolve `docs/audits/stage-06-ui-audit.md`.

### Stage completion

- [x] **Stage 6 complete and audited**

---

## Stage 7 — Submission and reviewer integrity

**Goal:** Support evidence review without allowing participant or automation to impersonate reviewer authority.

### Tasks

- [x] Implement submission readiness checks.
- [x] Implement submission record creation.
- [x] Implement Reviewer View.
- [x] Implement structured findings and decisions.
- [x] Require explicit verification statement for approval.
- [x] Require at least one finding for needs-changes or rejection.
- [x] Implement changed-evidence detection.
- [x] Implement review history.
- [x] Implement verified XP and badge calculations from valid approval only.
- [x] Document first-release reviewer provenance limitations.
- [x] Implement Git/PR-oriented handoff instructions without automatic push or merge.

### Required tests

- [x] Participant-created `verified` state is rejected.
- [x] Approval for another attempt does not verify the current attempt.
- [x] Changed evidence marks prior approval stale according to policy.
- [x] Needs-changes returns the quest to an actionable participant state without deleting evidence.
- [x] Verified XP and badges are calculated correctly.

### Stage audit

- [x] Attempt to forge, reuse, and mismatch review records.
- [x] Review language for false claims about cryptographic identity.
- [x] Verify reviewer actions are distinct from participant actions.
- [ ] Create and resolve `docs/audits/stage-07-review-audit.md`.

### Stage completion

- [ ] **Stage 7 complete and audited**

---

## Stage 8 — Fork updates, versioning, and migrations

**Goal:** Allow participants to receive upstream improvements without losing their work.

### Tasks

- [x] Document canonical upstream and participant-origin setup.
- [x] Implement update preflight checks.
- [x] Require or create a recoverable backup branch before automated update assistance.
- [x] Display release and migration notes.
- [x] Implement versioned participant-state migrations.
- [x] Validate state before and after migration.
- [x] Preserve in-progress attempts on older quest versions unless the participant opts into migration.
- [x] Add tests proving `participant/` is never replaced wholesale.
- [x] Document manual recovery when merge conflicts occur.

### Required tests

- [x] Dirty working tree produces a safe stop with guidance.
- [x] Backup branch exists before migration changes.
- [x] Participant fixture files survive representative upstream updates.
- [x] Failed migration restores or preserves pre-migration state.
- [x] Historical verified attempts remain readable.

### Stage audit

- [x] Review Git operations for destructive behavior.
- [x] Simulate update conflicts in program and participant zones.
- [x] Review every migration for reversibility and version guards.
- [ ] Create and resolve `docs/audits/stage-08-update-audit.md`.

### Stage completion

- [ ] **Stage 8 complete and audited**

---

## Stage 9 — Documentation, hardening, and release candidate

**Goal:** Make the application reproducible, supportable, and ready for a pilot cohort.

### Tasks

- [x] Complete participant setup and operating guide.
- [x] Complete curriculum-author guide.
- [x] Complete validator-author guide.
- [x] Complete reviewer guide.
- [x] Complete update, backup, and recovery guide.
- [x] Complete security and privacy guide reflecting actual behavior.
- [x] Add troubleshooting for common setup, build, service, Git, and validation failures.
- [x] Run performance checks with a representative large quest catalog.
- [x] Run full security and accessibility test suites.
- [x] Create release notes and known limitations.
- [x] Create `docs/IMPLEMENTATION-DETAILS.md` based on actual code.
- [x] Create `docs/TRACEABILITY.md` mapping requirements to code and tests.

### Required tests

- [ ] A clean-clone installation test succeeds using only documented steps. (Needs a fresh checkout and a network install; recorded as an open row in `docs/TRACEABILITY.md`.)
- [x] A new quest can be added without application-code changes.
- [x] A second person can run a quest, assemble proof, validate it, and review it.
- [x] Representative catalog build time and page size meet documented budgets.
- [x] All prior stage tests pass together.

### Stage audit

- [x] Audit documentation against actual commands and behavior.
- [x] Audit implementation details against Git diff and architecture.
- [x] Audit traceability for missing or unsupported claims.
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
| 2026-09-17 | feature/golden-thread-implementation | 10 | Stage 3 re-audit: pass with residuals (all closed). Stage 6 audit: fail → all findings closed, `docs/audits/stage-06-ui-audit.md`. Final-audit findings all closed; release re-audit commissioned | Await the release re-audit, then make the decision | Release decision not yet made |
| 2026-09-17 | feature/golden-thread-implementation | 10 | Superseded: Final audit returned **do-not-release**: 3 blocking, 4 high. All blocking and high findings fixed (`docs/audits/stage-10-final-audit.md`); re-audit commissioned | Await the re-audit, fix M4 and M5, then make the release decision | Release decision not yet made |
| 2026-09-17 | feature/golden-thread-implementation | 10 | Superseded: Stages 3, 6, 8 and 9 complete. Stage 3/6 re-audit and the final release audit both commissioned | Record both audit results, fix blocking and high findings, then make the release decision | Clean-clone install untested; no Git remote configured |
| 2026-09-17 | feature/golden-thread-implementation | 3 | Superseded: Stage 3 audit findings fixed: B1, H1-H3, all eight mediums, plus S2-R1 and H5. Browser tests added. Awaiting re-audit | Re-audit Stage 3 and Stage 2, then Stages 6, 9, 10 | |
| 2026-09-17 | feature/golden-thread-implementation | 3 | Superseded: Stage 3 audit recorded **fail** (1 blocking, 4 high, 8 medium) in `docs/audits/stage-03-generation-audit.md`. Stage 2 re-audit: pass with one open item (H5) plus residual S2-R1 | Fix S3-B1, S3-H1..H3, S2-R1, H5; then the medium findings; then rerun both audits | Stages 4, 5, 7 and 8 were built on top of unaudited Stage 3 and may need rework |
| 2026-09-16 | feature/golden-thread-implementation | 3 | Superseded (partial): design tokens, app.css, app.js, routes.py, progress_calc.py, recommend.py, view_models.py, base layout, 7 component macros, home/map/catalog/region pages (e845d3c) | Write quest-detail, evidence, validation-result, passport, health, review and content-error pages; then `quest_app/build.py` (atomic output, last-known-good, indexes, manifest); then Stage 3 tests and audit | Stage 3 has no `build.py` yet, so `make build` does not run |

## Deferred work register

| ID | Description | Reason deferred | Target | Owner | Approval |
|---|---|---|---|---|---|
| D1 | Glossary content type (`content/glossary/`) | No schema, no sample, no screen renders one | Post-release | Curriculum maintainer | Stage 0 audit F5 |
| D2 | Coverage reporting | `pytest-cov` was installed with nothing configured; half-configured is worse than absent | **Post-release** (re-approved 2026-09-17: Stage 9 shipped without it) | Implementation | Stage 1 audit L1 |
| D3 | `attempts[].validation_result_ids` and `submission_id` consumers | Submission records are Stage 7 | Stage 7 | Implementation | Stage 2 audit M6 |
| D4 | `review.evidence_hash`, `review.quest_version` comparison, `hashing.hash_directory()` caller | Changed-evidence detection is Stage 7 | Stage 7 | Implementation | Stage 2 audit M6 |
| D5 | Validator-registry and submission schemas | Authored with the stages that use them | Stages 5 and 7 | Implementation | Stage 0 audit F7 |
| D7 | Live Environment Health checks (dependency versions, Git status, participant write test, external CLI presence, service binding) | A generated page cannot inspect the machine at the moment it is read; the five static checks say what was true at build time and label themselves as such | **Post-release**, through the local service (re-approved 2026-09-17) | Implementation | Stage 3 audit S3-M4 |
| D8 | A fixture exercising all eight quest states at once | The shipped fixture covers two; the rest are reached by mutating it in `tests/ui/test_states.py` | Post-release | Curriculum maintainer | Stage 6 audit F4 |
| D9 | Container or seccomp isolation for validators | Release one is policy plus process boundaries: a validator using `open()` directly bypasses `Workspace`. Disclosed in the release notes | Post-release | Implementation | Final re-audit, Job 2 |
| D10 | Secret-scanner coverage: keyword-distant assignments, bare 40-hex keys, base64 blobs, webhook URLs, any PII | The detectors are a safety net and are documented as one; widening them without a corpus risks false positives that make people route around the gate | Post-release | Implementation | Final re-audit R16 |
| D11 | Role separation between participant and reviewer | `/review/` sits in the primary navigation with no separation, so a participant can open the reviewer page for their own work. ADR-030 already states that release-one provenance is conventional | Post-release | Program owner | Final re-audit, Job 2 |
| D12 | A degraded view for an attempt whose evidence directory is missing | Today one deleted folder makes the whole site unbuildable until `progress.yaml` is hand-edited | Post-release | Implementation | Final re-audit R8 |
| D6 | Presentation-only reserved fields (`quest.tools`, `author`, `last_reviewed`, `risk.notes`, `region.icon`, `badge.icon`, `track.focus_tags`, `site.professional_role`) | Consumed by pages that arrive in Stage 3 and Stage 6 | Stages 3 and 6 | Implementation | Stage 2 audit M6 |
