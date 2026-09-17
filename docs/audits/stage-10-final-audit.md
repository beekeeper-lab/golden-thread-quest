# Stage 10 — Final Independent Release Audit

**Audited commit:** `1418b78`
**Auditor:** independent review agent, fresh context, read-only, 92 tool calls
**Recommendation:** **`do-not-release`** — 3 blocking, 4 high, 6 medium, 4 low
**Status after fixes:** every blocking and high finding corrected; re-audit commissioned.

## The shape of it

Three blocking defects sat on the product's primary path, and the suite was green because
**every fixture began from a pre-populated participant directory with nothing in `submitted`
— exactly the state all three defects hid behind.** That sentence is the most useful thing in
this document. A test suite that only ever starts from a healthy state cannot find the
defects that live in the unhealthy one.

## Blocking

### B1 — A new participant could not start. The first action of the pilot failed.

`start_attempt` read `participant/progress.yaml` before doing anything, and starting a quest
was the only documented way to create that file. `ProgressStore.initialise()` existed with
**zero callers**. The refusal was circular: *"No participant progress file exists yet. Start a
quest to create one."*

Every test passed because `tests/conftest.py` copied `fixtures/participant/`, which already
contained the file. Nothing exercised the empty-participant write path.

**Fixed.** `start_attempt` creates the file when it is absent, seeded from the site's own
configuration and the local account name. `tests/integration/test_first_run.py` starts from a
genuinely empty participant directory and drives the real service end to end.

### B2 — No state-changing control existed in the generated UI, and every page claimed the service was down.

`offline_service_view()` was a constant and `build_site` called it unconditionally, so a page
served **by the running service** still told the participant the service was not running, and
every `ActionView` was constructed with `enabled=False`. The generated site contained **zero
`<form>` elements**. Every participant action was reachable only by hand-crafting a JSON POST
with the run token, which is documented nowhere.

**Fixed.** `build_site` takes the service state. The service builds pages whose controls
work; the CLI builds pages that say plainly they cannot change anything. The forms are
ordinary HTML that post without JavaScript, and the run token is substituted into the HTML as
it is served — so it reaches a form without ever being written to disk, and the test asserting
that still holds.

### B3 — `/review/{quest-id}/` was never generated, so the reviewer queue linked to a 404.

`build_site` rendered the reviewer template once, at `/review/`, with `quest=None`,
`can_decide=False` and a stale `blocked_reason` reading *"Until Stage 7 lands the reviewer
workflow…"* — three stages after Stage 7 shipped. The queue linked to per-quest pages that
did not exist. `test_no_broken_internal_links` passed only because the shipped fixture has
nothing in `submitted` at build time.

**Fixed.** One reviewer page per attempt, with the ten sections U10 requires. There is now a
test that builds with an attempt in `submitted` and re-runs the link check.

## High

| ID | Finding | Resolution |
|---|---|---|
| H1 | The guides described behaviour the code did not have | True once B1–B3 were fixed; the reviewer guide's decision step is also now listed as needing the service |
| H2 | Five of fourteen traceability rows were false or weaker than the criterion | Four were fixed by writing the test that did not exist — `git_status` had none, `.gitignore` was only copied and never read, `recommend.py` was untested, and the quest-page row rested on one string |
| H3 | Evidence edited after approval kept `verified` silently | `progress._check_stale_approval` compares at load time and warns; four tests, including a tampered review hash |
| H4 | Stages 4–9 had no audit record | `docs/audits/stage-04-to-09-implementation-audits.md`, labelled in its first line as self-audit rather than independent review |

## Medium

| ID | Finding | Resolution |
|---|---|---|
| M1 | `make check` and CI ran none of the browser suite, and the fixture skipped rather than failed without Chromium | CI has a browser job; a missing browser is an error in CI |
| M2 | Release-note numbers were wrong | Corrected |
| M3 | Known limitations omitted B1–B3 | The list is accurate now that they are fixed; the reviewer-decision limitation is added |
| M4 | Deferred register drift | Open |
| M5 | `test_no_ui_file_was_touched` silently skipped `quest_app` | Open |
| M6 | The `locally_validated` guard lived in the service, so other callers bypassed it | Moved into `store.transition_attempt` as a guard argument |

## What the audit confirmed as sound

Recorded because it bounds the remaining work. Driving the real service end to end —
start, run a validator, mark evidence ready, record local validation, submit, needs-changes,
resume, resubmit, approve — **verified XP moved only on approval**. All reviewer guards fired.
Of **twelve** attempted routes to `verified` without a reviewer, eight were refused at load
time with precise messages and two behaved as documented; the two that succeeded are
ADR-030's stated social gap and H3, now closed. Schemas were only ever added to. `git log -p`
on the tests shows four removed assertions, all replaced by stricter ones — no test was
weakened to pass a stage. No secrets, no private evidence, no machine paths in generated
output.

## The lesson worth keeping

Every fixture in this project started from a healthy participant directory. Three blocking
defects lived in the states no fixture occupied: no participant at all, and an attempt
awaiting review. The corrective is not more tests of the happy path — it is fixtures that
start from nothing, and fixtures that start from every state the product defines.
