# Implementation Details

What was actually built, as opposed to what was planned. `docs/ARCHITECTURE.md` describes the
intended shape; where the implementation diverges, this file says so and points at the
decision that authorized it.

## Shape

```text
quest_app/           the application
├── config.py            roots, versions, participant-path resolution (ADR-018)
├── errors.py            the one problem shape every layer reports
├── yaml_loader.py       SafeLoader plus duplicate-key and deep-nesting refusal (ADR-029)
├── hashing.py           quest, mapping and directory hashes
├── markdown_render.py   CommonMark → sanitized HTML (ADR-021)
├── markdown_structure.py quest body structure from the token stream (ADR-027)
├── content_loader.py    discovery, parsing, schema validation, normalization
├── models.py            frozen content models and the state vocabulary
├── semantics.py         cross-document rules
├── progress.py          participant records, read but never believed
├── pipeline.py          load content, then state, then cross-check
├── progress_calc.py     derived states, totals, badges
├── recommend.py         deterministic weighted recommendation
├── view_models.py       display-ready models, one per screen
├── routes.py            every URL, derived from stable IDs
├── build.py             rendering, indexes, manifest, atomic swap
├── state_machine.py     the transitions a participant may make
├── store.py             atomic writes to participant-owned files
├── evidence.py          proof detection, secret scanning, evidence hashing
├── secret_patterns.py   the patterns behind every scan and every redaction
├── review.py            submissions and reviewer decisions
├── validator_registry.py the complete set of programs that may run
├── validator_runner.py  running one, under every registered constraint
├── validator_child.py   the subprocess a validator runs in, and nothing else
├── git_status.py        read-only repository inspection
├── update.py            upstream preflight; runs no merge
├── migrations.py        participant-state migrations
├── serve.py             the loopback action service
├── actions.py           the one action allowlist, shared by the service and the CLI
├── compat.py            the shims that keep the Python 3.10 floor honest (ADR-019, amended)
└── cli.py               validate, build, serve, action, update

validators/          registry.yaml, three quest-facing validators, two registered
                     environment probes, one unregistered slow probe used only by the
                     timeout test, and the Jira fixtures
templates/           layouts, ten component macros, thirteen page templates
assets/              design tokens, application stylesheet, enhancement script
tools/               secret scan, YAML-safety check, cleanup
```

## What each stage produced

| Stage | Built | Audit |
|---|---|---|
| 0 | Planning audit, ADR-016 to ADR-025 | pass-with-advisories |
| 1 | Package, toolchain, CI, safety tools | fail → fixed → pass-with-advisories |
| 2 | Content contracts, loading, semantics | fail → fixed → pass with one open item → fixed |
| 3 | Eleven screens, build pipeline, indexes | fail → fixed → re-audit |
| 4 | Loopback service, state machine, atomic writes | — |
| 5 | Validator registry, sandboxed runner, evidence | — |
| 6 | Structural and browser accessibility tests | — |
| 7 | Submissions, reviewer integrity | — |
| 8 | Update preflight, migrations | — |

## Decisions that shaped the code

The full log is `docs/DECISIONS.md`. Four are worth restating because they explain why the
code looks the way it does.

**ADR-020 — schemas validate, dataclasses carry.** `jsonschema` runs against the files in
`schemas/`, and validated documents become frozen dataclasses. There is no second model
layer restating the same rules, so the file a maintainer reads is the file that validates
their work.

**ADR-022 — the service is standard library.** Every requirement on the local service is a
*restriction*. A framework would have added dependencies and abstracted the exact request
surface those restrictions apply to.

**ADR-027 — Markdown structure comes from the token stream.** Line regexes made a nested
sub-detail into a top-level criterion and a fenced code block into criteria. The parser
already knows the difference, and asking it is the only way the loader and the renderer can
agree about what `ac-3` means.

**ADR-011 and ADR-017 together — authority is never blurred.** No transition a participant
can make produces `verified`. Running a validator is not a transition at all. The one place
`verified` is written is the consequence of an approval that was validated immediately
before.

## How the safety properties are actually obtained

Each of these is a claim the product makes. This is the mechanism, so a reviewer can check
the mechanism rather than the claim.

**No arbitrary command execution.** A validator is a Python callable named in
`validators/registry.yaml`, imported by an exact allowlisted module path. There is no
argument string anywhere in the path from a request to a running validator, so there is
nothing for a shell metacharacter to escape from. Parameters are typed and allowlisted, and
there is deliberately no string parameter type.

**No arbitrary filesystem access.** A validator receives a `Workspace` whose read and write
methods canonicalise a path and then re-check containment, *after* symbolic links are
followed. The service resolves static paths the same way. Participant paths keep the
contract prefix and follow a configured root (ADR-018).

**No credential reaches a validator by accident.** The child environment is constructed from
the registry's allowlist plus a minimal `PATH` and the repository's own import path.
`os.environ` is not inherited, and the child starts in the `working_directory` its registry
entry declares.

**A stopped validator is stopped.** The run happens in a child process in its own process
group, and a timeout kills the group. `validators/slow_probe.py` spawns a child of its own so
the test proves it.

**Verified means a reviewer said so.** Loading re-derives `verified` from the review record
and refuses six distinct forms of claim without one. Recording the decision that produces it
is itself confirmed: `record-review` is in `state_machine.CONFIRMATIONS`, the page renders
that text as a required checkbox, and `ActionRunner.perform` refuses the action without it —
so the browser, the JSON endpoint and `quest-app action --confirm` all meet the same gate.

**Participant files survive.** `tools/clean.py` removes an exact allowlist and refuses
anything reached through a symlink. The update helper runs no merge. Every participant write
is atomic, validated before it lands, and recorded in `participant/ACTIVITY.md`.

## Divergences from the plan

| Area | Plan | Built | Why |
|---|---|---|---|
| Acceptance criteria | Error on an unnumbered list | Warning; empty item and split list are errors | ADR-026 — the shipped content uses bullets, and the failures that actually break the ID promise are the other two |
| Content-hash mismatch | (Implied error) | Warning, with distinct wording for a verified attempt | ADR-028 — `CONTENT-MODEL.md` keeps verified attempts verified, and the hash covers editorial fields |
| Reviewer identity | — | Display name and Git history, not signatures | ADR-030 — a half-implemented signature invites trust it has not earned |
| Catalog filtering without JavaScript | "Works by reloading with a query string" | Region and tag pages are the scripting-free routes; live filtering is an enhancement | A static page cannot filter itself; the honest routes are real pages |
| Environment Health | Live checks | Build-time facts, labeled as such | Deferred (D7) — a generated page cannot inspect the machine when it is read |
| Badge awards | Reviewer-awarded badges | Always "pending" | Release one has no badge-award record; granting one by arithmetic would be the blurring ADR-011 forbids |

## Test layers

| Layer | Where | Count |
|---|---|---|
| Unit | `tests/unit` | detectors, template genericity |
| Contract | `tests/contract` | schemas, loading, sanitization, format validation |
| Semantic | `tests/semantic` | every rejection rule, progress integrity |
| Integration | `tests/integration` | CLI, build, transitions, evidence, updates |
| Security | `tests/security` | cleanup, secret scan, service, validator sandbox, review integrity |
| UI | `tests/ui` | generated-HTML structure, and browser-driven flows |

`make check` runs everything except the browser layer; `make test-ui` runs that.

## Known limitations

`docs/RELEASE-NOTES.md` carries the full list for a reader deciding whether to run
this. These are the same limitations seen from the implementation side.

1. Reviewer provenance is conventional, not cryptographic (ADR-030).
2. Environment Health reports build-time facts, not live ones (D7).
3. Reviewer-awarded badges cannot yet be awarded (no badge-award record type).
4. Validator isolation is policy plus process boundaries, not a container or seccomp. The
   architecture permits adding one without changing quest content.
5. Coverage reporting is not configured (D2).
6. There is no glossary content type (D1).
7. Two builds of the same content are byte-identical only when `SOURCE_DATE_EPOCH` is
   set; otherwise every page footer carries the time it was built.
