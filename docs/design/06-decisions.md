# Part 6. Key decisions

`docs/DECISIONS.md` is the full log: forty-one architecture decision records (**ADRs**),
appended rather than rewritten, several amended after an audit found the code and the
decision disagreeing. This part groups them by the question each one answers and gives the
reason in one or two sentences. Read the log for the evidence behind each.

## 6.1 Product shape

| ADR | Decision | Why |
|---|---|---|
| 001 | The quest is its own repository | Participants fork, run and update it independently of any other program |
| 002 | Participants fork the canonical repository | A fork keeps upstream history, so curriculum updates arrive by merge |
| 003 | Three ownership zones in separate top-level folders | Updates cannot overwrite participant work; generated output stays disposable |
| 010 | A restrained field-guide visual direction | Motivation without looking childish in an enterprise setting |
| 011 | Only a reviewer decision produces verified progress | Automated checks establish facts, not the quality or meaning of the work |
| 013 | Repository evidence is primary; screenshots support | Files, tests and logs are reproducible and diffable |

## 6.2 Content and contracts

| ADR | Decision | Why |
|---|---|---|
| 004 | Markdown with YAML front matter for quests, YAML for structured content | Readable diffs and approachable authoring |
| 005 | JSON Schema is the public contract | Language-neutral, testable, editor-friendly |
| 012 | Stable IDs; attempts record quest version and content hash | Titles and filenames change; version-aware attempts survive curriculum edits |
| 016, 026 | Acceptance criteria are parsed from the body with positional IDs `ac-<n>`; a bullet list is a warning, an empty item or split list an error | One copy of the criteria; the failures that actually move an ID are the ones that stop the build |
| 020 | `jsonschema` against the published schemas, frozen dataclasses inside | No second rule set that can drift from the schema a maintainer reads |
| 021 | `markdown-it-py` with raw HTML off, then `nh3` sanitization | The guarantee does not depend on the renderer's escaping |
| 025, 029 | YAML through a strict safe loader: no custom constructors, no duplicate keys, bounded nesting | `xp: 10` then `xp: 90` must not mean one thing in review and another at build |
| 027 | Markdown structure from the token stream, never from lines | Line regexes turned code blocks and nested items into criteria |
| 028 | A content-hash mismatch is a warning, never fatal | A typo fix must not revoke approved work, but the reader must be told |

## 6.3 Generation and runtime

| ADR | Decision | Why |
|---|---|---|
| 006 | Python and Jinja2 generate the site deterministically | Server-rendered HTML is inspectable and needs no frontend build |
| 007 | No frontend framework | A framework would duplicate state the Python model already holds |
| 008 | Static generation plus a loopback service for the few mutating actions | Static pages cannot write files; a full web app is unnecessary |
| 009 | Mermaid documents; HTML and CSS define the UI | Diagrams describe relationships, not layout or accessibility |
| 015 | Generated output is not canonical | A build can always recreate it |
| 022 | The service uses the standard library `http.server` | Every requirement is a restriction; a framework hides the surface they apply to |
| 019 | Python 3.10 or newer (amended from 3.12) | The sandbox a participant may be given ships 3.10 |
| 023, 024 | pytest, Playwright, axe-core; ruff and `mypy --strict` | One toolchain locally and in CI |
| 037 | The service records each bound port under `local-data/service-ports/` | A CLI action must know whether a service is running to build live or offline pages |
| 040 | The build honours `SOURCE_DATE_EPOCH` | Makes "two builds are byte-identical" true on demand |

## 6.4 Safety and integrity

| ADR | Decision | Why |
|---|---|---|
| 014 | Only registered validators and named actions run | Arbitrary command execution on localhost is an avoidable boundary failure |
| 017 | A validation run never changes attempt state; `locally_validated` is requested and guarded | A validator must not be an authority over participant state |
| 018 | Participant paths keep the `participant/` prefix; the root is configuration | Tests use fixtures without touching live work; the contract does not move |
| 030 | Reviewer provenance is conventional, and said so | A half-built signature scheme invites trust it has not earned |
| 031 | The evidence hash covers the work, not the records; proof files outside the package are digested too | The application's bookkeeping must not read as a change to the work |
| 032 | The application never pushes, opens a pull request or merges | Those are claims the participant makes, not the tool |
| 033 | Every rule the browser shows is enforced in the action layer | A second caller turned a greyed-out button into a hole |
| 039 | A validator judges the attempt it was given | Records connect by ID, never by modification time |
| 041 | The service answers only to a loopback name, and every request gets a response | Defeats DNS rebinding; no traceback, no silent drop |

## 6.5 Concurrency and failure

| ADR | Decision | Why |
|---|---|---|
| 034 | One mutation at a time across processes: a file lock around load, decide and write | The CLI and the service could interleave a read-modify-write |
| 035 | One build at a time per output directory | Two builds shared one staging directory and published partial sites |
| 036 | Not being able to lock is never a reason to refuse the work | The atomic rename keeps files whole; refusing to record work is worse |
| 038 | A failed rebuild after an action is an advisory, not a failed action | The participant's record cannot be regenerated; the site can |

## 6.6 Patterns across the decisions

Three patterns recur and explain most of the code's shape:

1. **One place per rule.** Confirmations live in `state_machine.CONFIRMATIONS`, guards in
   `actions.py`, secret patterns in `secret_patterns.py`, schemas in `schemas/`. A second copy
   is a second thing to drift, and audits repeatedly found drift where a rule had two homes.
2. **Re-derive, never believe.** Anything a participant is not allowed to decide is computed
   from records on every load rather than read from their file.
3. **Degrade toward the participant's record.** When something non-essential fails (a lock,
   a rebuild, an activity line), the participant's work is kept and the failure is reported,
   never the other way round.
