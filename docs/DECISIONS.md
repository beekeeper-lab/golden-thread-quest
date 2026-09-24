# Architecture and Product Decisions

This is the initial architecture decision log. Claude must append decisions rather than silently replacing earlier ones.

## ADR-001 — Independent quest repository

**Decision:** The Golden Thread Quest is its own repository. The broader AI Context Engineer Journey may later have a small registry repository when more than one quest exists.

**Reason:** Participants should be able to fork, clone, run, and update this quest independently. A monolithic journey repository would couple release timing and participant histories across unrelated future quests.

## ADR-002 — Participant forks as the default distribution model

**Decision:** The canonical repository is forked by participants.

**Reason:** Forks preserve upstream history and allow curriculum updates. A template repository creates unrelated history and is better only for deliberately frozen cohorts.

## ADR-003 — Three ownership zones

**Decision:** Program-owned, participant-owned, and generated files remain in separate top-level areas.

**Reason:** Upstream updates must not overwrite participant work. Generated output must be disposable. Ownership boundaries simplify validation and security.

## ADR-004 — Markdown and YAML for authored content

**Decision:** Narrative quest content uses Markdown with YAML front matter. Primarily structured content uses YAML.

**Reason:** Maintainers need readable diffs, approachable authoring, and structured fields. A database or raw JSON would make common edits less pleasant and less reviewable.

## ADR-005 — JSON Schema as the public contract

**Decision:** JSON Schema defines the required shape of content and participant state.

**Reason:** Schemas are language-neutral, testable, editor-friendly, and appropriate for validating YAML or JSON representations.

## ADR-006 — Deterministic Python/Jinja generation

**Decision:** Python loads, normalizes, validates, and renders content through Jinja2 templates.

**Reason:** The product is primarily content-driven. Server-rendered HTML is inspectable, portable, fast, and avoids an unnecessary frontend compilation pipeline.

## ADR-007 — No frontend framework in release one

**Decision:** Use semantic HTML, modern CSS, and limited vanilla JavaScript.

**Reason:** React or an equivalent would duplicate application state, complicate the Python-generated model, and increase maintenance without clear first-release value.

## ADR-008 — Hybrid static generation and local service

**Decision:** HTML is generated deterministically. A loopback-only service performs narrowly defined local actions and triggers rebuilds.

**Reason:** Pure static HTML cannot safely create files, run validators, or inspect Git. A full dynamic web application is unnecessary.

## ADR-009 — Mermaid is documentation, not primary UI

**Decision:** Mermaid documents architecture, workflows, and state transitions. HTML/CSS defines the actual UI.

**Reason:** Mermaid communicates relationships well but cannot adequately specify responsive layout, spacing, accessibility, interaction states, or visual hierarchy.

## ADR-010 — Professional field-guide visual direction

**Decision:** Use a restrained field-guide aesthetic: strong typography, maps/regions as metaphors, quiet texture, and professional status displays.

**Reason:** Gamification should aid motivation without making the program look childish or reducing trust in enterprise settings.

## ADR-011 — Verified progress requires a reviewer decision

**Decision:** Participants and validators cannot mark work verified or award verified XP.

**Reason:** Automated checks can establish objective facts but cannot prove the total quality or meaning of agentic work. The UI must not blur these authorities.

## ADR-012 — Stable IDs and versioned content

**Decision:** Relationships use stable IDs. Evidence records the quest version or content hash used when work was performed.

**Reason:** Titles and filenames change. Version-aware attempts allow curriculum improvements without invalidating earlier verified work.

## ADR-013 — Repository evidence is primary

**Decision:** Source, tests, instructions, logs, and structured results are preferred to screenshots.

**Reason:** Repository evidence is reviewable, reproducible, diffable, and harder to misinterpret. Screenshots remain useful for inherently visual results.

## ADR-014 — Allowlisted actions only

**Decision:** The local service may execute only registered validators or named actions with validated arguments and approved working directories.

**Reason:** A localhost process with arbitrary command execution would be an avoidable security boundary failure.

## ADR-015 — Generated output is not canonical

**Decision:** Generated HTML, indexes, caches, and transient raw responses are disposable and normally Gitignored.

**Reason:** Canonical truth remains in content, schemas, participant files, evidence, and review records. Generated output must be reproducible.

---

## Stage 0 decisions (2026-09-16)

Recorded by the implementation agent during the Stage 0 planning and feasibility audit.
Evidence and reasoning: `docs/audits/stage-00-planning-audit.md`.

## ADR-016 — Acceptance criteria are derived from the quest body with positional IDs

**Decision:** Acceptance criteria are parsed from the ordered list under the quest body's
`## Acceptance criteria` heading. Each criterion gets the positional ID `ac-<n>` (1-based) and a
`text_hash` of its normalized text. Reviewer findings and evidence status reference the positional ID.
A build error is raised when the heading is missing or contains no list.

**Amended by ADR-026:** a bullet list produces the same positional IDs and a warning asking
the author to number them, not a build error. An empty item is still an error, and so is a
list split in two by an intervening paragraph.

**Reason:** `COMPONENT-CATALOG.md` C10, `VIEW-MODEL-CONTRACT.md`, and the quest-detail page
(`templates/pages/quest_detail.html.j2`, which renders each criterion at its own
`criterion-ac-<n>` anchor) all require stable criterion IDs, while `CONTENT-MODEL.md` forbids duplicating
the criteria into front matter. Deriving them keeps one copy. The `text_hash` makes a silent change of
meaning under a stable ID detectable, which is what the quest `version` rule already asks an author to
declare.

## ADR-017 — A validation run never changes attempt state

**Decision:** Running a validator appends a result record and changes nothing else. `locally_validated`
is reached only when the participant requests it and every required validator's latest run returns a
qualifying outcome. A failing run leaves the attempt where it was and surfaces findings. The
`EvidenceReady --> InProgress: Validation fails` edge in the `ARCHITECTURE.md` diagram is not
implemented.

**Reason:** An automatic backward transition would make a registered validator an authority over
participant state, which ADR-011 denies it, and would discard the `evidence_ready` assertion the
participant deliberately made. `SCREEN-SPECS.md` U06 requires that a validator failure never become
"quest failed".

**Amended (round 11):** the guard protected the transition, not the file. A `locally_validated`
state written into `progress.yaml` by hand loaded and was shown under the validator's authority.
The loader now refuses it (`progress.unvalidated_locally_validated_state`, an error, as a forged
`verified` is) when a quest declares validators and any of them has no qualifying result for the
attempt. It asks for *a* qualifying result per validator, not that the latest one qualifies,
because a failing re-run after local validation leaves the attempt where it was under this ADR
and must not take the site down. No other state is checked, because submission is allowed
straight from `evidence_ready`.

**Amended (round 12):** the round 11 check compared the attempt against the *current* quest's
validators, which punished a legitimate attempt exactly like a forged one: an upstream update
that added a validator moved a `locally_validated` attempt from "consistent" to "a required
validator has no result", with no way to tell that apart from a hand-edited state, because
nothing here keeps a record of what a quest required at an earlier version. Every action was
then refused for that attempt, including the one, `run-validator`, that would clear the finding.
The check now reads `attempt.quest_version` first. On the same version, nothing changes: any
validator missing a qualifying result is still `progress.unvalidated_locally_validated_state`,
an error. On a different version, a validator missing a qualifying result is only an error if
the attempt has *no* qualifying result at all — indistinguishable from the forgery this check
exists to catch — and otherwise becomes `progress.locally_validated_missing_new_validator`, a
warning naming the validator and saying to run it, because the application has no way to know
whether that validator existed when the attempt validated.

## ADR-018 — Participant paths are contract-fixed, the participant root is configuration

**Decision:** `evidence_path` and `result_path` keep the literal `participant/` prefix the schemas
require. The base directory they resolve against is injected (`participant_root`), defaulting to
`<repo>/participant` and pointed at `<repo>/fixtures/participant` under test. Every resolved path is
canonicalized and re-verified inside the configured root after symbolic links are followed.

**Reason:** Tests must exercise the real loader against the shipped fixtures without writing into a
participant's live directory, and the schema prefix is part of the published contract, so it is
configuration that moves, not the contract.

**Amended (round 12):** `participant_root` moved, but `generated_root` and `local_data_root` did
not — the CLI's `--participant-root` rebuilt the config without carrying them forward, and
`from_environment` never read a variable for either. A test that ran the CLI as a real subprocess,
the only way an installed-Cowork participant can act at all, rebuilt the repository's own
`generated/` on every mutating action, for example overwriting a checked-in `generated/index.html`
with fixture data until the next `make build`. `generated_root` and `local_data_root` are now
configuration the same way: `GTQ_GENERATED_ROOT` and `GTQ_LOCAL_DATA_ROOT` are read by
`AppConfig.from_environment`, and `_config_from_args` carries both forward when
`--participant-root` is also given. Every test that shells out to the CLI sets all three.

## ADR-019 — Python 3.10 or newer

**Decision:** `requires-python = ">=3.12"`. Development and CI run 3.12 and the newest stable release.

**Reason:** `PLANNING-STATUS.md` requires 3.12 or newer. No 3.13-or-later-only syntax is used, so the
floor stays where the plan put it.

**Amended 2026-09-21 (round 4):** the floor is `>=3.10`, not `>=3.12`. The Cowork sandbox a
participant may be handed ships 3.10, and an application that will not install there is not
local-first in any sense that matters. Nothing in the codebase needed 3.12: the compatibility
shims live in `quest_app/compat.py` and are covered by tests. Development and CI still run the
newest stable release, and CI additionally runs the 3.10 floor so the claim is asserted rather
than assumed. The planning requirement is superseded here rather than quietly ignored.

## ADR-020 — `jsonschema` against the published schemas, frozen dataclasses internally

**Decision:** Authored and participant documents are validated with `jsonschema` (Draft 2020-12)
against the files in `schemas/`. Validated documents are then converted into frozen dataclasses for
internal use. Pydantic is not used.

**Reason:** The published schemas are the public contract. A Pydantic model layer would restate the
same rules in a second place that can drift from the file a maintainer actually reads.

## ADR-021 — `markdown-it-py` for CommonMark, `nh3` for sanitization

**Decision:** Quest narrative is rendered by `markdown-it-py` with raw HTML disabled, then passed
through `nh3` with an explicit tag and attribute allowlist and a URL-scheme allowlist. Rendered HTML
is carried in a distinct view-model field name (`safe_rendered_html`) so it cannot be confused with
ordinary text.

**Reason:** `PLANNING-STATUS.md` requires CommonMark plus sanitization.
`SECURITY-AND-PRIVACY.md` requires an explicit allowlist and disabled raw HTML. Sanitizing after
rendering means the guarantee does not depend on the renderer's own escaping being complete.

## ADR-022 — The loopback service uses the Python standard library

**Decision:** The local service is built on `http.server.ThreadingHTTPServer` with an explicit route
table. FastAPI, Starlette, and Flask are not used.

**Reason:** Every service requirement in `ARCHITECTURE.md` and `SECURITY-AND-PRIVACY.md` is a
*restriction* — loopback binding, per-run token, origin checks, body-size caps, allowlisted route IDs,
no filesystem paths from callers. A framework adds dependencies and abstracts the exact request
surface those restrictions apply to. The service handles a single local user and needs no concurrency
model beyond threads.

## ADR-023 — `pytest`, Playwright, and axe-core

**Decision:** `pytest` for unit, contract, semantic, golden, integration, and security layers.
Playwright for participant and reviewer flows. axe-core through Playwright for automated accessibility
checks.

**Reason:** Named in `IMPLEMENTATION-PLAN.md`.

## ADR-024 — `ruff` for format and lint, `mypy --strict` for types

**Decision:** `ruff format` and `ruff check` are the formatter and linter. `mypy --strict` type-checks
`quest_app/` and `validators/`.

**Reason:** One tool covering format and lint keeps the local commands and CI identical. Strict typing
is affordable on a codebase this size and prevents the view-model contract from decaying into
untyped dictionaries.

## ADR-025 — YAML is parsed with `safe_load` only

**Decision:** Every YAML read uses `yaml.safe_load`. `yaml.load` and custom constructors are forbidden
and a lint rule enforces it.

**Reason:** `IMPLEMENTATION-PLAN.md` Stage 2 requires safe YAML parsing. Authored content, participant
state, and review records are all inputs that can arrive from a pull request.

---

## Stage 2 audit decisions (2026-09-16)

Recorded after the independent Stage 2 audit returned `fail`.
Findings and evidence: `docs/audits/stage-02-content-audit.md`.

## ADR-026 — An unnumbered acceptance-criteria list is a warning, not an error

**Decision:** ADR-016 is amended. A bullet list under `## Acceptance criteria` produces
positional IDs exactly as a numbered list does, and a warning asking the author to number
them. It is not a build error. An **empty** item *is* an error, and so is a list split in
two by an intervening paragraph.

**Reason:** ADR-016 as first written said "a build error is raised when the heading is
missing or contains no ordered list". The audit found that all three shipped quests use
bullet lists, so the package the decision log describes does not build — the code and the
decision disagreed, and neither had been chosen deliberately.

Numbering is the right thing to ask for, because participants and reviewers refer to
criteria by number. But it is a presentation nicety: the identifier is `ac-<n>` derived from
position either way, so an unnumbered list is not *less* stable, only less readable. The
failures that actually break ADR-016's promise are the ones now escalated to errors:

* an **empty item** shifts the identifier of every criterion after it, so a reviewer finding
  pinned to `ac-3` silently moves to a different criterion;
* a **split list** means the author wrote five criteria and the build used two, with no
  message.

Refusing to build over a bullet would block authors on a formatting preference while those
two real defects passed. This inverts that.

## ADR-027 — Markdown structure is read from the token stream, never from lines

**Decision:** Section splitting and acceptance-criteria extraction parse the Markdown token
stream (`quest_app/markdown_structure.py`). Line-oriented regexes are not used for either.

**Reason:** The first implementation matched headings and list items with regexes, and the
audit broke it four ways: a nested sub-detail became a top-level criterion, a fenced code
block containing numbers became criteria, an empty item renumbered everything after it, and
a criterion continued onto a second line lost that line from the model, the page *and* its
own hash — so editing it did not change the hash that staleness detection depends on.

All four are one mistake: treating Markdown as lines rather than as a document. The parser
already knows that `##` inside a fence is text and that an indented list is nested. Asking
it is also the only way the loader and the renderer can agree, and ADR-016's promise is
precisely that `ac-3` means the same criterion on the page and in a reviewer's finding.

## ADR-028 — A content-hash mismatch is surfaced, never fatal

**Decision:** `attempts[].content_hash` is compared to the quest's current content hash on
every load. A mismatch is a **warning**, with different wording for a verified attempt
("the approval may be stale") and for work in progress ("the text has changed since you
started"). It is never a build error.

**Reason, part one — why compare at all.** The hash was required, stored, and compared to
nothing: 64 zeros validated. It is the only thing that distinguishes "the quest text
changed" from "the version number changed", and without it a reviewer's approval of one set
of acceptance criteria silently applies to a different set.

**Reason, part two — why a warning.** The first version of this decision made a mismatch an
error for a verified attempt, and implementing it immediately broke a test for the right
reason: editing a verified quest's text made the build fail. That contradicts
`CONTENT-MODEL.md`, which says "previously verified attempts remain verified unless a
documented program policy explicitly revokes them" — and the hash deliberately covers the
whole front matter and body, so a typo fix in a Hints section would have invalidated
someone's approved work.

The participant and the reviewer need to be told. The build does not need to stop. Stage 7's
changed-evidence detection is where a possibly-stale approval becomes visible in the
interface, and this warning is what feeds it.

The integrity **error** stays where it belongs: a `verified` state with no valid approval
behind it at all (ADR-011).

## ADR-029 — Duplicate YAML keys and unbounded nesting are refused

**Decision:** All YAML is read through `StrictSafeLoader` (`quest_app/yaml_loader.py`), which
is `SafeLoader` plus a duplicate-key error, and `RecursionError` from deep nesting becomes an
ordinary reported problem. `tools/check_yaml_safe.py` names this one file as the audited
exception to the `yaml.load` ban.

**Reason:** `xp: 10` followed by `xp: 90` parsed as 90 while a reviewer reading the diff saw
10. Content that means one thing in review and another at build time defeats the entire
point of validating authored content in a pull request. Separately, around nine hundred
levels of nesting raised `RecursionError`, which is not a `YAMLError`, so it escaped the
loader's handling and ended the run with a traceback containing absolute paths.

---

## Stage 7 decisions (2026-09-16)

## ADR-030 — Reviewer provenance is conventional in release one, and said so plainly

**Decision:** A reviewer is identified by the display name in the review record and by Git
history. Review records are not cryptographically signed. The application refuses every
*internally inconsistent* claim — a review that does not match the attempt, an approval with
no verification statement, an approval of evidence that changed since submission, a
`verified` state with no approval behind it — and the remaining gap is documented in the
reviewer guide and visible in the interface rather than papered over.

**Reason:** Signing needs key distribution, key custody and a revocation story, none of
which exist for a pilot cohort, and a half-implemented signature is worse than none because
it invites trust it has not earned. The threat this release actually defends against is
mistake and drift, not a determined forger with write access to their own repository. Saying
which one is which is the honest position, and `SECURITY-AND-PRIVACY.md` already requires
that the limitation be visible.

## ADR-031 — The evidence hash covers the participant's work, not the records about it

**Decision:** `evidence_hash` excludes `validation/`, `submission.yaml` and every
`review*.yaml`.

**Reason:** Found by a test that should have passed and did not. Writing the submission
record into the evidence directory changed the very hash the record had just captured, so a
freshly submitted attempt read as "changed since submission" the moment it was submitted.
The same applies to a validation re-run and to the review record itself. The question the
hash answers is "has the participant's work changed?", so the application's own bookkeeping
has no business in it.

**Amended (round 11):** the participant's work is not only the package. Every quest declares
proof outside it — a test under `participant/tests/`, a document under `participant/context/`
— and editing one after submission or after approval raised nothing. Submission and review
records now also carry `proof_files`: each declared proof path (required and optional, of a
path-bearing type) that does not lie under the quest's own evidence area, with a digest of
what it held. Authored `attempt-001` paths under the evidence area are left out because
`_inside_the_package` maps them into the package, which `evidence_hash` already covers. A
path is resolved with `resolve_participant_path`, so one that leads outside `participant/`
is recorded as `unresolvable` and never read; one with nothing at it is `missing`, so a file
appearing or disappearing is a change. The approval gate compares the submission's
`proof_files`, the reviewer page names each changed path, and the loader warns
(`progress.proof_changed_since_approval`) when an approved review's `proof_files` no longer
match. The review records the paths the submission recorded, so both describe the same set.

Old records lack the field. They are compared on `evidence_hash` alone, exactly as before,
and never read as changed or forged for its absence. A review of an old submission computes
its paths from the quest as it stands, so its approval can still go stale later. The paths
come from the quest as loaded, not from the attempt's recorded version: the application
keeps no earlier version of a quest's text, so when an update has moved a quest on, the
submission records the current version's declared paths.

**Amended (round 11, links):** a symbolic link inside the package that resolves outside it
is refused the same way by render, hash and scan: `PROOF.md` is not rendered through it, the
hash takes its link text rather than its target, the secret scan reports it (which blocks
submission), and the loader warns (`evidence.link_outside_package`). A link that resolves
inside the package is hashed by the content it shows, because that is what the build
renders. A package holding such a link hashes differently from before this change; a
package with no links hashes the same.

## ADR-032 — The application never pushes, opens a pull request, or merges

**Decision:** Submission prints the exact Git commands and stops. `git_status.py` runs only
an allowlisted set of read-only commands and raises if asked for anything else.

**Reason:** Pushing evidence or opening a pull request is a claim, on the participant's
behalf, that work is finished and ready for someone else's attention. That claim is theirs
to make. It is also the difference between a tool that enhances a repository and one that
takes it over, which `PRODUCT-BRIEF.md` draws explicitly.

## ADR-033 — A rule the browser enforces is enforced in the action layer, not the template

**Decision:** Every rule that decides whether a participant may do something lives in
`quest_app/actions.py`, the layer both the loopback service and the CLI call. A template may
grey out a control, but never as the only thing standing in the way.

**Reason:** Round 4 found prerequisites computed for display and enforced nowhere. The quest
page disabled Start on a locked quest, and one CLI command started it — a participant with
nothing verified could take a quest three links down the chain and carry it to `verified`.
The defect was invisible while the browser was the only caller, because the view was the
enforcement. A second caller made it a hole. The same reasoning covers the secret-scan gate,
the validator guard and the review guards, which were already there.

**Amended 2026-09-22 (round 7):** the C21 confirmation was the remaining rule the browser
enforced alone — a `required` checkbox, which is the browser's rule and not the service's, so
a form post without it performed the action. The actions that carry a confirmation and the
words they confirm now live in `state_machine.CONFIRMATIONS`; the page renders them from
there and the service refuses a form submission without one, so the page and the service
cannot disagree about which actions need confirming.

## ADR-034 — One mutation at a time, across processes

**Decision:** `ProgressStore.exclusive()` takes an exclusive POSIX file lock on
`participant/.progress.lock`, and `ActionRunner.perform` holds it around the whole action,
loading included. The lock is advisory and POSIX-only: where `fcntl` is unavailable the
action still runs.

**Reason:** Every mutation is a read, a decision and a write, and the service's lock is held
inside one process. Once the CLI could perform the same sequence, two processes could
interleave it: four concurrent starts produced four activity lines and three attempts. The
lock spans the load because reading state another process is about to replace is the race,
not just writing it. It is not held over a validator run, which is slow and appends rather
than replaces.

**Rejected:** refusing to act when the lock cannot be taken. A local-first application that
will not record a participant's own work because of a lock file is worse than the race it
prevents, and `atomic_write_text` still guarantees the file is never half-written.

## ADR-035 — One build at a time per output directory

**Decision:** `build_site` holds an exclusive POSIX file lock on `generated.lock` for the
whole build. The lock is advisory and POSIX-only, and a build that cannot lock proceeds.

**Reason:** Every build stages into `generated.building` and publishes by rename. That name
is fixed, so two builds in one repository share the directory and the second one's first act
is to delete it. Round 5 reproduced it three times out of three: the crash was the good case,
because twice both processes exited zero and published 3 and 20 of the site's 53 pages with
nothing saying the site was incomplete. ADR-034 serialises action against action; nothing
covered build against build, and `quest-app build`, `make build` and the service's rebuild
are all builds.

**Rejected:** a staging directory per process. It removes the collision during rendering and
leaves the publish itself racing over `generated.previous`, which is the step that decides
what a participant sees.

**Amended in round 6.** This ADR and ADR-036 both claimed the build lock fell through the way
the progress lock does. It did not: `_exclusive_output` handled a missing `fcntl` module and
nothing else, so an unwritable `generated.lock` or a filesystem answering `ENOLCK` crashed
every publisher, on exactly the filesystem the fall-through was written for. Two of round 6's
three lenses found it independently. The code now matches what was written here, and a test
covers each case.

## ADR-036 — Not being able to lock is never a reason to refuse the work

**Decision:** Where a lock cannot be taken, the work proceeds unlocked. That covers a missing
`fcntl` module, a lock file that cannot be opened, and `flock` itself failing, which is what
`ENOLCK` from a filesystem with no lock manager means. A wait for a held lock is announced
before it blocks.

**Reason:** ADR-034 stated this intent and delivered it only for a missing module. Both other
cases raised out of the lock, ahead of every guard, and the CLI had no handler for `OSError`
at all: a `.progress.lock` the participant could not open ended a `quest-app action` in a
traceback carrying absolute paths, and a home directory on NFS would have stopped every
mutation on both surfaces. The application worked without a lock before ADR-034 and the
atomic replace in `atomic_write_text` is what keeps the file readable either way, so the
degraded path is the application's own previous behaviour rather than a new risk.

**Rejected:** failing loudly so the participant knows the lock is gone. The participant
cannot act on it, and the failure lands on the surface least able to explain it.

**Amended in round 6.** Round 5 also deleted the lock file and the participant directory
around it when an action was refused before writing anything, so that a refusal left no
trace. It left something worse: a second process holding `flock` on that inode was left
holding a lock on an orphan, the next process created a fresh file and entered at once, and
two writers sat in the critical section together. The cleanup is gone. A refused first action
leaves one hidden, ignored file in a directory the participant owns, which is the cheaper of
the two, and `.gitignore` now ignores that file wherever the participant root is.

## ADR-037 — The service records the port it actually bound

**Decision:** `run_service` writes its bound port to `local-data/service-port` and removes it
on shutdown. `is_service_running` probes that port, falling back to the configured one, and
still requires this application's own response header before believing anything.

**Reason:** An action rebuilds the site, and the pages it writes say whether state can change
from them, so it must know whether a service is running. It asked at the configured port,
which is 8765 unless `GTQ_SERVICE_PORT` says otherwise, while `serve --port` is an advertised
flag and `action` has no matching one. Beside a service on any other port, one CLI action
published the offline view and disabled every control on every served page, which is the
defect ADR-033's round set out to fix.

**Rejected:** adding `--port` to `action` and `build`. It fixes the command a participant
remembers to type correctly and leaves the one they do not, and the port is a fact the
service already knows.

**Amended in round 6.** One file was one too few. `serve --port` exists so a repository can
host more than one service, and a single `service-port` file meant the second overwrote the
first's claim while either one's shutdown deleted it for both: stopping one left the other
serving pages with every control dead, which is the defect this file was added to prevent.
There is now one file per bound port under `local-data/service-ports/`, written by the
service that bound it and removed by that service alone; the probe asks at each in turn and
still requires this application's own header before believing any of them. The read is
bounded and range-checked, because an entry symlinked at `/dev/zero` otherwise hangs the
reader forever.

## ADR-038 — A rebuild that fails does not deny a change that already happened

**Decision:** An action performs its state change, then rebuilds. A failure of that rebuild
is reported as an advisory on a successful action, not as a failed action.

**Reason:** The change is on disk before the rebuild starts. Reporting an `OSError` from the
build as a failure told the participant their work had not been recorded, pointed them at
their participant directory when the problem was the output directory, and exited non-zero
while `progress.yaml` said the change had happened. Generated output is disposable and
rebuildable by a single command; the participant's record is neither, and the two must not
share a failure mode.

**Rejected:** rolling the state change back so the report is true. It throws away the one
thing in the transaction that cannot be regenerated.

**Amended 2026-09-22 (round 7):** this was implemented on the transition path only.
Submission, review and validation rebuilt without the guard, so the same failure told a
participant their submission had failed while `submission.yaml` sat on disk, and their retry
was refused because the attempt was already submitted. Every path that rebuilds after a
record is written now goes through one `ActionRunner._rebuild`, and the form route carries
the advisory into the page instead of discarding it.

## ADR-039 — A validator judges the attempt it was given

**Decision:** The validator workspace carries the evidence package of the attempt under
validation, and a check about that attempt's evidence reads `workspace.attempt_files`.
`iter_files` over `participant/evidence` is for questions about the whole tree, not for
questions about one attempt.

**Reason:** Nothing in the contract named the quest or the attempt, so checks reached for
`participant/evidence` and took whichever file was newest. A blank `PROOF.md` under an
unrelated quest failed a complete attempt and was reported as that attempt's failing
artifact, and a log from any other quest satisfied "failure is diagnosable" here. Records are
connected by their identifiers, never by modification time.

**Rejected:** passing the quest and attempt IDs and letting each validator build the path.
The path is the application's to construct; a validator that builds its own would be one
rename away from reading nothing at all.

## ADR-040 — The build timestamp is the only thing a rebuild may change

**Decision:** The build honours `SOURCE_DATE_EPOCH`. Set it and two builds of the same
content are byte-identical; leave it and every page carries the time it was built.

**Reason:** "Two builds of the same inputs are byte-identical" was written in the release
notes without qualification and was false for the command a reader runs: the footer carries
the clock. The test behind the criterion pinned the timestamp itself, so nothing ever ran the
claim the way a reader would. Honouring the reproducible-builds convention makes the claim
true on demand, and the documents now say what is true without it.

**Rejected:** removing the timestamp from the page. A reader of a generated page needs to
know how old it is more often than they need it to hash the same.

## ADR-041 — The service answers only to a loopback name, and every request gets a response

**Decision:** A request whose `Host` is not a loopback name is refused before anything is
rendered; a `GET` carrying a declared body is refused; and both handlers end in a catch-all
that answers with the exception's type and nothing else.

**Reason:** Every page carries the run's request token, and the service served pages to any
request that reached the port, whatever name it claimed — so a page at a name that resolves
to 127.0.0.1 is same-origin to the browser and can read the token out of a page. An
undeclared body on a kept-alive connection is parsed as a second request with every header
chosen by the sender, which is the hole round 6 closed on refusals and left open on `GET`.
And three exception types were caught by name while anything else escaped the handler: no
status, no body, a traceback carrying absolute paths, and the participant's change already
on disk.

**Rejected:** binding to a name rather than an address. The address is right; what was
missing was checking the name the request arrived under.
