# Part 4. The system in motion

This part walks through the main flows. Each diagram is drawn from the code, and each flow
names the functions that implement it so a reader can check.

## 4.1 How to read these diagrams

The activity diagrams are UML-style, drawn as Mermaid flowcharts:

- a **lane** (a labelled box) groups the steps one role or one process performs;
- a rounded box is an action; a diamond is a decision; a circle marks the start; a double
  circle marks the end;
- a box whose text begins **Refused** is a place the flow stops with a message and changes
  nothing.

Every mutating action in these flows passes through `ActionRunner.perform`
(`quest_app/actions.py`), whichever surface asked. It performs three steps before the action
itself: it refuses `start-quest`, `submit-for-review` and `record-review` without a
confirmation; it takes the progress lock; and it loads and validates the whole world
(`pipeline.load_world`). If content or participant state does not validate, every action is
refused. The diagrams show these steps once, in flow 4.2, and abbreviate them after that.

The commands in this part are the command-line equivalent of the browser controls. Run them
from the repository root with the virtual environment active (`source .venv/bin/activate`).

## 4.2 A participant starts a quest and assembles evidence

**Walkthrough.**

1. The participant chooses an available quest and confirms "Start this quest and create an
   evidence package in my repository".
2. The action layer checks the confirmation, takes the progress lock, and loads the world.
   It refuses a quest ID that is not in the loaded content, so no caller-supplied string
   ever reaches the filesystem as a path.
3. It refuses a locked quest: every prerequisite must be *verified* (ADR-033). This check is
   in the action layer, not only in the page, so the CLI cannot bypass it.
4. `store.start_attempt` creates `progress.yaml` if this is the participant's first action,
   refuses if the quest already has an attempt, mints the attempt ID, and creates the
   evidence package from a template: `PROOF.md` with its six headings, `manifest.yaml`, and
   empty `validation/`, `screenshots/` and `logs/` folders. Existing files are never
   overwritten.
5. It appends the attempt (quest version and content hash included), validates the new
   `progress.yaml` against its schema, writes it atomically, and appends a line to
   `ACTIVITY.md`.
6. The site is rebuilt. A failed rebuild becomes an advisory; the attempt is still recorded
   (ADR-038).
7. The participant does the work in their own editor and tools: artifacts under
   `participant/`, and `PROOF.md` filled in.
8. `mark-evidence-ready` runs the secret scan over the whole package. Any finding, any file
   the scan cannot read, and any symbolic link leading outside the package blocks it. The
   message names the file and line, never the value.

```bash
quest-app action start-quest --quest base-camp-repository-safety --confirm
quest-app action mark-evidence-ready --quest base-camp-repository-safety
```

```mermaid
flowchart TB
  subgraph PL["Participant"]
    s0(("start")) --> p1["Choose an available quest<br/>and confirm Start"]
    p5["Build artifacts, fill in PROOF.md"] --> p6["Mark evidence ready"]
  end
  subgraph AL["Action layer: actions.py"]
    a0["Check: confirmed, content valid,<br/>quest exists, prerequisites verified"]
    a1{"Pass?"}
    a7["Secret scan of the package:<br/>no finding, no unreadable file,<br/>no link out of the package"]
    a8{"Clean?"}
    rA["Refused with the reason<br/>nothing written"]
  end
  subgraph ST["Store: store.py"]
    t1{"No attempt yet?"}
    t2["Create progress.yaml if missing<br/>mint attempt ID<br/>create evidence package"]
    t3["Validate, atomic write<br/>ACTIVITY.md line, rebuild"]
    e1(("in_progress"))
    t4["Validate, atomic write<br/>ACTIVITY.md line, rebuild"]
    e2((("evidence_ready")))
  end
  p1 --> a0 --> a1
  a1 -- no --> rA
  a1 -- yes --> t1
  t1 -- no --> rA
  t1 -- yes --> t2 --> t3 --> e1
  e1 -.-> p5
  p6 --> a7 --> a8
  a8 -- no --> rA
  a8 -- yes --> t4 --> e2
```

*Figure 6. Starting a quest and marking evidence ready (`ActionRunner._perform`,
`store.start_attempt`, `ActionRunner._require_clean_secret_scan`). Marking evidence ready
needs no confirmation, but it takes the lock and loads the world like every action.*

## 4.3 Running a validator

**Walkthrough.**

1. The participant runs one of the quest's validators. The action layer refuses a validator
   the quest does not declare, and a quest with no attempt.
2. The registry entry is looked up by ID. `run_validator` refuses a validator not
   registered for this quest, and binds parameters against their declared types and allowed
   values; there is deliberately no free-text parameter type.
3. The runner builds the child's environment from a minimal `PATH` plus the registry
   allowlist, sets the working directory from the registry, and starts
   `python -s -c <bootstrap>` in a new session and process group. The specification (roots,
   parameters, the attempt's evidence root) is sent on standard input. There is no shell and
   no argument built from input.
4. The child imports the entrypoint, but only from the `validators` package, and calls it
   with a `Workspace` and an output collector. The validator's own prints are moved to
   standard error so they cannot corrupt the result, which is written as JSON on the
   original standard output.
5. The parent reads both streams as they arrive. Five things can end the run: the child
   exits; the timeout passes; a stream exceeds 1 MiB; the child exits and one second passes
   while grandchildren still hold a pipe; or the child's result channel (its `stdout`) closes
   while the OS process is still alive a second later, which means something the validator
   left running — a non-daemon thread is the case this exists for — is holding the
   interpreter open after it already returned its result (round 12 finding E11). In every case
   the whole process group is killed.
6. Each reported check is checked against the result schema's own `id` pattern and `outcome`
   enum before it is trusted. One outside either is replaced with a check reporting that a
   check was malformed, and the run's outcome is forced to `environment_failure`: a validator
   that cannot describe its own check correctly has a defect in itself, not the participant's
   work (round 12 finding E6). The run is then classified (next table). Every result carries
   at least one check, so an `interrupted` or `environment_failure` run still tells the
   participant what happened.
7. The complete output and every check field are redacted *first*, then truncated: the
   excerpt to the registered limit (at most 20,000 characters), each check field to its own
   schema limit. Redacting before truncating, never after, means a secret-shaped token cannot
   be cut in half at the boundary and stored in clear (round 12 finding E7).
8. The result is validated against `validation-result.schema.json` and written atomically to
   `validation/<run-id>.json` in the attempt's package. The site is rebuilt. **The attempt's
   state does not change.**
9. Later, `mark-locally-validated` succeeds only if every declared validator's latest result
   is `pass` or `warning`.

| Outcome | How it is reached (`validator_runner.py`) | Qualifies? |
|---|---|---|
| `interrupted` | The timeout passed | No |
| `environment_failure` | Output over 1 MiB; nonzero exit that the validator's own process produced; empty output; unreadable JSON; a check outside the schema's `id` or `outcome`; the validator raised; the validator tried to leave its roots; or it reported an environment failure itself | No |
| `inconclusive` | No checks, every check skipped, or any check inconclusive (and none failed) | No |
| `fail` | Any check failed | No |
| `warning` | Any check warned, none failed or were inconclusive | Yes |
| `pass` | Every check passed | Yes |

A nonzero exit is trusted over anything printed, *except* when the runner produced it itself
by killing a process whose result channel had already closed (step 5's fifth case): that exit
status describes the runner's own cleanup, not a judgment the validator passed on itself, so
the result it already wrote is kept rather than discarded (round 12 finding E11).

```bash
quest-app action run-validator --quest base-camp-repository-safety \
  --validator validate-repository-foundation
quest-app action mark-locally-validated --quest base-camp-repository-safety
```

```mermaid
flowchart TB
  subgraph PL["Participant"]
    s0(("start")) --> p1["Run a validator of the quest"]
  end
  subgraph AL["Action layer"]
    a1["Check: declared by the quest,<br/>attempt exists, registered for<br/>this quest, parameters valid"]
    a2{"Pass?"}
    rA["Refused with the reason"]
  end
  subgraph RP["Runner parent: validator_runner.py"]
    r1["Constructed environment,<br/>registry working directory,<br/>new process group"]
    r3{"Ended by?"}
    c1["interrupted"]
    c2["environment_failure"]
    r4["Sanitize each check against<br/>the schema's id and outcome;<br/>a malformed one is replaced<br/>and forces environment_failure"]
    r5["Classify checks:<br/>fail, inconclusive, warning, pass"]
    r6["Kill the process group;<br/>redact the complete output<br/>and checks, then truncate"]
    r7{"Valid result?"}
    r8["Atomic write validation/run-id.json<br/>rebuild; attempt state unchanged"]
    rB["Refused: run discarded"]
    p9((("result shown on<br/>the validation page")))
  end
  subgraph CH["Child process: validator_child.py"]
    h1["Import entrypoint from validators/<br/>run(workspace, output)<br/>result JSON on stdout"]
  end
  p1 --> a1 --> a2
  a2 -- no --> rA
  a2 -- yes --> r1 --> h1 --> r3
  r3 -- "timeout" --> c1
  r3 -- "over 1 MiB, or a nonzero<br/>exit the process itself<br/>produced, unreadable output" --> c2
  r3 -- "exit 0 with JSON; or its<br/>result channel closed and a<br/>leftover thread's process<br/>was killed a second later" --> r4
  c1 --> r6
  c2 --> r6
  r4 --> r5 --> r6 --> r7
  r7 -- no --> rB
  r7 -- yes --> r8 --> p9
```

*Figure 7. Running a validator (`ActionRunner._run_validator`, `run_validator`, `_collect`,
`_sanitize_checks`, `classify`, `validator_child.main`, `evidence.store_result`).*

**Fixed since round 12.** Findings E6, E7 and E11 above are what this diagram now shows:
check sanitization forcing `environment_failure` on a malformed check (E6), redaction before
truncation (E7), and a closed result channel with a killed leftover process no longer read as
`interrupted` (E11). **Still open, as a known limitation, not a defect (E9, Low):** a
grandchild that starts its own session survives cleanup, because nothing short of an
operating-system sandbox reaches a process that has left the group `killpg` targets
(`docs/VALIDATOR-CONTRACT.md`; deferred item D9).

## 4.4 Submitting for review

**Walkthrough.**

1. The participant confirms "Submit this evidence for review. A reviewer will read it".
2. `review.readiness_problems` collects every problem at once, so the participant sees all
   of them together. **Blocking** problems: the attempt is not `evidence_ready` or
   `locally_validated`; the package is missing; or the scan found a secret, a link leading
   outside the package, or a file too large for the scan to read — three kinds of scan
   finding, worded separately by `evidence.scan_kinds` so a participant is not sent looking
   for a credential that was never there (round 12 finding C3). **Advisory** problems: a
   declared validator has not been run, or its latest result does not qualify.
3. Any blocking problem refuses the submission.
4. Otherwise `create_submission` computes the evidence hash and the proof-file digests,
   writes `submission.yaml` (validated against its schema) into the package, moves the
   attempt to `submitted`, records the submission ID on the attempt, and appends an activity
   line.
5. The site is rebuilt, and the result carries the advisories and the Git commands for the
   next step.
6. **The application never pushes, opens a pull request or merges** (ADR-032). It prints the
   commands: create a branch, add the evidence and `progress.yaml`, commit, push, open a pull
   request. The participant runs them. Pushing is a claim, on the participant's behalf, that
   the work is ready, and that claim is theirs to make.

```bash
quest-app action submit-for-review --quest base-camp-repository-safety --confirm
```

```mermaid
flowchart TB
  subgraph PL["Participant"]
    direction TB
    s0(("start")) --> p1["Confirm submit"]
    p7["Run the printed Git commands:<br/>branch, add, commit, push, open PR"]
    e0((("end")))
  end
  subgraph AL["Action layer and review.py"]
    direction TB
    a1{"Confirmed?"}
    a2["Lock, load, validate"]
    a3["readiness_problems:<br/>state, package present, scan kinds<br/>(secret, link, oversize), validator results"]
    a4{"Any blocking problem?"}
    a5["Compute evidence hash<br/>and proof-file digests"]
    a6["Write submission.yaml<br/>validated, atomic"]
    a7["Transition to submitted<br/>record submission_id<br/>ACTIVITY.md line"]
    a8["Rebuild; return advisories<br/>and next-step commands"]
    rA["Refused: confirm it"]
    rB["Refused: every blocking problem listed"]
  end
  p1 --> a1
  a1 -- no --> rA
  a1 -- yes --> a2 --> a3 --> a4
  a4 -- yes --> rB
  a4 -- no --> a5 --> a6 --> a7 --> a8 --> p7 --> e0
```

*Figure 8. Submitting for review (`ActionRunner._submit`, `review.create_submission`,
`review.readiness_problems`, `review.submission_instructions`).*

## 4.5 The reviewer's decision

**Walkthrough.**

1. The reviewer reads the evidence: the reviewer page (`/review/<quest-id>/`) shows the
   quest and its version, the attempt, the submission, the validator results, the secret-scan
   result, and whether anything changed since submission, naming each changed path.
2. The reviewer chooses **approved**, **needs changes** or **rejected**, fills in the form,
   and confirms. The confirmation text depends on the decision; only the approval text says
   it produces verified XP.
3. `record_decision` refuses a decision that is not one of the three values, an attempt that
   is not `submitted`, and — since round 12 finding E4 — an attempt with no readable
   `submission.yaml`. The loader already refuses a hand-edited `submitted` state with no
   submission record at load (Part 3, Section 3.5); this check is `record_decision`'s own,
   so a `submitted` state built or altered some other way cannot reach a decision either.
4. An **approval** needs a verification statement of at least twenty characters saying what
   was checked and how. Then the **changed-since-submission gate**: the current evidence hash
   and each recorded proof-file digest are compared with `submission.yaml`. If anything
   differs, the approval is refused unless the reviewer acknowledges the change. Approving
   changed evidence would approve something the reviewer has not seen.
5. **Needs changes** and **rejected** need at least one finding with a severity, a summary
   and the evidence observed.
6. The review record is validated against its schema. An existing `review.yaml` is archived
   as `review-<timestamp>.yaml` rather than overwritten, so a change of mind stays visible.
   The new record is written atomically.
7. `_apply_decision` sets the attempt state: `verified` for an approval, `needs_changes`
   otherwise. This is the only code that writes `verified`.
8. The site is rebuilt. On the next load, `verified` is re-derived from this record
   (Part 3, Section 3.5), and verified XP and badges follow from it.
9. After `needs_changes`, the participant runs `resume-quest` and the cycle repeats.

```bash
quest-app action record-review --quest base-camp-repository-safety \
  --decision approved \
  --reviewer "Your Name" \
  --statement "What you checked and how, in your own words." \
  --confirm

quest-app action record-review --quest base-camp-repository-safety \
  --decision needs_changes \
  --reviewer "Your Name" \
  --finding "high:What is wrong:Where you saw it" \
  --confirm
```

Add `--acknowledge-changed-evidence` to approve evidence that changed after submission; the
browser form has the same checkbox.

```mermaid
flowchart TB
  subgraph RV["Reviewer"]
    s0(("start")) --> v1["Read the reviewer page:<br/>quest, attempt, submission,<br/>results, scan, changes"]
    v1 --> v2{"Decision"}
    v3["Re-read what changed,<br/>tick acknowledge"]
  end
  subgraph AP["Application: review.py"]
    a0["Check: confirmed, attempt is<br/>submitted, submission record readable"]
    a1{"Statement of<br/>20+ characters?"}
    a2{"Changed since<br/>submission and not<br/>acknowledged?"}
    a4{"At least one<br/>finding?"}
    a5["Validate review record, archive<br/>old review.yaml, atomic write"]
    a6["State: verified"]
    a7["State: needs_changes"]
    rA["Refused with the reason;<br/>a change names each path"]
  end
  subgraph PT["Participant"]
    t1((("verified XP<br/>counted")))
    t2["resume-quest, fix,<br/>resubmit"]
  end
  v2 -- approved --> a0
  v2 -- "needs changes<br/>or rejected" --> a0
  a0 -- approval --> a1
  a0 -- other --> a4
  a1 -- no --> rA
  a1 -- yes --> a2
  a2 -- no --> a5
  a2 -- yes --> rA
  rA -.-> v3
  v3 -.-> a0
  a4 -- no --> rA
  a4 -- yes --> a5
  a5 -- approval --> a6 --> t1
  a5 -- other --> a7 --> t2
```

*Figure 9. Recording a reviewer decision (`ActionRunner._record_review`,
`review.record_decision`, `review.changes_since_submission`, `review._apply_decision`).*

**Provenance.** A reviewer is identified by the display name in the record and by Git
history. Records are not signed (ADR-030). The application refuses every internally
inconsistent claim, but a participant with write access to their own repository could write
a record naming someone else. Programs that need more should review through pull requests so
Git carries the identity. Release one also has no role separation: a participant can open the
reviewer page for their own work (deferred item D11).

## 4.6 The build and render pipeline

**Walkthrough.**

1. `quest-app build` (also `make build`), `quest-app serve`, and every action's rebuild all
   call the same pipeline.
2. `load_world` loads content first: discover, parse strictly, validate against schemas,
   normalize, then apply cross-document rules and check validator references. Participant
   state is read only if content is valid, because an attempt cannot be judged against a
   curriculum that does not make sense. A missing `progress.yaml` is normal.
3. Participant state is read with bounded reads: each file must be an ordinary file under a
   size ceiling, 2 MB for `progress.yaml`, a submission or a review record, 8 MB for a
   validation result. Round 12 found this bound applied only to `progress.yaml`: a FIFO or a
   link to a device in place of a validation result, or a stray `review*.yaml` with broken
   YAML, could hang or crash `build` (findings E2 and E3). Both record kinds are now read the
   same bounded way, and review records are enumerated by one shared definition
   (`progress.review_archive_paths`) instead of two globs that used to disagree. A
   `validation/` directory that is itself a link is reported and nothing in it is read.
   `verified` and `locally_validated` claims are checked against their records.
4. **If anything is an error**, the build renders the error page (U11) to
   `local-data/build-errors/index.html`, prints its path, exits non-zero, and leaves the
   published site untouched.
5. **If valid**, `build_site` takes the build lock and renders into `generated.building`:
   derived states, totals, badges and recommendations; one view model per page; every page
   through Jinja2 with autoescaping; the JSON indexes and the manifest; a copy of `assets/`.
6. The publish is two renames. Only then does a reader see the new site.

```bash
make validate-content
make build
```

```mermaid
flowchart TB
  s0(("build, serve, or<br/>an action's rebuild"))
  subgraph LD["Load: pipeline.load_world"]
    l1["Discover regular files; strict safe YAML;<br/>front matter and Markdown tokens"]
    l3["JSON Schema per document;<br/>normalize; sanitize Markdown"]
    l5["Cross-document rules,<br/>validator references"]
    l6{"Valid?"}
    l7["Bounded read of participant state;<br/>re-derive verified, locally_validated"]
    l8{"Valid?"}
  end
  subgraph ER["Failure path: build.render_error_page"]
    x1["Error page to<br/>local-data/build-errors/"]
    x2((("exit non-zero,<br/>site untouched")))
  end
  subgraph BD["Render: build.build_site"]
    b0["Take generated.lock;<br/>states, totals, badges, recommend"]
    b2["View model per page;<br/>Jinja2 into generated.building"]
    b4["indexes/*.json, build-manifest.json,<br/>copy assets"]
    b5["Swap by rename:<br/>generated.building becomes generated"]
    b6((("new site<br/>published")))
  end
  s0 --> l1 --> l3 --> l5 --> l6
  l6 -- no --> x1
  l6 -- yes --> l7 --> l8
  l8 -- no --> x1
  l8 -- yes --> b0
  x1 --> x2
  b0 --> b2 --> b4 --> b5 --> b6
```

*Figure 10. The build pipeline (`pipeline.load_world`, `content_loader.load_content`,
`build.build_site`, `build._swap`, `build.render_error_page`).*

**Fixed since round 12.** Findings E2 and E3 (bounded reads for validation results and review
records, above) and E8 are closed: evidence files are hashed by streaming a megabyte at a
time instead of holding each one in memory, and the secret scan reads at most 2 MB of a file
before treating it as a scan finding rather than pattern-matching a file that used to take a
build about a minute and hold both locks while it ran.

## 4.7 Taking an upstream curriculum update

**Walkthrough.**

1. The participant runs the preflight. It checks: a Git repository; no merge in progress
   (checked first, because the working-tree advice would otherwise be to commit conflict
   markers); a clean working tree; an `upstream` remote; the participant folder. Each is
   `pass`, `warning` or `fail`.
2. It reports what a migration would do and which attempts are on an older quest version
   than upstream now publishes. Those attempts are not moved.
3. If anything fails, it prints the fix for each and exits non-zero. Otherwise it prints a
   backup branch name and the commands, and stops. It runs no merge and creates no branch.
4. The participant runs the printed commands: create the backup branch, fetch, read the
   incoming log, merge. Because curriculum and participant work are in separate folders, the
   merge touches only program-owned files unless both sides edited the same file.
5. The participant runs `make validate-content`. If it reports that the progress schema is
   old, they run `make migrate`.
6. The migration refuses during a merge, takes the progress lock, reads the file with a
   bounded read, applies each step (never advancing an in-progress attempt's quest version,
   never dropping an unknown field), validates, writes atomically, reloads the whole world,
   restores the original bytes if the reload fails, and — since round 12 finding E10 —
   appends an activity line naming the migrations it kept, the same as every other writer of
   `progress.yaml`.
7. If the merge goes wrong: `git merge --abort`, or reset to the backup branch.

```bash
quest-app update
make update-check
make migrate
```

```mermaid
flowchart TB
  subgraph PL["Participant"]
    s0(("start")) --> p1["quest-app update"]
    p2["Fix each failed item"]
    p3["Run the printed commands:<br/>backup branch, fetch,<br/>read the log, merge"]
    p4{"Merge clean?"}
    p5["git merge --abort, or<br/>reset to the backup branch"]
    p6["make validate-content"]
    p7{"Schema old?"}
    p8["make migrate"]
    e0((("updated,<br/>participant/ intact")))
  end
  subgraph UP["Preflight: update.py, read-only Git"]
    u1["Check: repository, no merge,<br/>clean tree, upstream remote,<br/>participant folder. Report<br/>migration steps and attempts<br/>on older quest versions"]
    u3{"Any failed?"}
    u4["Print backup branch name<br/>and exact commands; stop"]
  end
  subgraph MG["Migration: update.apply_migrations"]
    m1["Refuse during a merge; take lock;<br/>bounded read, keep original bytes"]
    m2["Apply steps: keep attempt<br/>versions and unknown fields.<br/>Validate, atomic write"]
    m4{"World loads?"}
    m5["Restore original bytes"]
  end
  p1 --> u1 --> u3
  u3 -- yes --> p2 --> p1
  u3 -- no --> u4 --> p3 --> p4
  p4 -- no --> p5
  p4 -- yes --> p6 --> p7
  p7 -- no --> e0
  p7 -- yes --> p8 --> m1 --> m2 --> m4
  m4 -- yes --> e0
  m4 -- no --> m5
```

*Figure 11. Taking an upstream update (`update.preflight`, `update.update_instructions`,
`update.apply_migrations`, `migrations.migrate`). The flow starts at `start` in the
Participant lane.*

**Fixed since round 12.** A `locally_validated` attempt used to become a load error the
moment an update added a validator to its quest, with every action then refused, including
the `run-validator` that would have cleared it (finding E5); ADR-017's amendment (Part 3,
Section 3.5) now warns instead when the attempt still has a qualifying result from before the
update. `make migrate` now writes the activity line above (finding E10).

## 4.8 One browser action through the loopback service

**Walkthrough.** The participant presses a button on a served page, for example Submit on the
quest page. The page is an ordinary HTML form; no JavaScript is needed.

1. The browser posts `application/x-www-form-urlencoded` to
   `/api/action/submit-for-review/<quest-id>`. The form carries the per-run token, which the
   service substituted into the page when it served it, and the confirmation checkbox.
2. **Host check.** A `Host` header that is not a loopback name is refused, which defeats DNS
   rebinding (ADR-041).
3. **Origin check.** If `Origin` or `Referer` is present, it must be `http` on a loopback
   name at the bound port.
4. **Body.** The content type must be the form type and the declared length at most 64 KiB,
   checked before the body is read.
5. **Token.** Compared in constant time with the token in memory.
6. **Allowlist.** The action must be in `MUTATING_ACTIONS`; the path carries only IDs.
7. **Confirmation.** A confirmed action without the checkbox is sent back to the page with the
   confirmation text. `ActionRunner.perform` checks the same rule again, so the JSON endpoint
   and the CLI meet it too (ADR-033).
8. **Locks.** The service lock serializes requests in this process; the progress lock
   serializes against a CLI action in another process.
9. **Load, guards, write.** The action layer loads the world, applies the action's guards,
   and writes records atomically.
10. **Rebuild.** The site is rebuilt with live controls, because the service is running.
11. The service answers `303 See Other` back to the page, with a flash message for a refusal
    or an advisory. Every failure path answers with a status and a message; none escapes as a
    traceback.

```mermaid
sequenceDiagram
  participant B as Browser
  participant S as serve.py
  participant A as ActionRunner
  participant F as participant/
  participant G as build.py
  B->>S: POST form: action, quest ID, token, confirm
  Note over S: Host is loopback, else 403
  Note over S: Origin or Referer, if sent,<br/>is loopback at bound port, else 403
  Note over S: Form type, else 415<br/>length 1 byte to 64 KiB, else 400
  Note over S: Token matches, constant time, else 403
  Note over S: Action allowlisted, else 400
  Note over S: Confirmed, else back with the text
  S->>A: perform, under the service lock
  Note over A: Confirmation checked again
  A->>F: flock .progress.lock
  Note over A: load_world, guards for the action
  A->>F: atomic writes, ACTIVITY.md line
  A->>G: rebuild with live controls
  G-->>A: pages, or an advisory
  A->>F: release lock
  A-->>S: result and advisories
  S-->>B: 303 to the page, flash message
  B->>S: GET the page
  S-->>B: HTML with the token substituted
```

*Figure 12. A form action through the loopback service (`serve.Handler._post`,
`_handle_form_action`, `_host_is_acceptable`, `_origin_is_acceptable`, `_read_form_body`,
`_token_matches`, `ActionRunner.perform`).*

**Fixed since round 12.** Finding C1 (Blocking) was that every page was served with
`Referrer-Policy: no-referrer` (both the header and the `<meta name="referrer">` tag), so
Chromium sent `Origin: null` on a same-origin form POST, and `_origin_is_acceptable` at step 3
parsed `null` as a non-`http` origin and refused it — only the CLI, which sends no `Origin` at
all, could change state, and no test had submitted a form end to end. The policy is now
`same-origin`: a same-origin POST carries its real origin and passes the check exactly as a
CLI request does; a cross-origin POST still sends no `Origin` and is still refused, unchanged.
Verified against real Chromium, not assumed. Two browser tests submit real forms (start-quest,
record-review), accept the confirmation, and check the resulting files on disk; both fail with
403 if the old policy is put back.
