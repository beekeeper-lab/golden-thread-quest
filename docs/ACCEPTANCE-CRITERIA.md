# Release Acceptance Criteria

Every criterion carries a stable ID. `docs/TRACEABILITY.md` maps each ID to the code that
implements it and the test that holds it; before the IDs existed, a row could only match a
criterion by prose, which is how the traceability document came to overstate its coverage
without anyone noticing.

A ticked box means a test asserts it. An unticked box is unmet and says so in the
traceability document.

## Content and generation

- [x] **CG1** — All authored content validates against versioned schemas.
- [x] **CG2** — Cross-document validation detects duplicate IDs, broken references, and prerequisite cycles.
- [x] **CG3** — A maintainer can add a quest without editing Python, Jinja2, JavaScript, or CSS.
- [x] **CG4** — A valid new quest automatically appears in its region, catalog, filters, search, and prerequisite graph.
- [x] **CG5** — Invalid content prevents publication and produces an actionable error.
- [x] **CG6** — Generated output is deterministic for equivalent inputs, excluding documented build metadata.
- [x] **CG7** — A failed build preserves the last known valid output.

## Participant experience

- [x] **PE1** — A participant can see overall progress and a reasoned next-quest recommendation.
- [x] **PE2** — A participant can browse all regions and filter the catalog.
- [x] **PE3** — A quest page communicates mission, outcomes, prerequisites, acceptance criteria, safety, proof, validators, XP, and estimate.
- [x] **PE4** — Starting a quest persists state outside browser storage.
- [x] **PE5** — Restarting the application restores the same state.
- [x] **PE6** — The evidence workspace can create and display a standard proof package.
- [x] **PE7** — Validation results distinguish pass, fail, warning, environment failure, and inconclusive.
- [x] **PE8** — Claimed and verified progress are visibly distinct.

## Reviewer experience

- [x] **RE1** — A reviewer can see the exact quest version and attempt being reviewed.
- [x] **RE2** — A reviewer can inspect required proof and linked artifacts.
- [x] **RE3** — A reviewer can see validator results and reproduction instructions.
- [x] **RE4** — A reviewer can approve, request changes, or reject with findings.
- [x] **RE5** — Only approval changes the attempt to verified.
- [x] **RE6** — Evidence changes after approval can be detected and surfaced.

## Filesystem and Git safety

- [x] **FS1** — Program updates do not overwrite participant-owned files.
- [x] **FS2** — Local actions cannot write outside approved roots.
- [x] **FS3** — Symbolic-link and traversal tests pass.
- [x] **FS4** — Generated and local runtime data are Gitignored.
- [x] **FS5** — Secrets are excluded from logs and submission preparation.
- [x] **FS6** — Git status is shown before actions that prepare submissions.

## Validator safety

- [x] **VS1** — Only registered validators can run.
- [x] **VS2** — Validator arguments are typed and allowlisted.
- [x] **VS3** — No caller-provided shell command is executed.
- [x] **VS4** — Timeout, output limits, and interrupted execution are handled.
- [x] **VS5** — A validator cannot mark work reviewer-verified.
- [x] **VS6** — Validation results use the published result schema.

## UI and accessibility

- [x] **UI1** — All required screens and component states are implemented.
- [x] **UI2** — Primary navigation works with keyboard only.
- [x] **UI3** — Visible focus and skip navigation are provided.
- [x] **UI4** — Status is not expressed by color alone.
- [x] **UI5** — Key text and graphical elements meet WCAG 2.2 AA contrast.
- [x] **UI6** — Pages remain usable at 200% zoom and 390-pixel viewport width.
- [x] **UI7** — Motion honors reduced-motion preference.
- [x] **UI8** — Automated accessibility checks pass with no serious or critical findings.

## Documentation and handoff

- [x] **DH1** — Setup instructions work from a clean clone. *(Closed by `make verify-package`: exports tracked files only via `git archive`, then installs, validates content and builds in a fresh venv. Runs as the `clean-export` job in CI, so it is asserted on every change rather than confirmed once by hand.)*
- [x] **DH2** — Content-authoring instructions include a full quest example.
- [x] **DH3** — Validator-authoring instructions describe the safety boundary.
- [x] **DH4** — Update and migration behavior is documented.
- [x] **DH5** — `docs/IMPLEMENTATION-DETAILS.md` describes actual implementation, not planned behavior.
- [x] **DH6** — `docs/TRACEABILITY.md` connects these criteria to code and tests.
- [ ] **DH7** — Final audit reports no unresolved blocking or high findings. *(Open. Ten rounds have now run and each found something. Round 10 is recorded in `docs/audits/round-10-independent-audit.md`: thirty-three findings returned, thirty-two accepted after verification and one not reproduced — one blocking, eight high, every accepted one fixed or stated as a limitation, and every code fix carrying a test that fails without it. The blocking finding: approving an attempt started before a quest version bump wrote the content's version into the review, and the integrity check then refused to load the participant's state. The criterion closes on a round that finds nothing, so it needs round 11 against the merge commit.)*
