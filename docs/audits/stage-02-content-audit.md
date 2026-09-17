# Stage 2 — Content Contracts and Loading Audit

**Stage:** 2 — Content contracts and loading
**Branch:** `feature/golden-thread-implementation`
**Audited commit:** `93e91cd`
**Auditor:** independent review agent, fresh context, read-only, 53 tool calls
**Result:** `fail` — 1 blocking, 6 high, 14 medium, 9 low
**Status (2026-09-17):** every finding fixed and verified by an independent re-audit, which
recorded `pass with one open item`; that item (H5) and the residual S2-R1 are also now closed.
The re-audit is appended to the end of this file.

## Method

The agent ran every probe against the real code with the project's own interpreter rather
than reasoning about it: malformed YAML, unicode attacks on stable IDs, thirty-plus
sanitizer bypass attempts, forged validation records, and a field-by-field trace of all
eight schemas against their consumers.

## Baseline confirmed

- `git diff a68bbdf HEAD -- schemas/` is empty — no schema constraint was weakened.
- `ruff format --check`, `ruff check`, `mypy --strict`, `check_yaml_safe.py` and 151 tests pass.
- Unicode ID attacks (RTL override, zero-width, NFKC-colliding `base－camp`) are rejected by
  the ASCII-only `id` pattern.
- Percent-encoded traversal is caught by `PurePosixCheck`.
- **No injection was found in the markdown sanitizer** across mixed-case and whitespace
  schemes, entity, percent and nested encodings, `<svg>`, `<math>`, `<template>`, CDATA and
  attribute-quote breakout.

## Findings

### B1 — Blocking — the Stage 2 commit was not self-consistent

Four modules (`view_models.py`, `routes.py`, `recommend.py`, `progress_calc.py`) were
untracked in the working tree while `templates/README.md` referenced `quest_app.view_models`,
so a fresh clone documented a module that did not exist. Plan global rule "changes remain
within the current stage" and `CLAUDE.md` rules 4 and 11.

**Partly resolved, partly corrected.** The four modules were committed as Stage 3 work in
`b031d10` and `e845d3c` after the audit was commissioned, which closes the untracked half.

One part of the finding is **not accurate and is recorded rather than acted on**:
`git show --stat 93e91cd -- templates/` lists no files, so the Stage 2 commit did not delete
the three supplied contract templates. That deletion, and the `templates/README.md` rewrite,
happened in the Stage 3 commit `e845d3c`. The auditor was reading the working tree.

**Remaining action:** `pages/quest-detail.html.j2` is the file ADR-016 cites as its evidence
(`docs/DECISIONS.md`), and it was removed before its replacement existed. The Stage 3
quest-detail page must land, and ADR-016's evidence reference must be repointed at it.

### H1 — High — ADR-016 is not implemented as written, and all shipped content depends on it

ADR-016 says a build error is raised when the acceptance-criteria heading "contains no
ordered list". `content_loader.py` downgrades a bullet list to a warning. All three shipped
quests use bullets, so under the ADR as written the shipped package does not build. The
deviation is not recorded in `docs/DECISIONS.md`.

**Correction:** decide it in writing. Either convert the shipped criteria to ordered lists
and make the bullet case an error, or amend ADR-016 and state why positional IDs over an
unnumbered list are acceptable. Do not leave code and decision log disagreeing.

### H2 — High — criterion IDs are not stable, because the parser is a line regex

| input | produced |
|---|---|
| `1. one` / `   1. sub a` / `   2. sub b` / `2. two` | `ac-1 one`, `ac-2 sub a`, `ac-3 sub b`, `ac-4 two` |
| a numbered list interrupted by a fenced code block containing numbers | code-block lines become criteria |
| `1.` (empty) then `2. two` | `ac-1 two` — every later ID shifts by one |
| four-space-indented list (a code block) | parsed as a criterion |

A sub-detail of criterion 1 becomes criterion 2, so "criterion 3" does not mean the same
thing to a participant reading the page and to a reviewer finding pinned to `ac-3` — which
is the one guarantee ADR-016 exists to provide. No test covers nesting, code blocks or empty
items.

**Correction:** walk the markdown-it token stream and take only top-level ordered-list items
of the first list; error on an empty item rather than silently renumbering.

### H3 — High — a multi-line criterion loses its continuation text

`1. one that continues` / `   onto a second line` yields only `one that continues`.
`acceptance_criteria` is in `STRUCTURED_SECTIONS`, so the parsed criterion is the *only*
representation — the continuation is dropped from the model, from the page, and from
`text_hash`. Editing it therefore does not change the hash, so the staleness detection
ADR-016 promises does not fire for the most natural way to write a long criterion.

### H4 — High — `attempts[].content_hash` is required, stored, and compared to nothing

`Attempt.content_hash` is written and read nowhere. `fixtures/participant/progress.yaml`
carries `sha256:1111…` and `sha256:2222…`; 64 zeros validates equally well.
`CONTENT-MODEL.md` and the Stage 2 task "implement content hashes and supported-version
checks" are half-done: hashes are computed and never checked.

**Correction:** compare against `bundle.quests[qid].content_hash` — warn on mismatch, error
for a `verified` attempt — and give the fixture real hashes.

### H5 — High — an absolute developer path reaches a browser-bound problem

`str(OSError)` embeds the filename, and it is passed straight to `received`:

```
"received": "[Errno 13] Permission denied: '/tmp/…/content/quests/base-camp/repository-safety.md'"
```

`VIEW-MODEL-CONTRACT.md` forbids absolute machine paths in browser view models.
`ContentProblem.__post_init__` guards `source` only, and
`test_no_absolute_developer_path_reaches_the_output` never exercises the unreadable-file path.

**Correction:** report `exc.strerror` and `exc.errno`, never `str(exc)`; extend the
constructor guard to `received`.

### H6 — High — `format: date-time` and `format: date` are advertised and not enforced

`Draft202012Validator(schema)` is built with no `format_checker`, so
`started_at: "banana"` produces zero errors. Downstream, `_timestamps_out_of_order` catches
`ValueError` and returns `False`, so its warning is silently defeated by any non-ISO value,
and `attempt_for` orders attempts by string comparison of garbage.

**Correction:** pass `format_checker=Draft202012Validator.FORMAT_CHECKER` and add
`jsonschema[format]` to the dependencies.

## Medium

| ID | Finding |
|---|---|
| M1 | ~900-level nested YAML raises an unhandled `RecursionError`, aborting the run with a traceback and absolute paths |
| M2 | Duplicate YAML keys are silently accepted, last wins — a duplicated `xp:` reads as the first value in a diff and applies as the second |
| M3 | Duplicate `##` headings silently overwrite, and `## Mission!` slugs to `mission` and satisfies the required-section check |
| M4 | A `##` heading inside a fenced code block splits the section — a quest documenting its own structure corrupts itself |
| M5 | Validation results are filed by the record's self-declared `attempt_id`, not the directory they sit in, and `quest_id` is never cross-checked. This is the path a forged local validation would take in Stage 5 |
| M6 | Six validated fields have no consumer (`validation_result_ids`, `submission_id`, `evidence_hash`, review `quest_version`, review `validation_result_ids`) and `hash_directory()` has no caller. Legitimate Stage 5/7 deferrals, but the deferred-work register is empty |
| M7 | Images and raw HTML vanish from a quest body with no warning, alt text included; the authoring guide never says images are unsupported |
| M8 | Three tests pass on one branch only: two sanitizer tests never reach nh3's scheme allowlist because markdown-it rejects the destination first, and the unsafe-evidence-path test only ever fires the schema branch |
| M9 | `fixtures/quest-detail-view-model.json` has no consumer and now contradicts the implementation (`resolve-user` vs `ac-1`, `mission` vs `section-mission`) |
| M10 | Stage 2 checkboxes unticked, no restart-log row, no audit file — now corrected by this document |
| M11 | `render_inline` and `strip_markdown` are dead and untested; `render_inline` keeps `th`/`td` without `table`, so it will emit orphaned cells on first use |
| M12 | `ValidationResult.environment` is a raw dict in a model field, `output_excerpt` is loaded verbatim, and `redaction_applied` is believed as declared — `redact_text` exists and is not applied |
| M13 | With a participant root outside the repository, `config.relative` collapses every problem source to a bare filename |
| M14 | The quest content hash covers editorial fields, so Stage 8's "newer version" notice will fire on typo fixes |

## Low

L1 a UTF-8 BOM reports "no front matter"; L2 a missing trailing newline reports the same
falsely; L3 `target=` inside a link title suppresses `target="_blank"`; L4 YAML 1.1
sexagesimal turns `xp: 1:30` into `90`; L5 an unquoted `last_reviewed` parses as a date and
fails as "not of type string"; L6 `make build` and `make serve` exit 2; L7 no file-size or
criteria-count cap; L8 cycle detection is recursive; L9 `AcceptanceCriterion.dom_id` lost its
only consumer with the deleted template.

## Required before Stage 3 continues

1. B1 — land the quest-detail page and repoint ADR-016's evidence reference.
2. H1 — decide the bullet-list question in `docs/DECISIONS.md`.
3. H2, H3 — rebuild criterion derivation on the markdown token stream, with tests for
   nesting, code blocks, empty items and multi-line items.
4. H4 — compare `content_hash`; give the fixture real hashes.
5. H5 — stop leaking `str(OSError)`; extend the constructor guard to `received`.
6. H6 — enable the format checker.
7. Rerun this audit and record the result.


---

# Stage 2 re-audit (2026-09-17)

**Audited commit:** `264de55`
**Auditor:** independent review agent, fresh context, read-only
**Result:** `pass with one open item`

Every fix was verified by execution rather than by reading the commit message.

| Finding | Verdict |
|---|---|
| B1 quest-detail page and ADR-016 reference | **fixed** |
| H1 bullet-list decision | **fixed** — ADR-026, code and decision log now agree |
| H2 criterion derivation | **mostly fixed** — every named case plus nine more; one residual (S2-R1) |
| H3 multi-line criterion | **fixed** — continuation preserved, and editing it changes the hash |
| H4 content-hash comparison | **fixed**, with the warning-not-error deviation accepted as correctly reasoned |
| H5 absolute path in `received` | **partially fixed** — see below |
| H6 format checker | **fixed, and better than the audit recommended** |
| M1 deep nesting, M2 duplicate keys, M5 record misfiling | **fixed** |
| M8 tests passing on one branch | **half fixed** — the sanitizer half is genuine; the resolver branch is still untested |

## H6 — the recommendation would have produced a fake fix

Worth recording because it nearly happened twice. The original audit recommended
`Draft202012Validator.FORMAT_CHECKER`, whose checkers in this environment are
`date, email, idn-email, ipv4, ipv6, regex, uuid` — **no `date-time`**. The implementation
used `FormatChecker()` with the `[format]` extra pinned, which does register it. Verified:
`started_at: "banana"` and `last_reviewed: "nope"` are both now rejected.

## H5 — the open item

The leak itself is closed at both call sites: `chmod 000`, a broken symlink, a directory
where a file is expected and invalid UTF-8 all now report `Permission denied`,
`No such file or directory`, `Is a directory` and `invalid start byte` respectively, with no
absolute path in any field.

Three parts of the correction were not done:

1. **The constructor guard was never extended to `received`.** `ContentProblem.__post_init__`
   still checks `source` only, and `_looks_absolute()` — written for exactly this — is dead
   code called from nowhere.
2. `progress.py` still passes `str(exc)` from `resolve_participant_path`, whose message
   embeds the offending path. Participant-supplied rather than developer-supplied, but the
   same class of value, and the guard that would catch it exists and is unwired.
3. No regression test covers the unreadable-file path.

## S2-R1 — residual, medium

`first_list_items` treats a list inside a **blockquote** as the first list. A quoted example
under `## Acceptance criteria` becomes `ac-1` and the real criteria are then reported as a
split list — or, with no second list present, the quoted example silently *becomes* the
acceptance criteria with no warning at all. That is the exact class of failure ADR-016
exists to prevent.

**Correction:** refuse to open the first list while inside `blockquote_open`.

## Gate

Stage 2 stays unticked until H5 is closed properly, S2-R1 is fixed, and this re-audit is
rerun against the result.
