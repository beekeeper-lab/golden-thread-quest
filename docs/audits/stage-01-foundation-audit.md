# Stage 1 — Repository and Engineering Foundation Audit

**Stage:** 1 — Repository and engineering foundation
**Branch:** `feature/golden-thread-implementation`
**Audited commit:** `f52d50e`
**Auditor:** independent review agent, fresh context, read-only
**First result:** `fail` — 2 blocking, 2 high, 3 medium, 5 low
**Result after fixes:** `pass-with-advisories`

## Method

An independent agent with no knowledge of how the code was written read the Stage 1 section
of the implementation plan, `SECURITY-AND-PRIVACY.md`, `ARCHITECTURE.md`, every file added
in the stage, and the Git diff; then attacked `tools/clean.py` and `tools/secret_scan.py`
in a sandbox copy of the repository rather than reasoning about them.

That is what found B2. Reading `clean.py` suggests an allowlist. Running
`ln -s prototype generated && clean.py --apply` shows a denylist with holes.

## Findings

### B1 — Blocking — `make check` had never passed, and CI had never been green

**Evidence.** `tools/secret_scan.py` scans every tracked file.
`tests/unit/test_secret_patterns.py` necessarily contains fifteen strings that match its own
detectors. `make check` therefore exited non-zero on a clean checkout, which falsified the
claim in `CONTRIBUTING.md` that a green `make check` means a green CI, and left two of the
four Stage 1 required tests unmet.

**Correction.** Added the ignore mechanism the plan implied rather than deleting the fixtures
or loosening the patterns (which `CLAUDE.md` rule 12 forbids). A line ending in
`# secret-scan: allow` is skipped.

The pragma lives in `tools/secret_scan.py`, not in `quest_app/secret_patterns.py`, and that
placement is the point: this tool is repository hygiene over program-owned code that a
reviewer reads, while evidence scanning and validator-output redaction call `scan_text`
directly. A participant cannot switch off the check on their own submission by writing a
comment in it. `tests/security/test_secret_scan_tool.py::test_pragma_is_not_honoured_by_the_pure_scanner`
holds that boundary.

**Verification.** `make check` exits 0. `tools/secret_scan.py` reports 0 findings over 84
files.

### B2 — Blocking — `clean.py --apply` deleted program-owned files through a symlink

**Evidence.** `resolve_target()` resolved the path first and then screened only the first
component of the result against a denylist of protected names. In a sandbox copy:

```
$ ln -s prototype generated && python tools/clean.py --apply
removed prototype          # prototype/ and everything in it
```

and `generated/../README.md`, `local-data/../.github`, `.coverage/../Makefile` and
`Participant/evidence` (different case) all resolved to allowed paths. The guard at
`target.is_dir() and not target.is_symlink()` was dead: `target` was already resolved, so
`is_symlink()` was always false and `rmtree` always followed the link.

**Correction.** Rewritten as a real allowlist:

1. the repository-relative path must be **exactly** an entry in `REMOVABLE`;
2. any `..` segment is refused before anything touches disk;
3. every component of the **unresolved** path is checked for being a symbolic link, walking
   down from the repository root — a resolved path has no links left in it, which is why
   asking afterwards always answered "no";
4. `PROTECTED` is compared case-insensitively, because macOS filesystems are;
5. removal operates on the unresolved path, so a symlink is unlinked rather than followed.

**Verification.** Every probe above is refused. `tests/security/test_cleanup_safety.py` now
covers the inside-repository symlink, the outside-repository symlink, all four traversal
escapes, the case-insensitivity hole, and — because `REMOVABLE` is data that a future edit
could get wrong — an unsafe entry injected into `REMOVABLE` at test time.

### H1 — High — the scanner had no tests, and a cleanup test asserted the opposite of its name

**Evidence.** Nothing imported `tools/secret_scan.py`; `tracked_files()`, `eligible()`,
`SKIP_DIRS` and the exit code were all uncovered, which is precisely why B1 shipped.
`test_symlinked_generated_directory_is_unlinked_not_followed` asserted that
`resolve_target` *raises* — nothing was ever unlinked — and covered only the
outside-repository link, not the inside-repository link that B2 exploited.

**Correction.** Added `tests/security/test_secret_scan_tool.py` (13 tests: planted secret,
pragma scope, skipped directories, binary and oversized files, undecodable input, paths
outside the repository, exit codes, JSON output, and a slow test asserting the repository
itself is clean). Replaced the misnamed cleanup test with one that names what it asserts and
two that cover both link directions.

### H2 — High — the detector missed the formats this product actually handles

**Evidence.** `generic-assignment` required quotes around the value and a delimiter
immediately after the keyword, so it missed `.env` lines, YAML values, JSON fields, bearer
headers, Stripe keys and npm tokens — the shapes that dominate evidence packages and raw API
responses, which is where `secret_patterns.py` does most of its work from Stage 5 onward.

**Correction.** Split into quoted and unquoted assignment patterns over a wider keyword list,
plus `bearer-header`, `stripe-key` and `npm-token`. All seven previously missed formats are
now detected and all documentation forms are still ignored, including a new rule that any
value containing a brace is a template fragment rather than a credential — real tokens, keys,
JWTs and base64 contain no braces, so it costs no detection and removes a class of false
positive from source, Jinja templates and CI configuration.

### M1 — Medium — the scanner crashed on any path outside the repository

`relative_to(REPO_ROOT)` raised `ValueError` for `secret_scan.py /tmp/x.txt`. Added
`display_path()`, which falls back to the plain path, with a test.

### M2 — Medium — the scanner's own output leaked part of every secret

The excerpt printed four leading and two trailing characters plus the exact length, into CI
logs — itself a place secrets leak from. Reduced to a three-character lead for values of
twelve characters or more, nothing at all for shorter ones, and removed entirely from the
`--json` output, which is the form most likely to be stored or forwarded. Two tests.

### M3 — Medium — CI duplicated the Makefile's commands instead of invoking it

The six checks matched at the time but nothing prevented drift, and the documentation
already made a claim that was false (B1). CI now runs `make format-check`, `make lint`,
`make typecheck`, `make yaml-safe`, `make secret-scan` and `make test`.

### L1 — Low — licensing

All runtime dependencies are permissive: Jinja2 BSD-3-Clause; PyYAML, jsonschema,
markdown-it-py and nh3 MIT. Dev dependencies are MIT or Apache-2.0, with one transitive
MPL-2.0 (`pathspec`, via mypy, development only). Two real gaps, both closed: the project
declared `Proprietary` with no `LICENSE` file — added, and it states explicitly that work a
participant authors under `participant/` belongs to that participant — and `pytest-cov` was
installed while nothing ran coverage, so it has been removed. Coverage reporting is deferred
rather than half-configured.

### L2 — Low — `.gitignore` gaps

The file already satisfied `SECURITY-AND-PRIVACY.md` for every named case, and `.env.example`
was verified line by line to contain no real value. Added `.envrc`, `.pgpass`, `*.jks`,
`*.keystore` and `coverage.xml`.

### L3 — Low — pre-commit diverged from CI

The hooks ran mutating `ruff format` and `ruff check --fix` where CI runs `--check`, so a
commit could be rewritten under the developer and a difference hidden rather than prevented.
Both hooks now verify.

### L4 — Low — three documented commands do not exist yet

`make build`, `make serve`, `make validate-content` and the three console scripts point at
`quest_app.cli`, which arrives in Stage 2. `docs/SETUP.md` presents them as working. Accepted
as stage sequencing; the Stage 2 audit checks that they work before the documentation claim
stands.

### L5 — Low — `participant/` was not created

The ownership boundary that `CONTRIBUTING.md` and `docs/SETUP.md` describe has no on-disk
existence yet. Deliberately deferred to Stage 4, where participant state is first written:
creating an empty directory now would imply a feature that does not exist. Recorded in the
restart log so the Stage 1 task is not left ambiguous.

## Process finding

The audit also noted that Stage 2 code was present and uncommitted in the working tree while
Stage 1 was unaudited — `CLAUDE.md` rules 4 and 8. Correct, and worth recording rather than
quietly fixing: B1 and B2 were corrected on top of the audited commit before Stage 2 work
resumed, and the Stage 2 modules were not committed until Stage 1 passed.

## Audit gate

- [x] Dependency necessity and license compatibility reviewed; `LICENSE` added, unused
      dependency removed.
- [x] Scripts reviewed for destructive behaviour; two real deletion paths closed and covered
      by tests.
- [x] `.gitignore` and example configuration reviewed for secret leakage.
- [x] CI verified to invoke the documented local commands.
- [x] Rerun result: `pass-with-advisories` — `make check` exits 0, 85 tests pass.

## Carried forward

| ID | Carried to | Item |
|---|---|---|
| L4 | Stage 2 | `make build` / `serve` / `validate-content` must work before the setup guide's claim stands |
| L5 | Stage 4 | Create `participant/` when participant state is first written |
| — | Deferred register | Coverage reporting |
