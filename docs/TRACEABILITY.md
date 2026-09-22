# Traceability

Every release acceptance criterion from `docs/ACCEPTANCE-CRITERIA.md`, mapped to the code
that implements it and the test that holds it. An unchecked row is unmet and says why.

A row with no test is not traceable. Where that is the case it is marked **no test**, which
is itself the finding.

## Content and generation

| ID and criterion | Implementation | Test |
|---|---|---|
| **CG1** All authored content validates against versioned schemas | `content_loader.SchemaSet` | `contract/test_content_loading.py::test_the_shipped_package_is_publishable` |
| **CG2** Cross-document validation detects duplicate IDs, broken references, cycles | `semantics.py` | `semantic/test_invalid_content.py::TestCrossReferences` |
| **CG3** A maintainer can add a quest without editing code | `build.py`, generic templates | `integration/test_build.py::TestAddingContentNeedsNoCodeChange::test_no_ui_file_was_touched` |
| **CG4** A valid new quest appears in region, catalog, filters, search, prerequisite graph | `build.py` indexes | `TestAddingContentNeedsNoCodeChange` (five assertions) |
| **CG5** Invalid content prevents publication with an actionable error | `errors.ContentProblem` | `semantic/test_invalid_content.py` (20 rules) |
| Generated output is deterministic | sorted traversal, sorted JSON | `integration/test_build.py::test_two_builds_of_the_same_inputs_are_identical` |
| **CG7** A failed build preserves the last valid output | `build._swap` | `test_a_build_that_fails_midway_leaves_the_previous_site_intact` |

## Participant experience

| ID and criterion | Implementation | Test |
|---|---|---|
| **PE1** Overall progress and a reasoned next-quest recommendation | `recommend.py`, `pages/home.html.j2` | `unit/test_recommendation.py` (eight tests: eligibility, three reasons, determinism, tie-breaking) |
| **PE2** Browse all regions and filter the catalog | region, tag and catalog pages | `ui/test_browser_flows.py::TestCatalogFiltering` |
| **PE3** A quest page communicates mission, outcomes, prerequisites, criteria, safety, proof, validators, XP, estimate | `pages/quest_detail.html.j2` | `test_a_quest_page_communicates_every_required_element` (asserts all nine) |
| **PE4** Starting a quest persists state outside browser storage | `store.start_attempt` | `integration/test_state_transitions.py::TestWritingProgress` |
| **PE5** Restarting restores the same state | `pipeline.load_world` | `test_a_transition_is_recorded_and_survives_a_reload` |
| **PE6** The evidence workspace creates and displays a standard proof package | `store._create_evidence_package`, `evidence.py` | `integration/test_evidence.py` |
| **PE7** Validation results distinguish pass, fail, warning, environment failure, inconclusive | `validator_runner.classify` | `security/test_validator_sandbox.py::TestClassification` |
| **PE8** Claimed and verified progress are visibly distinct | `progress_calc.totals`, C02 | `test_claimed_and_verified_are_never_presented_as_one_total` |

## Reviewer experience

| ID and criterion | Implementation | Test |
|---|---|---|
| **RE1** A reviewer sees the exact quest version and attempt | per-quest reviewer page, `_review_context` | `test_a_reviewer_page_exists_for_every_attempt`, `TestSubmission` |
| **RE2** A reviewer can inspect required proof and linked artifacts | `evidence.detect_proof` | `integration/test_evidence.py::TestProofDetection` |
| **RE3** A reviewer can see validator results and reproduction instructions | `_review_context` results table and PROOF.md render | `test_a_reviewer_page_exists_for_every_attempt`; `submission_instructions` covered by `TestSubmission` |
| **RE4** Approve, request changes, or reject with findings | `review.record_decision` | `TestApprovalGuards` (five guards) |
| **RE5** Only approval changes the attempt to verified | `review._apply_decision` | `TestWhatApprovalProduces`, `TestForgery` |
| **RE6** Evidence changes after approval are detected and surfaced | `progress._check_stale_approval` | `TestEvidenceChangedAfterApproval` (four tests, including a tampered review hash) |

## Filesystem and Git safety

| ID and criterion | Implementation | Test |
|---|---|---|
| **FS1** Program updates do not overwrite participant files | `update.py` runs no merge | `integration/test_update_and_migration.py::test_participant_files_survive_an_upstream_style_update` |
| **FS2** Local actions cannot write outside approved roots | `config.resolve_participant_path`, `Workspace` | `security/test_validator_sandbox.py::TestWorkspaceContainment` |
| **FS3** Symbolic-link and traversal tests pass | resolve-then-check, everywhere | `test_cleanup_safety.py`, `test_service.py`, `test_validator_sandbox.py` |
| **FS4** Generated and runtime data are gitignored | `.gitignore` | `unit/test_gitignore.py`, including `git check-ignore` against the real rules |
| **FS5** Secrets excluded from logs and submission preparation | `evidence.scan_evidence` gate | `test_review_integrity.py::test_a_submission_carrying_a_secret_is_refused` |
| **FS6** Git status shown before submission | `git_status.summary_for` | `integration/test_update_and_migration.py::TestGitSafety` |

## Validator safety

| ID and criterion | Implementation | Test |
|---|---|---|
| **VS1** Only registered validators can run | `ValidatorRegistry.get` | `TestOnlyRegisteredValidatorsRun` |
| **VS2** Validator arguments are typed and allowlisted | `Parameter.coerce` | `TestParameters` (five cases) |
| **VS3** No caller-provided shell command is executed | no argument string exists | `test_an_entrypoint_outside_the_validators_package_is_refused` |
| **VS4** Timeout, output limits, interruption handled | `run_validator`, `_terminate_tree` | `test_a_timeout_produces_interrupted_not_a_verdict` |
| **VS5** A validator cannot mark work reviewer-verified | `state_machine.TRANSITIONS` | `test_a_passing_validator_cannot_produce_verified` |
| **VS6** Results use the published result schema | `RunResult.to_document` | `test_a_real_run_produces_a_schema_valid_document` |

## UI and accessibility

| ID and criterion | Implementation | Test |
|---|---|---|
| **UI1** All required screens implemented | thirteen page templates | `integration/test_build.py::test_a_clean_build_produces_every_page` |
| **UI2** Primary navigation works with keyboard only | semantic links | `ui/test_browser_flows.py::TestKeyboardAndFocus` |
| **UI3** Visible focus and skip navigation | `:focus-visible`, skip link | `test_focus_is_always_visible`, `test_the_skip_link_moves_focus_to_the_main_landmark` |
| **UI4** Status is not expressed by color alone | label plus `::before` glyph | `test_status_is_never_communicated_by_colour_alone` |
| **UI5** Key contrast meets WCAG 2.2 AA | design tokens, light and inverse pairs | `ui/test_contrast.py` (20 pairings) and axe `color-contrast` |
| **UI6** Usable at 200% zoom and 390-pixel width | responsive CSS | `ui/test_browser_flows.py::TestResponsive` (four viewports plus 200%) |
| **UI7** Motion honours reduced-motion | `prefers-reduced-motion` block | `test_reduced_motion_is_respected` |
| **UI8** Automated accessibility checks pass with no serious findings | vendored axe-core | `test_no_serious_accessibility_violation` (11 pages) |

## Documentation and handoff

| ID and criterion | Implementation | Test |
|---|---|---|
| **DH1** Setup works from a clean clone | `docs/SETUP.md`, `make setup`, `make verify-package` | `clean-export` job in `.github/workflows/ci.yml`, plus a by-hand clone-and-install recorded in round 4 |
| **DH2** Content-authoring instructions with a full example | `docs/CONTENT-AUTHORING-GUIDE.md` | — |
| **DH3** Validator-authoring instructions describe the safety boundary | `docs/VALIDATOR-CONTRACT.md`, `docs/guides/VALIDATOR-AUTHORING.md` | — |
| **DH4** Update and migration behavior documented | `docs/guides/UPDATING.md` | `integration/test_update_and_migration.py` |
| **DH5** `IMPLEMENTATION-DETAILS.md` describes what exists | this repository | — |
| **DH6** `TRACEABILITY.md` connects criteria to code and tests | this file | — |
| **DH7** Final audit reports no unresolved blocking or high findings | `docs/audits/` | pending Stage 10 |

## Rows corrected after the final audit

The final audit opened fourteen rows and found five that were false or materially weaker
than the criterion they claimed. All five are corrected above, and in four cases the fix was
to write the test that did not exist: `git_status` had none at all, `.gitignore` was only
ever copied and never read, `recommend.py` was entirely untested, and the quest-page row
rested on one string assertion. That is recorded here rather than quietly amended, because a
traceability document is only worth having if it is audited like anything else.

## Open rows

None. The one row that was open here — **setup works from a clean clone** — closed in round
4. The `clean-export` CI job asserts the install on every change from an exported tree, and
round 4 additionally ran `git clone` from the remote followed by `make setup`,
`make validate-content` and `make build` on a machine holding no build artefacts. That run
also found the formatting gate failing at `207a7b3`, which is the kind of thing only a clean
clone finds; it is recorded in `docs/audits/round-04-independent-audit.md`.

The three accessibility rows that were open at the first writing are now closed: contrast is
computed from the tokens and checked again by axe in a browser, the responsive and zoom
conditions are exercised at all four named viewports, and axe runs over eleven pages with
serious and critical impacts failing the build.


## Capability added after the criteria were written

These rows carry no criterion ID because no criterion asked for them. They are listed so the
document stays a complete map of what is tested, rather than only of what was specified.

| Capability | Implementation | Test |
|---|---|---|
| Every state transition is available without a browser, through one allowlist shared with the service | `actions.py`, `cli.py` | `integration/test_cli_actions.py::test_the_cli_and_the_service_share_one_allowlist`, `::test_listing_actions_names_every_transition` |
| The CLI cannot reach `verified`, exactly as the HTTP surface cannot | `actions.py`, `state_machine.TRANSITIONS` | `::test_no_cli_action_can_produce_verified` |
| A reviewer can approve, request changes or reject without a browser, on the same vocabulary and the same guards | `cli.py`, `review.record_decision` | `::test_a_reviewer_can_approve_without_a_browser`, `::test_approval_without_a_statement_is_refused`, `::test_a_malformed_finding_is_refused_rather_than_dropped`, `::test_approving_changed_evidence_needs_the_acknowledgement` |
| A quest that declares no validators still reaches `submitted`, and one that declares them is still refused without a qualifying run | `actions.py` `_require_qualifying_validation` | `::test_a_quest_declaring_no_validators_can_still_reach_submitted`, `::test_a_quest_declaring_a_validator_is_refused_without_a_qualifying_run` |
| The commands the guides tell a participant to type are installed and run | `pyproject.toml` entry points | `::test_the_commands_the_guides_name_are_actually_installed`, `::test_the_installed_command_runs` |
| Python 3.10, the declared floor, runs the suite | `quest_app/compat.py` | the `3.10` leg of the `check` matrix in `.github/workflows/ci.yml` |

## Criterion coverage

Every row above carries the stable ID of the criterion it maps to, from
`docs/ACCEPTANCE-CRITERIA.md`. Before the IDs existed a row could only match a criterion by
prose, which is how this document came to name the wrong test file for a criterion twice in
a row without anyone noticing.

**Criteria with no row here: CG6.** Each one is either covered by a row whose wording differs, or genuinely unmapped; treat an ID appearing in neither place as unverified.
