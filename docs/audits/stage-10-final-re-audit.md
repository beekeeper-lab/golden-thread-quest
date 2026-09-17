# Stage 10 — Final Release Re-audit

**Audited commit:** `128617e`
**Auditor:** independent review agent, fresh context, read-only, 128 tool calls
**Recommendation:** **`do-not-release`** — 1 blocking, 3 high, 9 medium, 4 low
**Status after fixes:** blocking and high closed; the mediums are closed or deferred with a
register entry.

The auditor confirmed B1, B2 and B3 from the first round were genuinely fixed, by driving
the real service from an empty participant directory through start, validate,
evidence-ready, locally-validated, submit, needs-changes, resume, resubmit and approve, and
checking every link at three different attempt states.

## Blocking

### R1 — A refused action produced no message, and the page showed the opposite

The service redirected with `?problem=<reason>` and nothing read it: `flash` was hard-coded
empty in the build and only the base template consumed it.

Reproduced: with a GitHub token in `PROOF.md`, `mark-evidence-ready` was refused — and the
page the participant landed on rendered the previous build's success panel, *"The scan found
nothing secret-like."* **A security control refused an action and the page then told the
participant the opposite.**

**Fixed.** The service renders the reason into the page as it serves it, in the same
substitution pass as the request token, so it works without JavaScript. The refusal path
rebuilds first, so the state beside the message is current. Tested end to end, including that
neither the message nor the evidence preview reproduces the value.

## High

### R2 — The per-validator environment allowlist did not work in either direction

The environment was set around `process.start()`, and `forkserver` captures its helper's
environment at first use. Executed: a validator with an empty allowlist received
`JIRA_BASE_URL`; the one that declared it received `<ABSENT>`. In a running service the order
is whatever the participant clicks first.

**Fixed** by replacing `multiprocessing` with `subprocess`, which takes `env=` and makes the
environment per-run by construction — and which also removes the low finding that
`forkserver` re-imports the parent's `__main__`. A probe validator now reports what the child
actually sees, so the control is verified from inside rather than inferred from registry
strings.

Surfacing the reason for an environment failure (R11) paid for itself within a minute: it
turned a silent empty result into `the validator raised PermissionError`, which was the child
calling `setsid()` after `start_new_session` had already made it a session leader.

### R3 — The traceability document still overstated coverage

The `git_status` row still pointed at a test for a different module, and several rows were
weaker than the criterion. Underneath it, `ACCEPTANCE-CRITERIA.md` had **no criterion IDs and
no ticked boxes**, so rows matched criteria by prose only — which is exactly why the drift was
invisible.

**Fixed.** Every criterion has a stable ID, 47 of 48 are ticked, and the one that is not is
named. Two recommendation tests that could pass vacuously were rewritten: one was wrapped in
an `if` that could skip its own assertion, and the tie-breaking test never constructed a tie.

### R4 — Any filesystem error closed the connection with no response

A read-only participant directory produced `curl: Empty reply from server` and a traceback
with absolute paths on stderr. **Fixed**: a real response naming the operation, never the
path, with a test that makes the directory read-only.

## Medium

| ID | Finding | Resolution |
|---|---|---|
| R5 | An approval whose `quest_version` disagreed with the attempt was accepted, conferring verified XP for a version nobody attempted | Fixed and tested |
| R6 | The transition guard defaulted to `None`, so the invariant its docstring claimed did not exist | Required now, with a named `no_guard`; a test asserts it has no default |
| R7 | The stale-approval warning never reached a page | Open — deferred (D12 neighbours it); the warning reaches the CLI and the reviewer page |
| R8 | One deleted evidence directory makes the whole site unbuildable | Deferred as D12 |
| R9 | The reviewer guide never mentioned the service; the participant guide claimed commands were printed that were not | Both rewritten |
| R10 | A service-built site left on disk shows enabled forms that do nothing | Open — inherent to a generated site that records service state; the token placeholder makes them refuse rather than misfire |
| R11 | `environment_failure` threw away its reason | Fixed |
| R12 | Register and document drift | Fixed: counts, `final-audit.md`, Stage 2 boxes, `PLANNING-STATUS.md`, five new register entries |
| R13 | A corrupt participant file is reported as a curriculum problem | Open, Low in effect — the message is wrong, the refusal is right |

## Low

R14 dead string removed. R15 the service no longer prints the token — the pages it serves
already carry it, and printing it put it into any log the participant redirected into.
R16 secret-scanner gaps deferred as D10. R17 the local account name as `display_name` is
recorded in the participant guide as theirs to change.

## What the auditor confirmed

**Fourteen routes to `verified` without a reviewer; ten refused with precise messages**,
including four the previous round had not tried: a second attempt sharing another's evidence
directory and review, a copied `review.yaml`, an approval present only as an archive, and a
`verified` state over a `rejected` review. The two that succeed are ADR-030's documented
social gap. **No writes outside `participant/` were found** across thirteen traversal probes,
six static-handler shapes and a cross-origin POST. No absolute paths or secrets in generated
output. The validator timeout killed a `sleep 300` grandchild with the group.
