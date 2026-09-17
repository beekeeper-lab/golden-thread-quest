# Traceability

Every release acceptance criterion from `docs/ACCEPTANCE-CRITERIA.md`, mapped to the code
that implements it and the test that holds it. An unchecked row is unmet and says why.

A row with no test is not traceable. Where that is the case it is marked **no test**, which
is itself the finding.

## Content and generation

| Criterion | Implementation | Test |
|---|---|---|
| All authored content validates against versioned schemas | `content_loader.SchemaSet` | `contract/test_content_loading.py::test_the_shipped_package_is_publishable` |
| Cross-document validation detects duplicate IDs, broken references, cycles | `semantics.py` | `semantic/test_invalid_content.py::TestCrossReferences` |
| A maintainer can add a quest without editing code | `build.py`, generic templates | `integration/test_build.py::TestAddingContentNeedsNoCodeChange::test_no_ui_file_was_touched` |
| A valid new quest appears in region, catalog, filters, search, prerequisite graph | `build.py` indexes | `TestAddingContentNeedsNoCodeChange` (five assertions) |
| Invalid content prevents publication with an actionable error | `errors.ContentProblem` | `semantic/test_invalid_content.py` (20 rules) |
| Generated output is deterministic | sorted traversal, sorted JSON | `integration/test_build.py::test_two_builds_of_the_same_inputs_are_identical` |
| A failed build preserves the last valid output | `build._swap` | `test_a_build_that_fails_midway_leaves_the_previous_site_intact` |

## Participant experience

| Criterion | Implementation | Test |
|---|---|---|
| Overall progress and a reasoned next-quest recommendation | `recommend.py`, `pages/home.html.j2` | `unit/test_recommendation.py` (nine tests: eligibility, three reasons, determinism, tie-breaking) |
| Browse all regions and filter the catalog | region, tag and catalog pages | `ui/test_browser_flows.py::TestCatalogFiltering` |
| A quest page communicates mission, outcomes, prerequisites, criteria, safety, proof, validators, XP, estimate | `pages/quest_detail.html.j2` | `test_a_quest_page_communicates_every_required_element` (asserts all nine) |
| Starting a quest persists state outside browser storage | `store.start_attempt` | `integration/test_state_transitions.py::TestWritingProgress` |
| Restarting restores the same state | `pipeline.load_world` | `test_a_transition_is_recorded_and_survives_a_reload` |
| The evidence workspace creates and displays a standard proof package | `store._create_evidence_package`, `evidence.py` | `integration/test_evidence.py` |
| Validation results distinguish pass, fail, warning, environment failure, inconclusive | `validator_runner.classify` | `security/test_validator_sandbox.py::TestClassification` |
| Claimed and verified progress are visibly distinct | `progress_calc.totals`, C02 | `test_claimed_and_verified_are_never_presented_as_one_total` |

## Reviewer experience

| Criterion | Implementation | Test |
|---|---|---|
| A reviewer sees the exact quest version and attempt | per-quest reviewer page, `_review_context` | `test_a_reviewer_page_exists_for_every_attempt`, `TestSubmission` |
| A reviewer can inspect required proof and linked artifacts | `evidence.detect_proof` | `integration/test_evidence.py::TestProofDetection` |
| A reviewer can see validator results and reproduction instructions | `_review_context` results table and PROOF.md render | `test_a_reviewer_page_exists_for_every_attempt`; `submission_instructions` covered by `TestSubmission` |
| Approve, request changes, or reject with findings | `review.record_decision` | `TestApprovalGuards` (five guards) |
| Only approval changes the attempt to verified | `review._apply_decision` | `TestWhatApprovalProduces`, `TestForgery` |
| Evidence changes after approval are detected and surfaced | `progress._check_stale_approval` | `TestEvidenceChangedAfterApproval` (four tests, including a tampered review hash) |

## Filesystem and Git safety

| Criterion | Implementation | Test |
|---|---|---|
| Program updates do not overwrite participant files | `update.py` runs no merge | `integration/test_update_and_migration.py::test_participant_files_survive_an_upstream_style_update` |
| Local actions cannot write outside approved roots | `config.resolve_participant_path`, `Workspace` | `security/test_validator_sandbox.py::TestWorkspaceContainment` |
| Symbolic-link and traversal tests pass | resolve-then-check, everywhere | `test_cleanup_safety.py`, `test_service.py`, `test_validator_sandbox.py` |
| Generated and runtime data are gitignored | `.gitignore` | `unit/test_gitignore.py`, including `git check-ignore` against the real rules |
| Secrets excluded from logs and submission preparation | `evidence.scan_evidence` gate | `test_review_integrity.py::test_a_submission_carrying_a_secret_is_refused` |
| Git status shown before submission | `git_status.summary_for` | `integration/test_update_and_migration.py::TestGitSafety` |

## Validator safety

| Criterion | Implementation | Test |
|---|---|---|
| Only registered validators can run | `ValidatorRegistry.get` | `TestOnlyRegisteredValidatorsRun` |
| Validator arguments are typed and allowlisted | `Parameter.coerce` | `TestParameters` (five cases) |
| No caller-provided shell command is executed | no argument string exists | `test_an_entrypoint_outside_the_validators_package_is_refused` |
| Timeout, output limits, interruption handled | `run_validator`, `_terminate_tree` | `test_a_timeout_produces_interrupted_not_a_verdict` |
| A validator cannot mark work reviewer-verified | `state_machine.TRANSITIONS` | `test_a_passing_validator_cannot_produce_verified` |
| Results use the published result schema | `RunResult.to_document` | `test_a_real_run_produces_a_schema_valid_document` |

## UI and accessibility

| Criterion | Implementation | Test |
|---|---|---|
| All required screens implemented | twelve page templates | `integration/test_build.py::test_a_clean_build_produces_every_page` |
| Primary navigation works with keyboard only | semantic links | `ui/test_browser_flows.py::TestKeyboardAndFocus` |
| Visible focus and skip navigation | `:focus-visible`, skip link | `test_focus_is_always_visible`, `test_the_skip_link_moves_focus_to_the_main_landmark` |
| Status is not expressed by colour alone | label plus `::before` glyph | `test_status_is_never_communicated_by_colour_alone` |
| Key contrast meets WCAG 2.2 AA | design tokens, light and inverse pairs | `ui/test_contrast.py` (20 pairings) and axe `color-contrast` |
| Usable at 200% zoom and 390-pixel width | responsive CSS | `ui/test_browser_flows.py::TestResponsive` (four viewports plus 200%) |
| Motion honours reduced-motion | `prefers-reduced-motion` block | `test_reduced_motion_is_respected` |
| Automated accessibility checks pass with no serious findings | vendored axe-core | `test_no_serious_accessibility_violation` (11 pages) |

## Documentation and handoff

| Criterion | Implementation | Test |
|---|---|---|
| Setup works from a clean clone | `docs/SETUP.md`, `make setup` | **no test** — open, Stage 9 |
| Content-authoring instructions with a full example | `docs/CONTENT-AUTHORING-GUIDE.md` | — |
| Validator-authoring instructions describe the safety boundary | `docs/VALIDATOR-CONTRACT.md`, `docs/guides/VALIDATOR-AUTHORING.md` | — |
| Update and migration behaviour documented | `docs/guides/UPDATING.md` | `integration/test_update_and_migration.py` |
| `IMPLEMENTATION-DETAILS.md` describes what exists | this repository | — |
| `TRACEABILITY.md` connects criteria to code and tests | this file | — |
| Final audit reports no unresolved blocking or high findings | `docs/audits/` | pending Stage 10 |

## Rows corrected after the final audit

The final audit opened fourteen rows and found five that were false or materially weaker
than the criterion they claimed. All five are corrected above, and in four cases the fix was
to write the test that did not exist: `git_status` had none at all, `.gitignore` was only
ever copied and never read, `recommend.py` was entirely untested, and the quest-page row
rested on one string assertion. That is recorded here rather than quietly amended, because a
traceability document is only worth having if it is audited like anything else.

## Open rows

One criterion has no test and is therefore not traceable: **setup works from a clean clone**.
It needs a fresh checkout and a network install, which the test suite deliberately does not
do. It is listed rather than quietly ticked, because a traceability document whose rows are
aspirations is worse than none.

The three accessibility rows that were open at the first writing are now closed: contrast is
computed from the tokens and checked again by axe in a browser, the responsive and zoom
conditions are exercised at all four named viewports, and axe runs over eleven pages with
serious and critical impacts failing the build.
