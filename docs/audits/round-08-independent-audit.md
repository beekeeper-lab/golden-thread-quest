# Release Audit — Round 8

Status: **complete.** Twenty-six findings returned, twenty-five accepted after verification
here and one rejected. Every accepted finding is fixed, and every code fix carries a test that
fails without it.

Commit under audit: `b0667c0` on `main`, the merge of `chore/round-07-audit`. The tree here is
what a clone of `main` now gets.
Range of newest work: `31a74cb..b0667c0`.
Predecessor: `docs/audits/round-07-independent-audit.md`.

## Why this round exists

`docs/ACCEPTANCE-CRITERIA.md` leaves **DH7** open. Seven rounds have run and each one found
something. The criterion closes on a round that reports no unresolved blocking or high
findings, which is a round that finds nothing, not a round whose findings are all fixed.

## Method

Three lenses, each given the repository paths and the commit range and nothing else: no summary
of what the author believed, no sight of each other's findings, and no access to
`docs/audits/`, which would have told them what earlier rounds concluded.

| Lens | Scope |
|---|---|
| Curriculum | The eight quests as curriculum, regions, badges, tracks, the participant journey walked end to end, the validator fixtures, and the accessibility of what is actually rendered |
| Engine | Code correctness, concurrency, the state model, the local service, the validator subsystem, and the architecture rules in `CLAUDE.md` |
| Documentation | Traceability, acceptance criteria, ADR accuracy, cross-document consistency, and clean-clone reproducibility from the remote at this branch's head |

Round 7 named two themes to carry forward: a mechanism correct in the case it was written for
and one step short everywhere else, and a check that cannot see what it is judging. The lenses
are pointed at the four request-path mechanisms round 7 added, the rebuild advisory now carried
into the page, `Workspace.attempt_files` and the three validators, and the modules no lens has
reached — `view_models`, `recommend`, `markdown_structure`, `update`, `migrations` — plus the
accessibility the browser tests do not assert.

Every finding requires file:line or a command and its output. A claimed defect that could not be
triggered is recorded as unverified rather than as a finding. Findings returned by a lens are
re-verified here before they are accepted; a lens is a source, not a verdict.

## Lens findings

Severities below are the ones this pass assigned, which are not always the ones the lens
proposed. Where they differ the reason is in the verification column.

### Curriculum

| # | Finding | Severity | Verification | Disposition |
|---|---|---|---|---|
| C1 | `validators/repository_foundation.py` judged a participant's ignore rules by reading the whole `.gitignore` as one lowercased string, comments included. A file containing no rule at all — only a note to the reader mentioning generated output, local data, `.env` and credentials — passed all four categories. This is the only automated check behind AC3 of the first quest, which every other quest depends on. | High | Reproduced: a comments-only file returns `missing: []` | **Fixed.** The check now reads the lines that actually ignore something: blanks, comments and negations are not coverage, and a file with none of them fails as "no ignore rules were found". |
| C2 | `content/quests/context-library/canonical-work-item.md` declares only `jira-read-assigned-stories` as a prerequisite while its own criterion 9 needs a second system, so the page says "Prerequisites are satisfied" for a participant who cannot yet satisfy the quest. | claimed High | Confirmed as described, and rejected as a defect: the quest's Scenario says so in the participant's own words at the point of use — "finish either *Read a Trello board* or *Read your assigned GitHub Issues* before you claim this quest. Only the Jira quest is a hard prerequisite, because either of the other two satisfies the second system" — and both alternatives are in `related_quests`. Either one satisfies criterion 9, and the content model has no disjunctive prerequisite; making either quest a hard prerequisite would be wrong | **Rejected.** Recorded rather than fixed. |
| C3 | `validators/playwright_quality.py` flagged a selector as brittle only when a tag name was followed by a combinator, or a class or id was followed by `>`. A plain class or id locator — `page.locator(".btn-primary")`, the commonest form of the coupling the check exists to catch — was invisible to it, and a test built entirely on them passed outright if it contained a single accessible query anywhere. | High | Reproduced: `.btn-primary`, `#submit`, `.card .title` and `div` all returned no match | **Fixed.** A class or id selector is matched on its own and a structural tag whether or not anything follows; attribute and engine-prefixed selectors (`[data-testid=…]`, `text=…`) are left alone. |
| C4 | `jira_read_assigned._check_disappearances_reported` recognised only four top-level field names as a report of a vanished story, a vocabulary the quest content never states. | High | The lens's finding holds, and verifying it found the worse half: a story counted as "reported" merely by appearing in the participant's list. A synchronization that never noticed GTQ-100 had gone away, and listed it unchanged as `In Progress`, produced `('disappearances-reported', 'pass', 'Every story that disappeared between runs is still reported.')` — a false pass on the criterion the fixture exists for | **Fixed.** A record kept in the list counts only if it says the item is no longer assigned — a false `assigned` flag, a removal field, or a status or note naming the removal — and the refusal names every accepted form, so the vocabulary is knowable from the failure. |
| C5 | `templates/pages/review.html.j2` gave the review queue and the automated-validation results the same `aria-label="Table"` on their scroll regions. Two landmarks with one name on one page are two things a screen-reader user cannot tell apart. | Low | Confirmed at `templates/pages/review.html.j2:21,116` | **Fixed**, with a test that fails any page repeating a region label or naming one after its markup. |

### Engine

| # | Finding | Severity | Verification | Disposition |
|---|---|---|---|---|
| E1 | The C21 confirmation was consulted in the HTML form handler and nowhere else. `POST /api/action` and `quest-app action` went from the action allowlist straight to `ActionRunner.perform`, which never looked at it — the rule ADR-033's round-7 amendment says now lives in the layer both callers go through. | High | Reproduced on both surfaces: `perform('start-quest', …)` with no confirmation returned `{'ok': True, …, 'state': 'in_progress'}`, and a JSON POST with no `confirm` anywhere returned HTTP 200 | **Fixed.** The gate is in `ActionRunner.perform`. The form still refuses first so the message lands on the page the participant came from; the CLI takes `--confirm`; a JSON client sends `"confirm": true`. |
| E2 | `record-review` was not in `CONFIRMATIONS` at all. It is the one action that produces verified completion and verified XP, and the only thing in front of it was a `window.confirm` in the page's script: with scripting off the form posted an approval unguarded. The test written to catch exactly this passed twice over — its assertion was satisfied by an unrelated checkbox and a `required` on the reviewer's name, and no fixture build renders the decision form, so it never saw it. | High | Reproduced: the form carries `data-confirm` and no `name="confirm"` input; a POST with a decision, a statement and a token and no confirmation returned 303 and left the attempt `verified` with 30 verified XP | **Fixed.** `record-review` carries a confirmation, the page renders it as a required checkbox from the same definition the service enforces, and the test now looks for the confirmation by name. The templates are checked directly as well, so a form no fixture renders is still covered. |
| E3 | `do_GET` and `_serve_static` had no error handling. Both write handlers have had a catch-all since round 7; the read path had none, so an unreadable page or a reader clicking away mid-response closed the connection with no status and no body and put a traceback carrying absolute paths on the participant's terminal. | High | Reproduced both: a mode-000 page produced no bytes at all and a `PermissionError` traceback; a client disconnecting mid-response produced `ConnectionResetError` | **Fixed.** The read path answers its own failures, or closes quietly when there is nobody left to answer. |
| E4 | `_body_is_absent` read `Content-Length` with `get`, which returns the first of them. Sending `0` and then a real length made a GET look bodyless while the body stayed in the socket, to be read as the next request on a kept-alive connection with every header chosen by the sender. | Medium | Reproduced: a single length gave 400, `0` then `45` gave 200 and the smuggled request was answered — two responses in the stream | **Fixed.** More than one declared length is refused. Not browser-reachable — `Content-Length` is a forbidden header for `fetch` and XHR — so the exposure was to local socket clients. |
| E5 | `::1` is accepted by `assert_loopback`, offered by `--host`, named in `.env.example` and printed on start, and the `Host` and `Origin` checks split the authority on the last colon, which `[::1]:PORT` does not survive. | Medium | Confirmed, and worse than reported: the service binds `ThreadingHTTPServer`, which is AF_INET, so `--host ::1` never bound at all — `gaierror [Errno -9] Address family for hostname not supported` | **Fixed.** An IPv6 literal binds an IPv6 socket, the host and origin checks unbracket it, and the printed address is a usable URL. A test binds `::1` and asks for a page under the name a browser sends. |
| E6 | `_redirect_back` built `Location` from the Referer's path with no check, so a path beginning `//` produced a protocol-relative URL and sent the browser off this machine carrying the refusal text, which quotes values the participant supplied. The origin check does not catch it: it compares the Referer's origin and never its path. | Medium | Reproduced: `Location: //evil.example/x?problem=That%20quest%20does%20not%20exist.` | **Fixed.** A location that is not a single-slash path is replaced with `/`. |
| E7 | `working_directory` is required by the registry schema, set to `participant` on all five entries and published in the validator contract and the authoring guide — and nothing applied it. The child was launched in the repository root, so a validator resolving a relative path as the contract describes read the wrong tree. | Medium | Confirmed: the resolver at `validator_registry.py:124` had exactly one reference, its own definition | **Fixed.** The child starts in the declared directory, with the repository named on `PYTHONPATH` so the import that used to depend on the current directory still works. The environment probe now reports where it started, so the constraint is asserted from inside the child rather than assumed. |
| E8 | `update.preflight` built the backup-branch name twice from the clock, so a preflight straddling a second boundary reported one branch in `backup_branch` and told the participant to create another in `instructions`. | Low | Confirmed at `update.py:164-165` | **Fixed**, with a test that forces a different name per call rather than waiting for the second boundary. |
| E9 | The publish is two renames, and between them a request for any page was answered "No such page. Run a build if you expected one." The service rebuilds after every action while it is still serving. | Low | The lens measured one 404 in 3 079 requests across twelve rebuilds | **Fixed.** A request that arrives mid-publish waits out the swap, bounded, and only while one is in flight. |

### Documentation

| # | Finding | Severity | Verification | Disposition |
|---|---|---|---|---|
| D1 | `docs/SECURITY-AND-PRIVACY.md` describes five controls around external-system writes — preview, duplicate and permission checks, explicit confirmation, a result record, idempotency — and a required security test for an external write without them. None of it exists, and nothing marks it as deferred. | High | Confirmed: every quest declares `external_write: false`, every registry entry is `network: denied`, and the application makes no outbound request | **Fixed** by saying so: the section now states that release one performs no external write and that its requirements are conditions on a quest that does not exist yet. The invariant is asserted in `tests/test_release_facts.py`, so the day a quest declares a write, the failing test says those controls have to be built. The quest page's default risk notice promised the same absent mechanism and now says what is true: the write is the participant's to make. |
| D2 | "Screenshots require a redaction confirmation" has no gate anywhere. | Medium | Confirmed: the only confirmations are the action ones, plus a comment in the generated `PROOF.md` | **Fixed.** The document now says what is true — the scanner reads text, a token in a picture is invisible to it, and the `PROOF.md` "Sensitive values" section asks the participant to confirm — and it is listed as a limitation. |
| D3 | `docs/IMPLEMENTATION-DETAILS.md`'s file map lists every `quest_app` module individually and omits `secret_patterns.py`, the module behind every scan and redaction in the document's own safety section. | Medium | Confirmed against `ls quest_app/*.py`: it and `__init__.py` are the only two absent. The lens proposed High; a missing row in a map whose neighbours are accurate misleads a reader about one module, which is the Medium band | **Fixed.** |
| D4 | The same map summarises `validators/` as "three sample validators", omitting the two registered environment probes and the unregistered slow probe. | Medium | Confirmed against `validators/registry.yaml` | **Fixed.** |
| D5 | `docs/RELEASE-NOTES.md` says "3, plus a probe"; `README.md` says "3 quest-facing, plus 2 registered probes and one unregistered slow probe". Two documents, one registry. | Medium | Confirmed | **Fixed**, by making the release notes say what the README says. |
| D6 | `make update-check` fails on a literal clean clone — "No 'upstream' remote is configured" — and no document tells a reader to add that remote. `docs/guides/UPDATING.md` uses `upstream` in every command as though it already exists. | Medium | Reproduced by two independent clean-clone runs, and again here | **Fixed.** The guide now names the remote and the command that creates it, and says that the refusal is the check working. The command itself already prints the fix. |
| D7 | `docs/DECISIONS.md` ADR-016 still says a bullet list under the acceptance-criteria heading is a build error. ADR-026 supersedes that and the code agrees with ADR-026. ADR-019 and ADR-038 carry inline amendment notes; ADR-016 does not, so a reader who opens it alone gets the wrong behaviour. | Medium | Confirmed against `content_loader.py:474-481` | **Fixed.** |
| D8 | `docs/TRACEABILITY.md` says a row with no test is "marked **no test**". No row uses that notation; the four untested rows use `—`. | Low | Confirmed | **Fixed**, by saying what the table does. |
| D9 | `VALIDATION-REPORT.md` says eight JSON Schemas; there are ten. | Low | Confirmed. It is a dated planning artifact and the current documents are right, so the risk is low | **Fixed** by marking it as preserved from its validation date, with the current number named. |
| D10 | `docs/TRACEABILITY.md` cites `test_invalid_content.py` as 20 rules; it holds 25. | Low | Confirmed | **Fixed.** |
| D11 | The test behind PE8 asserted only that "Claimed XP" and "Verified XP" both appear somewhere on the passport, which says nothing about either number. | Low | Confirmed at `tests/integration/test_build.py:179-183` | **Fixed.** It now reads both values — 50 claimed against 20 verified for the fixture participant — and refuses a page that shows one combined total. |
| D12 | The known-limitations lists in `docs/IMPLEMENTATION-DETAILS.md` and `docs/RELEASE-NOTES.md` do not correspond. | Low | Confirmed: seven items against eight | **Fixed.** The release notes are named as the full list and the implementation document says it is the same set seen from the implementation side. |

### Found while running the gates

The review lenses work in Git worktrees checked out inside the repository, and `ruff check .`
read one of them. Nothing in the repository ignored `.claude/worktrees/`, so a tool's scratch
checkout could be linted, scanned or committed. It is ignored now. Not a product defect, but
it is the second round in which the way the round itself is run turned out to matter.

## Gates

| Gate | Result |
|---|---|
| `make check` | pass — 624 passed, 42 deselected |
| `make test-ui` | pass — 42 passed |
| `make validate-content` | pass — 8 quests, 8 regions, 4 badges, 1 track, 0 warnings |
| `make verify-package` | pass — the exported archive installs, validates and builds on its own |
| Clean clone from `origin` at this branch's head | pass — `git clone --branch chore/round-08-audit`, then `make setup`, `make check` (622 passed, 3 skipped), `make validate-content`, `make build` (53 pages) and `make verify-package`. The gate round 7 recorded as not run |
| Clean clone at the commit under audit | pass, run by the documentation lens before any fix landed |
| CI at this branch's head | pass — `check` on 3.10, 3.12 and 3.13, `browser`, and `clean-export`, all green |
| Each fix reverted one at a time | every code fix is caught by a test. The three validator fixes, the confirmation gate on both surfaces, the four request-path mechanisms, the validator working directory, the preflight name, the publish window and both template fixes were each reverted to `b0667c0` and the test that covers them failed |

The suite grew from 598 to 624. `make test-ui` is unchanged at 42.

The two counts differ by two because the clean clone reports a run — 622 passed and 3 skipped,
625 — while `make check` here reports 624 collected minus what this machine deselects. The
README already says a run can read higher or lower than the collected number, and
`tests/test_release_facts.py` asserts the collected one.

## Verdict

**Round 8 does not close DH7.** Twenty-six findings returned: none blocking, seven high, ten
medium, eight low, and one rejected after verification. Every accepted finding is fixed, and
every code fix has a test that fails without it.

The round has one theme, and it is the one round 7 named in a different form: **a rule
enforced on whichever surface happened to have a control for it.** The confirmation was a
checkbox in a form, so it was checked in the form handler — and the JSON endpoint and the CLI
performed the same actions with nothing saying the caller meant them. The reviewer's approval,
the single action that produces verified completion and verified XP, was not in the list at
all: in front of it stood a `window.confirm` in a script, which is not a rule, and a test that
believed it was because an unrelated checkbox satisfied the string it searched for.

The same shape is in the rest. Both write handlers answered their own failures and the read
path answered none. The GET-body refusal read one `Content-Length` and a second one walked
past it. `working_directory` was required by a schema, set on every entry, published in a
contract, and applied by nothing. And a validator's check for a disappeared story accepted the
story's mere presence as the report of its disappearance — a check standing where a check
should be, looking at the wrong thing.

Round 9 should run against the merge commit, with the same three lenses and the same rule that
a lens is a source rather than a verdict. Point it at:

- the action layer's new confirmation gate, since it now sits in front of every mutating call
  and a mistake there is a mistake everywhere, and at what a JSON or CLI caller can still do
  that a browser cannot;
- the read path's new catch-all, the publish wait and the IPv6 socket, all added here and all
  on the path of every request;
- `build.py` and `content_loader.py`, which no lens has read end to end in any round;
- the reviewer's flow driven for real — a submitted attempt, the service running, the decision
  form rendered — which no fixture build produces and which is therefore the least exercised
  screen in the application;
- `tools/`, `scripts/` and the Makefile, which nothing has audited;
- and the tests themselves: E2 was a test that passed on the defect it was written for, and
  round 8 found two more of those. A test that cannot fail is the same defect as a check that
  cannot see.
