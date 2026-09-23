# Release Audit — Round 9

Status: **complete.** Nineteen findings returned and all nineteen were accepted after
verification here. Every one is fixed, and every code fix carries a test that fails without it.

Commit under audit: `5248500` on `main`, the merge of `chore/round-08-audit`. The tree the
lenses read is what a clone of `main` gets.
Predecessor: `docs/audits/round-08-independent-audit.md`.

## Why this round exists

`docs/ACCEPTANCE-CRITERIA.md` leaves **DH7** open. Eight rounds have run and each one found
something. The criterion closes on a round that reports no unresolved blocking or high
findings — a round that finds nothing, not a round whose findings are all fixed.

## Method

Three lenses, each in its own worktree at `5248500`, each given only paths and a commit and
nothing else: no summary of what the author believed, no sight of each other's findings, and
no access to `docs/audits/`, which would have told them what earlier rounds concluded.

| Lens | Scope |
|---|---|
| Curriculum | The eight quests as curriculum, the rendered site, the templates and view models, the reviewer's decision screen driven for real against a running service, and the accessibility of what is actually generated |
| Engine | The action layer and its confirmation gate, the loopback service's read and write paths, `build.py` and `content_loader.py` end to end, the review and progress models, and the validator subsystem |
| Tooling, tests, documentation | The Makefile, `tools/`, `scripts/`, CI, the test suite judged as code that must be able to fail, and every document except this directory |

Round 8 named one theme to carry forward: **a rule enforced on whichever surface happened to
have a control for it.** It recurs below, and so does its twin — a check standing where a check
should be, looking at the wrong thing.

A lens is a source, not a verdict. Every finding below was re-verified here before it was
accepted, and one severity was lowered on that evidence.

## Findings

| # | Finding | Severity | Verification | Disposition |
|---|---|---|---|---|
| C1 | A proof row that a validator passed rendered `state-verified` — the gold tick this application uses nowhere else but for a reviewer's approval. The label read "Validated" and the badge said otherwise, and the badge is what a reader scans. `docs/ui/UI-SPECIFICATION.md:98` says not to shorten `locally_validated` to "verified". | High | Confirmed at `templates/components/proof_list.html.j2:12`, against `.state-verified` and the unused `.state-locally_validated` at `assets/css/app.css:209-213`. The lens proposed Blocking; the states stay distinct in the model, the store, the state machine and the label, and only the badge collapses them, which is the High band and not an architecture violation | **Fixed.** The mapping moved out of a nested template ternary into `PROOF_STATE_CLASSES`, and a test reads every badge on every generated page and refuses one labelled "Validated" that wears the reviewer's class. |
| C2 | Required evidence saved where the quest says to save it read "Not detected", for essentially every quest. Each file proof points into `logs/` or `screenshots/` under an attempt directory the author had to invent — quests write `attempt-001`, `_next_attempt_id` produces `<prefix>-attempt-001` — so the literal path never exists, and the fallback looked only for the bare filename at the top of the package. | High | Reproduced by the lens against a running service, and confirmed here at `quest_app/evidence.py:90-97`, `quest_app/store.py:294-302` and all eight quest files | **Fixed.** The authored path is re-read against the real package, keeping the subdirectory the quest asked for, so a file in the wrong subdirectory still does not count. Two tests: one that the right place is detected, one that the wrong place is not. |
| C3 | A reviewer's findings — severity, what is wrong, what they observed — were stored faithfully and rendered only on the reviewer's own page. The participant read "A reviewer asked for corrections" and had to open `review.yaml` in their own repository to learn what the corrections were. | High | Confirmed by grep across `templates/`: `finding` appears in `review.html.j2` and nowhere a participant looks. The lens drove a real `needs_changes` decision and read both participant pages | **Fixed.** A `reviewer_findings` component on the quest page and the evidence workspace, carrying severity, summary, observation and required change, for any decision that is not an approval. The test records a real decision through `record_decision`, rebuilds, and reads both pages. |
| C4 | Every refusal banner was `role="status"`, which is always polite. `docs/ui/UI-SPECIFICATION.md:226` reserves assertive announcement for urgent failure. A screen-reader user could be refused — including on the one action that produces verified XP — and hear nothing. | High | Confirmed at `quest_app/serve.py`, and the refusal is the banner an action's outcome arrives in | **Fixed** for the action-result refusal, which is the urgent one. The two error banners that are a page's own content stay polite: a reader lands on them and reads them in document order, and interrupting for text already in front of them is noise. |
| C5 | Base Camp's outcomes promised resuming interrupted agent work. Its one quest requires a re-run record and makes the recovery demonstration optional, and `base-camp-interruption-recovery` is still in `docs/CURRICULUM-BACKLOG.md`. | Medium | Confirmed against `content/regions/base-camp.yaml` and `content/quests/base-camp/repository-safety.md` | **Fixed** by narrowing the outcome to what the required proof establishes. `docs/CONTENT-MODEL.md` rule 8 says no validator can check this and names it as drift found in two successive rounds; this is the third. |
| E1 | Git porcelain v1 has a two-character status field, and `inspect` read it by splitting on the first space — while `_run` stripped the whole output, eating the first line's leading space. A tracked file edited and never staged kept its status letter on the front of its path, so `contains_uncommitted` could never match and the evidence workspace printed "yes" under evidence committed for evidence that was not. | High | Reproduced in a scratch repository: `changed_paths` held `('articipant/evidence/…',)`. The existing test passes because it stages first, producing `AM path`, which parses either way | **Fixed** in both halves — porcelain is read raw and parsed by column, and a rename reports where the file now is. The test edits a committed file and never stages it. |
| E2 | `_rebuild` runs after the state change is on disk and caught `OSError` only. A broken template raises `TemplateSyntaxError`, which left the CLI as a traceback with absolute paths in it — after the submission had been written, so the retry was refused for an attempt that really had moved. | High | Reproduced by the lens end to end, and by the test added here | **Fixed.** A rebuild failure is the partial success it always was, on every surface, and the CLI has a catch-all of its own. Round 7's test asserted a 500 for the non-`OSError` case; it now asserts the same complete answer the `OSError` case already got, which says more, not less. |
| E3 | The registry let a validator declare a capture size five times what `output_excerpt` can hold, and the runner wrote the excerpt at the declared size — so a passing run was refused whole for breaking its own schema. `_bounded` also appended its truncation notice past the limit, putting a validator registered at exactly the cap over it by construction, and nothing bounded the check list at all. | High | Reproduced by the lens at 24189 characters against a 20000 cap, and at 20021 for the notice. No shipped validator triggers it; the first one anyone writes that reports detail does | **Fixed.** One number now: the registry schema's maximum is the result schema's cap, the registry entries say what is true, the notice is counted inside the budget, and the check list has a bound with a check that says so. `tests/unit/test_validator_limits.py` fails if the two schemas drift apart. |
| E4 | `is_service_running` accepted any answer carrying the application header, whatever repository the answering service served. A second clone on one machine made `quest-app build` publish pages saying the service was running, with live-looking controls, for a repository that had no service. | High | Found independently by two lenses and reproduced here: a worktree with no `local-data/` and no service reported `is_service_running: True` because another checkout held 8765. The engine lens proposed Medium and the tooling lens High; the participant-facing consequence is the High band | **Fixed.** The service says which repository it serves, as a hash of its repository and participant roots, and the probe requires a match. A service that predates the header is treated as somebody else's, which is the only safe reading. |
| E5 | `do_POST` had no outer answer, though `do_GET` has had one since round 7. Its inner catch-all answers by writing to the socket, so when the socket was what failed — a participant who submits and closes the tab — that write raised again, past every handler, onto the terminal. | Medium | Reproduced by the lens with a socket closed mid-request; the same probe against `do_GET` produces nothing | **Fixed**, with the same wrapper `do_GET` carries. Two tests: an unexpected failure is answered, and a reader who goes away is not a traceback. |
| E6 | Any `OSError` escaping the read path was reported with the write path's sentence: a page the service could not open told the participant their change could not be written to their participant directory, and sent them to inspect a tree that was never involved. | Medium | Reproduced by the lens with an unreadable generated page | **Fixed.** A read failure names the generated site and `quest-app build`. |
| E7 | `duplicate_section_titles` compared exact title strings while `parse_sections` keys on the casefolded, slugged title. `## Mission` beside `## MISSION` passed the guard and then overwrote it: the build succeeded, said nothing, and the page showed the second block where the author's Mission should have been. | Medium | Reproduced directly against `duplicate_section_titles` | **Fixed.** One `section_key` function decides the key, and the guard groups by it and names the colliding pair. This is the round's second example of a check standing in the right place looking at the wrong thing. |
| E8 | `update.preflight` returned a field called `backup_branch` and creates nothing: every command in `PERMITTED_COMMANDS` is read-only. A field named that way reads as a branch that exists. | Low | Confirmed at `quest_app/update.py` | **Fixed** by naming it `proposed_backup_branch` and correcting the module docstring, which also claimed it creates one. |
| E9 | `_review_context` asserted its own invariant, which `python -O` removes; the next line would then raise an `AttributeError` from inside a page render. | Low | Confirmed at `quest_app/build.py` | **Fixed** with an explicit raise, as every other invariant in the codebase has. |
| E10 | Neither POST body reader rejected a duplicate `Content-Length`, though the GET path has refused exactly that since round 7, citing request smuggling on a kept-alive connection. Not exploitable as it stands — the refusal path closes the connection first — but the asymmetry is a trap for the next change to it. | Low | Confirmed by the lens; both readers took the first header and walked past the second | **Fixed.** One `_declared_length` for both readers, refusing a repeated header and `Transfer-Encoding` the way the GET path does. |
| T1 | The symlink half of `resolve_participant_path` had no test. Deleting the re-check that a resolved path is still inside the participant root left the whole suite green, while the equivalent guard in `tools/clean.py` has had symlink tests since Stage 1. | Medium | Reproduced by the lens by deleting the line and running ~620 tests, and confirmed here by grep: no test names `resolve_participant_path` and a symlink together | **Fixed** with tests for both directions — a link out of the tree is refused, a link within it is not — and the guard's removal now fails one of them. |
| T2 | `scripts/build_user_guide_html.py` read two stylesheets from `~/.claude/skills/…` — a directory on one machine in the world, not in this repository and not a dependency — while `CONTRIBUTING.md` told every contributor to run it. | Medium | Confirmed at `scripts/build_user_guide_html.py:20`; `grep -rn "\.claude/skills"` returns that one line | **Fixed** by making the location configurable, refusing with a message that names what is missing and where to point it, and correcting CONTRIBUTING to say the built guide is committed so nobody has to rebuild it. Vendoring the two files was rejected: their provenance is the maintainer's authoring tool and their licence is not stated. |
| G1 | `serve --port 0` asks the operating system for a free port, and zero is falsy. `run_service` tested the flag for truth twice, discarded it, and bound the default — then refused with "choose another port with `--port`", which is what had just been typed. | Medium | Reproduced directly: with the fix the same command binds an ephemeral port | **Fixed** with `is not None` on both tests. See below for how it was found. |

## Found while running the gates

`make check` failed three tests in `tests/security/test_service.py` on the first run of this
round. All three were the same thing, and it was not a test problem.

Two review lenses were running services of their own, and one held `127.0.0.1:8765`.
`_port_entries` always probes the configured default port, so tests rooted in `/tmp` asked the
stranger and believed it (E4), and the test that spawns a service with `--port 0` had that flag
discarded and collided with it (G1). Reproduced afterwards with nothing but the documented
workflow: `make serve` in one terminal, `make check` in another, same three failures.

Both defects are fixed. The tests that call a port dead now use one nothing can be answering
on, because a test that depends on what else is running on the machine is not a test. With a
service running on 8765, all seventy-eight service tests now pass.

That is the third round in which the way the round itself is run turned out to matter, and the
second in which it surfaced a real defect rather than noise. It is worth keeping: running the
gates beside a working installation is a condition the suite should survive, and twice now it
has not.

One test also had to change its expectation rather than its subject. Round 7's
`test_an_unexpected_failure_still_answers_the_json_caller` asserted a 500 for a rebuild that
raised something other than `OSError`, because that was the only failure `_rebuild` did not
catch. The change had already landed on disk in both cases, so a 500 told the caller their
request had failed when it had not, and their retry was then refused for an attempt that really
had moved. It now asserts the partial-success answer the `OSError` path already gave — the
state, the advisory, the exception type, and no absolute path — which is a stronger assertion
than the status code it replaced.

## Gates

| Gate | Result |
|---|---|
| `make check` | pass — 643 passed, 42 deselected |
| `make test-ui` | pass — 42 passed |
| `make validate-content` | pass — 8 quests, 8 regions, 4 badges, 1 track, 0 warnings |
| `make verify-package` | pass — the exported archive installs, validates and builds on its own |
| Clean clone from `origin` at this branch's head | pass — `git clone --branch chore/round-09-audit`, then `make setup`, `make check` (641 passed, 3 skipped), `validate`, `build` and `make verify-package` |
| CI on this branch | pass — `check` on 3.10, 3.12 and 3.13, `browser`, and `clean-export`, green on every commit of it, including the last one that changed code (`e981a51`) |
| `make check` beside a running `make serve` | pass — the condition that failed three tests at the start of this round |
| Each fix reverted one at a time | every code fix is caught by a test. The badge mapping, the evidence path resolution, the reviewer findings panel, the assertive refusal, the porcelain parser, the broad rebuild catch, the excerpt bound, the section key, the POST wrapper, the read message, the repository signature, the participant-path re-check and the `--port 0` flag were each reverted and the test that covers them failed |

The suite grew from 624 to 643. `make test-ui` is unchanged at 42.

## Verdict

**Round 9 does not close DH7.** Nineteen findings returned: none blocking, eight high, seven
medium, four low, and none rejected. Every finding is fixed and every code fix has a test that
fails without it.

Round 8's theme held. The confirmation gate it moved in front of every mutating call is sound —
the engine lens could not get past it on any surface, and could not reach a verified state or
verified XP by any route but a reviewer's approval. What this round found instead is the same
shape one level down: **a rule applied to the half of the problem someone was looking at.**

The porcelain parser handled the staged half and the strip ate the other. `_rebuild` answered
the filesystem half of its own failures and let the rest out as a traceback. The read path
borrowed the write path's words. `do_GET` got an outer answer in round 7 and `do_POST` did not.
The GET path refused a duplicate `Content-Length` and both POST readers walked past one. The
duplicate-heading guard compared titles while the parser compared keys. And the service probe
asked whether a service was running rather than whether this repository's was, which no lens
would have noticed had two of them not been running at once.

On the curriculum side the pattern is the same and the cost is higher, because it reaches the
participant: the badge for a machine's check and the badge for a person's approval were the
same gold tick; the reviewer's reasons were rendered for the reviewer and not for the person
who has to act on them; and the path a quest tells a participant to save evidence to was not a
path anything looked in.

Round 10 should run against the merge commit, with the same three lenses and the same rule that
a lens is a source rather than a verdict. Point it at:

- the reviewer flow driven for real again, now that the participant's pages carry the
  reviewer's findings, and at what a reviewer sees after a second decision on the same attempt;
- the validator subsystem end to end, which round 9 bounded but did not exercise with a
  validator written for the occasion — `process.communicate()` still reads a child's whole
  output into memory before any limit applies, bounded by the timeout and nothing else;
- `view_models.py` and `progress_calc.py`, which no lens has read end to end in any round;
- `migrations.py` and `update.py` with a real version bump and a real upstream, which nothing
  has driven;
- the generated site read as a participant with a screen reader and at 200% zoom, which this
  round reasoned about from the CSS rather than measuring;
- and the tests again. Round 8 found three that could not fail; this round found the suite
  itself could fail for reasons outside it, and one test that passed because a flag it relied
  on was silently ignored. A test that cannot fail and a test that fails for the wrong reason
  are the same defect seen from two sides.
