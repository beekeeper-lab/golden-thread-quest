# Part 8. Glossary

Terms are defined where they first appear; this list collects them. Code names are given
where the term maps to one.

| Term | Meaning |
|---|---|
| **Acceptance criterion** | One item of the ordered list under a quest's `## Acceptance criteria` heading. Identified by position as `ac-<n>` with a hash of its text (ADR-016, ADR-026) |
| **Action** | One of the ten named operations that change state: `start-quest`, `mark-evidence-ready`, `mark-locally-validated`, `reopen-evidence`, `submit-for-review`, `withdraw-submission`, `resume-quest`, `run-validator`, `record-review`, `rebuild` (`actions.MUTATING_ACTIONS`) |
| **Action layer** | `quest_app/actions.py`, specifically `ActionRunner`: the one place every action's rules are enforced, called by both the service and the CLI (ADR-033) |
| **Activity log** | `participant/ACTIVITY.md`, one line per change the application made to participant files |
| **ADR** | Architecture decision record, numbered in `docs/DECISIONS.md` |
| **Advisory** | A problem reported alongside a successful action rather than blocking it, for example an unrun validator at submission, or a rebuild that failed after a change was recorded |
| **AI Context Engineer** | The role the curriculum trains: owner of the intent and validation bookends of software delivery |
| **Atomic write** | Writing a temporary file in the same directory, flushing it to disk, and renaming it over the target, so the target is either wholly old or wholly new (`store.atomic_write_text`) |
| **Attempt** | One participant's run at one quest, recorded in `progress.yaml` with an attempt ID, quest version, content hash, state and evidence path |
| **Attempt state** | One of the six stored states: `in_progress`, `evidence_ready`, `locally_validated`, `submitted`, `needs_changes`, `verified` (`models.AttemptState`) |
| **Available** | Computed quest state: every prerequisite verified, no attempt yet. Never stored |
| **Badge** | A recognition defined in `content/badges/`, awarded automatically from verified quests, or by a reviewer or the program (reviewer awards are not implemented in release one) |
| **Blocking / High / Medium / Low** | Audit finding severities. Blocking: unsafe, data-loss risk, architecture violation, or core flow unusable. High: material requirement failure or likely confusion. Medium: quality, resilience or accessibility weakness. Low: polish |
| **Bookend** | One of the two ends of delivery the role owns: intent (requirements, work items) and validation (tests, evidence) |
| **Build lock** | Exclusive file lock on `generated.lock` held for a whole build (ADR-035) |
| **Claimed XP** | XP from quests in `evidence_ready` or any later state. The participant's own record, never added to verified XP |
| **Confirmation** | An explicit "I mean this" in the request, required for `start-quest`, `submit-for-review` and `record-review`. A checkbox in the browser, `--confirm` on the CLI, `"confirm": true` in JSON (`state_machine.CONFIRMATIONS`) |
| **Content hash** | SHA-256 over a quest's front matter and body. Recorded on an attempt at start; a later mismatch is a warning (ADR-028) |
| **Content problem** | The single error shape every layer reports: file, stable ID, field path, rule, redacted received value, suggestion (`errors.ContentProblem`) |
| **Curriculum maintainer** | The person who writes quests, regions, badges, tracks and validators. Also called curriculum author |
| **DH7** | The one open release acceptance criterion: the final audit reports no unresolved blocking or high findings. Closes only on a round that finds none |
| **Evidence hash** | SHA-256 over an evidence package, excluding `validation/`, `submission.yaml` and `review*.yaml` (ADR-031) |
| **Evidence package** | The folder `participant/evidence/<quest-id>/<attempt-id>/` holding `PROOF.md`, `manifest.yaml`, logs, screenshots, validation results, the submission and review records |
| **Fork** | The participant's copy of the canonical repository; its `origin` remote. Curriculum arrives from the `upstream` remote |
| **Generated output** | Everything under `generated/`: HTML, JSON indexes, build manifest. Disposable and never authoritative (ADR-015) |
| **Lens** | One of the independent reviewers in an audit round, each with its own scope and worktree |
| **Loopback service** | The HTTP server in `serve.py`, bound to `127.0.0.1`, that serves the pages and performs actions |
| **Locked** | Computed quest state: at least one prerequisite is not verified. Never stored |
| **Machine-owned** | The ownership zone of `generated/` and `local-data/`: disposable, ignored by Git |
| **Migration** | A step that moves `progress.yaml` from one schema version to the next, validated before and after, reversible by restoring the original bytes (`migrations.py`) |
| **Needs changes** | Attempt state after a reviewer asks for changes or rejects. The participant resumes from it |
| **Origin check** | Refusal of a state-changing request whose `Origin` or `Referer` is present and is not `http` on a loopback name at the bound port |
| **Participant** | The learner who works through quests in their own fork |
| **Participant-owned** | The ownership zone of `participant/`: the participant's files, never replaced by an update |
| **Preflight** | `quest-app update`: read-only checks before taking an upstream update. Prints commands; runs no merge |
| **Prerequisite** | A quest that must be verified before another can start |
| **Program-owned** | The ownership zone of `content/`, `schemas/`, `templates/`, `assets/`, `quest_app/`, `validators/` and most of `docs/`: changed upstream |
| **Progress lock** | Exclusive file lock on `participant/.progress.lock` held across load, decision and write of every action (ADR-034) |
| **Progress store** | `store.ProgressStore`, the only writer of `participant/progress.yaml` |
| **PROOF.md** | The participant's narrative for one attempt: what was built, where, how to reproduce, what was checked, what remains, and a sensitive-values confirmation |
| **Proof files** | Digests of every declared proof path outside the evidence package, recorded on submission and review so a change to them is detected (ADR-031, amended) |
| **Proof requirement** | An entry in a quest's `proof.required` or `proof.optional`: a file, directory, validator result, command record, screenshot, demonstration or review |
| **Qualifying result** | A validator run whose outcome is `pass` or `warning`. Only these count toward `locally_validated` |
| **Quest** | One unit of curriculum: a Markdown file with YAML front matter under `content/quests/<region>/` |
| **Quest version** | An integer the author raises when a quest's evaluable meaning changes. An attempt keeps the version it started on |
| **Redaction** | Replacing secret-like values in validator output, check fields and messages before they are stored or shown (`secret_patterns.redact_text`) |
| **Region** | A group of quests on the map, such as Base Camp or Jira Jungle. Defined in `content/regions/` |
| **Registry** | `validators/registry.yaml`: the complete list of programs the application may run, with their constraints |
| **Request token** | A random value minted when the service starts, held in memory, substituted into served pages, and required on every state-changing request |
| **Review record** | `review.yaml` in the evidence package: the reviewer's decision, findings, verification statement, evidence hash and proof files. Superseded records are archived as `review-<timestamp>.yaml` |
| **Reviewer** | The person who evaluates submitted evidence and records a decision. Also called Questmaster |
| **Round** | One release audit pass against a specific commit, recorded under `docs/audits/` |
| **Secret scan** | Detection of secret-like values: over tracked files by `tools/secret_scan.py`, and over an evidence package by `evidence.scan_evidence`, where it blocks marking evidence ready and submission |
| **Stable ID** | A lowercase, hyphenated identifier that never changes when a title or filename does, and is never reused (ADR-012) |
| **Submission record** | `submission.yaml` in the evidence package: what was submitted, with its evidence hash and proof files |
| **Track** | An ordered or rule-based selection of quests, defined in `content/tracks/` |
| **Upstream** | The canonical repository participants take curriculum updates from |
| **Validator** | A program-owned Python function, registered by ID, that checks participant artifacts and returns structured findings. Never an authority over state (ADR-017) |
| **Validator outcome** | One of `pass`, `fail`, `warning`, `environment_failure`, `inconclusive`, `interrupted` |
| **Verification statement** | The reviewer's own words, at least twenty characters, saying what they checked and how. Required to approve |
| **Verified** | Attempt state produced only by a reviewer's approval, and re-derived from the review record on every load (ADR-011) |
| **Verified XP** | XP from verified quests only |
| **View model** | A display-ready object built in `view_models.py` for one page. Templates read only view models |
| **Workspace** | The object a validator receives, whose reads and writes are confined to the registered roots after symbolic links are resolved, and which exposes the attempt's own evidence files |
| **XP** | Experience points declared per quest (`xp`), shown as two separate totals: claimed and verified |
