# Security and Privacy Requirements

## Threat model

The application reads repository content, displays authored Markdown, updates participant files, and runs selected validators. Those capabilities expose risks even when the service is local.

Primary threats include:

- malicious Markdown or embedded HTML;
- path traversal through content or request parameters;
- arbitrary command execution disguised as validation;
- prompt injection inside tickets, transcripts, comments, or repository files;
- secret capture in evidence, logs, screenshots, or Git;
- cross-origin requests against a localhost service;
- symbolic links escaping participant-owned roots;
- unsafe external writes;
- forged review or verified state;
- validators that hang, fork excessively, consume storage, or alter unrelated files.

## Browser-content safety

- Sanitize rendered Markdown using an explicit allowlist.
- Disable raw HTML by default.
- Escape all template values by default.
- Use a restrictive Content Security Policy.
- Do not load remote scripts, fonts, analytics, or images by default.
- Treat URLs from content as untrusted; permit only documented schemes.
- Add `rel="noopener noreferrer"` to external links opened in a new context.
- Never render validator logs as trusted HTML.

## Local service safety

- Bind to loopback only.
- Generate a per-run anti-request-forgery token.
- Require the token for every state-changing request.
- Validate `Origin` when present and reject unexpected origins.
- Enforce request-body limits and strict content types.
- Map route IDs to server-side records rather than accepting filesystem paths.
- Canonicalize paths and verify they remain within approved roots after resolving symbolic links.
- Write atomically and preserve recoverable prior state.

### Files in the participant tree

The participant tree is untrusted input, so reads and writes there follow fixed rules
(`quest_app/safe_io.py`, ADR-042):

- A state file, record or validation result is read only if it is a regular file, and only
  up to a ceiling. A FIFO, a device or a link to either is reported, never read. A
  state record (`progress.yaml`, `submission.yaml`, `review.yaml`, a review archive) that is
  itself a link is reported and never read, wherever it leads (ADR-043).
- Nothing is written through a symbolic link, into a directory reached through one, or onto
  a target that is not a regular file. Nothing is opened in a way that can block.

### The application's own roots

`generated/`, its `.building`, `.previous` and `.lock` siblings, and `local-data/` are
written by the application and never resolved through links (ADR-043):

- A build refuses, deleting nothing, when any of the four generated paths is a link; when
  the generated root, staging or previous directory is, contains or lies inside a source
  folder, the participant root or local data, or is or contains the repository; and when
  one of them already exists as a non-empty directory with neither the
  `.golden-thread-output` marker nor `build-manifest.json`.
- The build error page and the service port file are written with the same no-follow walk
  as participant files, starting at `local-data/`, which is itself refused if it is a link.
  The build lock is opened with `O_NOFOLLOW | O_NONBLOCK`.

| Ceiling | Applies to | Over it |
|---|---|---|
| 2 MB (`MAX_STATE_BYTES`) | `progress.yaml`, `review.yaml`, review archives, `submission.yaml` | reported by `validate`; not read |
| 8 MB (`MAX_VALIDATION_RESULT_BYTES`) | a validation result | refused when written; reported by `validate` if found |
| 2 MB (`MAX_EVIDENCE_FILE_BYTES`) | each evidence file the secret scan reads (not images, PDF or zip) | a scan finding that blocks submission and tells the participant to trim the file |

The scan is not limited to the attempt's evidence package. A quest's declared proof commonly
names files outside it (`participant/context/**`, `participant/skills/**`); `scan_declared_proof`
(`quest_app/evidence.py`) scans those too, under the same rules, so that "no secret was found"
on the mark-evidence-ready gate, the submission gate, and every page that reports the scan
means the same thing everywhere.

Validator output has its own limits: see `docs/VALIDATOR-CONTRACT.md`. Evidence is hashed
by streaming, so a large image or archive costs time, not memory.

## Validator safety

Validators are registered by stable ID. A registry entry defines:

- executable or Python callable;
- fixed argument template;
- allowed parameter types and values;
- working directory;
- environment-variable allowlist;
- read/write path policy;
- timeout;
- output limit;
- success and inconclusive semantics;
- redaction rules.

The service must never pass user input to `shell=True` or an equivalent shell command string. Use argument arrays and explicit paths.

Validators should run with the least available privileges. The architecture should permit future container or process sandboxing without changing quest content.

## Secret handling

- Credentials come from authenticated CLIs, environment variables, or approved credential stores.
- Content, progress, evidence, logs, screenshots, and Git must not contain secrets.
- `.gitignore` includes common secret and local-response patterns.
- A secret scanner runs before submission preparation, and again when a reviewer records an
  approval: an approval is refused while it finds anything (round 17 E5).
- Logs redact configured keys and token-like values.
- Raw external-system responses are stored only under Gitignored `local-data/` and are opt-in.
- A screenshot is not the only kind of evidence the scanner cannot usefully read (round 15
  E11 corrected this: it previously named screenshots as the one blind spot). It scans
  text, and every image format (`.png`, `.jpg`, `.jpeg`, `.gif`, `.webp`), plus `.pdf` and
  `.zip`, is skipped outright rather than opened. Round 16 E12 found that this used to be
  decided by the file's *extension* alone (`SKIP_SUFFIXES`), so a plain-text secret saved
  as `logs/terminal.pdf` or `logs/env-backup.zip` passed the scan clean on the filename's
  say-so. The decision is now made from the file's own magic bytes
  (`_looks_like_a_skippable_binary_format`, `quest_app/evidence.py`), read from the file's
  header only — never the whole file, so a legitimate multi-megabyte screenshot is still
  skipped whatever its size, rather than being read in full first and then reported too
  large to check. `.docx`/`.xlsx`/`.pptx` share the plain zip signature and there is no
  cheap, reliable way to tell them apart by header bytes alone; since neither is read as
  text either way, this scan treats every zip-signed file the same rather than claiming a
  distinction it cannot make. A compressed or container format that carries none of these
  signatures — `.gz`, `.7z`, `.tar` and similar — is not skipped, but its bytes are not text
  either: the scanner decodes and pattern-matches them anyway, and a real secret inside such
  a stream does not survive decompression into a shape any pattern recognizes, so it passes
  with the same silence a skipped file would. Three of the signatures — `GIF87a`, `GIF89a`
  and `%PDF-` — are plain ASCII, so a text file can open with one; round 17 E7 found such a
  file was skipped unread. A file opening with one of those three is skipped only when its
  first 64 KB are not NUL-free UTF-8, which a real GIF's screen descriptor or a real PDF's
  binary comment line and compressed streams never are. A zip written with no compression
  (`ZIP_STORED`) still carries its members' text verbatim and is still skipped. The `PROOF.md` template every attempt is given
  ends with a **Sensitive values** section asking the participant to confirm the package
  carries no secret, customer name or private ticket content, and clearing an image,
  archive or office document before it goes in is their judgment. There is no automated
  gate over any binary or compressed format, and release one does not claim one.

### Secret-scan patterns (`quest_app/secret_patterns.py`)

- Every fixed-prefix pattern (`ghp_`, `AKIA…`, `glpat-`, `xox[abposr]-`, `xapp-`, `AIza`,
  `sk-ant-`, `ATATT3`, `ATTA`, `github_pat_`, `ya29.`, a JWT's `eyJ`, plus the generic
  `sk-`/`sk_`/`rk_`/`npm_`) is matched case-sensitively: a real credential has a fixed case,
  and matching either case only invited false positives from ordinary uppercase text.
- A **distinctive** prefix (long and specific enough that it does not occur inside an
  ordinary word or identifier) keeps no leading word boundary, so a token glued directly to
  a preceding letter or digit is still caught. A **short generic** prefix (`sk-`,
  `sk_`/`rk_live|test_`, `npm_`) requires a value that is not directly preceded by a letter
  or digit *and* contains at least one digit, because these fragments do turn up mid-word in
  ordinary evidence (a Trello card URL, a test name, a branch name) and a real key of this
  shape always has a digit in it. `openai-key`'s digit check used to be an unbounded
  lookahead sharing its own character class, so a run of nothing but `sk-` (no digit
  anywhere) failed that lookahead from every occurrence, each failure re-scanning to the end
  of the string: quadratic (round 16 E1; 80 KB took 6.3s, a 2 MB file never finished under
  the locks this runs inside of). The lookahead is now bounded — a real key is nowhere near
  200 characters long, so nothing genuine stops matching.
- Detected formats also include a GitHub fine-grained personal access token, a Trello API
  token, a Slack app-level token, a Google OAuth access token, a PGP private key block, a
  credential passed as a `key=`/`token=` URL query parameter, a credential passed to curl's
  `-u`/`--user` flag (round 16 E11; the scan requires the literal word "curl" earlier in the
  same command, so an unrelated colon-separated flag argument, such as a container runtime's
  numeric user:group, is not a false positive; round 17 E2 added a quoted credential, a value
  glued to the flag, `-u` at the end of a cluster of curl's argument-less short flags, and a
  `-u` on a backslash-continued line), a credential held in an XML element (Maven's
  `settings.xml` and similar tooling; round 17 E7 added compound tag names such as
  `<db_password>`, attributes on the tag, and a value on its own line between the tags) or
  in an XML attribute next to one that names it (Spring's `<property name="password"
  value="…"/>`, .NET's `<add key="…" value="…"/>`), and a credential held in a YAML block
  scalar (`password: >-` / `password: |`, with or without an indentation indicator or a
  trailing comment, followed by an indented value the flow-style unquoted pattern below never
  reaches on its own).
- Round 17 added: a whole private key block is one match — its armor headers, base64 body
  and END line, not only the BEGIN line (E1, which left the key body readable in the
  generated evidence and review pages while reporting it redacted); an assignment whose name
  carries text after the credential word (`SECRET_KEY=`, `DB_PASSWORD_PROD=`, `secretKey:`,
  `passwordHash=`, and an upper-case `_KEY` env-var name such as `TRELLO_KEY`), unless that
  text says the value describes a credential rather than holding one (`password_file`,
  `token_expires_at`, `tokenizer`, `total_tokens`; E2); the `:=` and `=>` separators, a
  double-quoted value containing an apostrophe and either quote containing an escaped quote;
  a credential passed as a separate `--password`/`--token` argument, to `docker login -p`,
  or glued to `mysql -p`; and the first cookie of a `Cookie`/`Set-Cookie` header (E4).
  A bare shell variable (`--token $GITHUB_TOKEN`) is a reference, like `${GITHUB_TOKEN}`.
- A file is decoded several ways and every decoding is scanned, since a whole file is not
  always one encoding (round 15 E6): by byte-order mark (a 4-byte UTF-32 mark is checked
  before the 2-byte UTF-16 marks it starts with the same two bytes as); by a high NUL-byte
  ratio with endianness inferred from where the NULs fall, for a file with no mark at all; a
  plain UTF-8 decode always; and, whenever any NUL byte is present, that file's bytes with
  every NUL stripped, decoded as UTF-8. The last two together are what let a file mixing
  encodings — a UTF-8 head with a UTF-16 tail a Windows `>>` append wrote after it, or a
  UTF-16 file whose NUL ratio a run of wide CJK characters dilutes under the whole-file
  trigger — still give up an ASCII-range token, without the scanner having to first decide
  which encoding, or which region of the file, produced it.
- An `Authorization` (or `Proxy-Authorization`) header is a finding whether it carries a
  Bearer credential, a Basic credential, or the `token` scheme GitHub's and Django's APIs
  also accept — a Basic value is flagged without decoding it, since Jira Cloud's documented
  script authentication is exactly `email:api_token` in Basic form, and a `curl -v`
  transcript (the command-record proof the Jira, Trello and GitHub quests ask for) shows the
  header verbatim regardless of what the base64 decodes to.
- `_is_placeholder` recognizes a value that is mostly mask characters (`*`, `x`, `•`) after
  a real-looking prefix — what `gh auth status` prints, and what this scanner's own
  `redact_text` produces — as a placeholder rather than a live credential, and a value
  entirely wrapped in one of the real template shapes (`${VAR}`, `{{ var }}`, `(redacted)`)
  the same way. Round 16 narrowed several of these checks that used to be broader than the
  real template shape they were named for:
  - A paren or brace elsewhere in a value no longer suppresses it on its own (round 16 E6
    narrowed this further than round 15 E12 had): a real password that happens to contain
    one (`Tr0ub4dor(3)x`) is detected. The remaining allowance — a real call or subscript
    shape (a lower-case identifier, optionally dotted, immediately followed by `(` or `[`,
    closed, or left open only where more identifiers and openers follow before the value
    class stopped at an argument's quote) — is kept
    only for the unquoted assignment pattern, which has no closing delimiter of its own and
    so captures straight into this module's own source wherever a keyword-named variable is
    assigned a call expression (`token = payload.get(`) or is itself passed as another
    call's own argument (`OpenAI(api_key=api_key)`). Round 17 E5 checks that shape as
    written: every identifier in it must read as code rather than a word-based password (no
    more than one digit between letters, and then only in a lowercase name), a call's or
    subscript's arguments may only be identifiers, numbers and operators, a bare closing
    `)`/`]` follows only a digit-free name, and a `{name}` placeholder is written in one
    case — so a password that merely ends like a call, a subscript or a placeholder is a
    finding.
  - Only a value that is entirely a `$(…)` command substitution or a `{{ … }}` expression is
    a template (round 17 E4): one that merely starts like one used to be excused whatever
    was glued after it.
  - `${VAR:-default}`/`${VAR-default}` is a shell or compose *default* — a real value the
    moment the variable is unset (an env file's `DB_PASSWORD=${DB_PASSWORD:-Sup3rS3cretValue9}`  <!-- # secret-scan: allow -->
    is the ordinary docker-compose/.env shape) — and round 16 E5 found it was being waved
    through as a placeholder just like a bare `${VAR}`. Only a value that is entirely `${NAME}`,
    optionally with a `:?message` clause (an error string shown when unset, never a
    default), refers to the environment rather than holding one now.
  - A dotted identifier chain is an attribute path, not a secret, only when it starts from
    one of the names this codebase's own source and its docs' own examples use for the
    object being accessed (`self`, `config`, `os`, and similar). Before round 16 E7, any
    short dotted chain qualified, so a dotted passphrase (`correct.horse.battery.staple`,
    `Welcome.To.Acme`) read exactly like an attribute path and was never reported. Round 17
    E6 checks every segment, not only the root: each must be a digit-free lowercase
    `snake_case` or `UPPER_SNAKE` name, and the chain is at most four names long.
  - A lone `<` or `>` at one end of a value used to be enough on its own to call it a
    template; round 16 E11 found that a real value merely starting with a stray `<` or
    ending with a stray `>` was waved through the same way. Only a matched `<...>` pair,
    start to end, is a documentation placeholder now.
  - The bracket-shaped unquoted value (`[REDACTED]`, `[Pr0d]`) used to stop at the closing
    `]`, so a placeholder glued to a real value (`[Pr0d]Sup3rS3cretValue`) captured only the
    bracket — a finding, but the wrong span, and redacting it left the real value in clear
    text, itself scanning clean (round 16 E4). A placeholder is only ever a value that is
    *entirely* one bracketed token; anything glued after the bracket is part of the value
    now, so it is captured, reported and redacted along with it.
- The keyword `token` does not fire immediately after `page` (case-insensitively), so
  Jira's own pagination fields — `nextPageToken`, `pageToken` — are not a credential just
  because the quest that asks participants to page through them also asks them to keep
  submitting the value as text. Round 16 E11 added `DB_PASS`/`PWD`-style keywords too: a
  bare `pass` is not safe to add on its own (this repository's own test-result vocabulary
  uses it as a plain field name, and English has "bypass"), so it requires a leading
  underscore (`DB_PASS`, `ADMIN_PASS`); `pwd` has no such restriction, except that a
  standalone `PWD`/`OLDPWD` whose value is a filesystem path is the shell's own
  working-directory variable, printed by every `env`/`printenv` transcript, and is not a
  finding (round 17 E9; a compound name such as `DB_PWD` is detected whatever its value).
- Round 17 E1: a keyword may be followed by an identifier suffix before its operator, so
  `SECRET_KEY`, `JWT_SECRET_KEY`, `SECRET_KEY_BASE`, `DB_PASSWORD_PROD`, `JIRA_API_TOKEN_2`,
  `secretKey` and `DB_PASS_PROD` are all assignment keys now; the encryption, storage-account
  and signing key compounds and the `dbPass`/`$dbpass` spellings (after a named
  credential-owner prefix only, so "bypass" and "onPass" stay vocabulary) were added. A
  suffixed name's value must start on the same line as its operator, since a Python class
  header followed by its body is otherwise exactly that shape, and a single-case
  `snake_case`/`UPPER_SNAKE` name that itself contains a keyword is read as the name of a
  credential (`TOKEN_PLACEHOLDER = REQUEST_TOKEN_PLACEHOLDER`), not as its value.
- An unquoted value is read whole (round 17 E3, E4, E17, C2): a bracket of any length glued
  to more value, a `]` that more value follows, a `${…}`/`$(…)`/`{{…}}` template with value
  glued after it, a `}` with more value glued straight after it, and a `,` or `;` glued
  between two runs of value characters (as long as the run after it reaches a real end of
  value and has none of `=`, `:`, `(`, `)`, `{`, `}`, `[`, `<`, `>` in it, which is what keeps
  code such as a call's next keyword argument out) are all part of the value, so the whole
  value is reported and redacted. A trailing run of nothing but `]` is left out, so a
  redaction followed by a stray bracket stays a fixed point of the scan.
- Markdown's backslash escapes and HTML character references render as the character they
  stand for, so the scan also reads the text with every escaped ASCII punctuation character
  and every reference to a printable ASCII character resolved, and redacts what it finds
  there on the escaped original (round 17 E11): a token written with its underscore escaped
  no longer passes the scan and then renders live.
- **Known gap, not fixed:** a token glued on its right to `_` or to a letter outside its
  character class (`x_ghp_<36 chars>_y`, `ATTA<64 hex>XYZ`) is still missed. The trailing
  `\b` after each distinctive-prefix pattern requires a transition between a word and a
  non-word character; loosening it risks matching into an ordinary longer identifier or hex
  run the same way the leading boundary once did (round 13 E11 / round 14 E1), and no
  corpus here demonstrates that trade is safe yet.
- Every pattern with an unbounded quantifier ahead of a literal that a pathological input
  never supplies used to be quadratic in the input length (round 15 E5): `basic-auth-url`'s
  scheme and `jwt`'s three segments are now bounded (a scheme cannot be longer than 32
  characters; a JWT segment cannot be longer than 4096, its header segment cannot be longer
  than 512), which keeps a 2 MB adversarial file under a few seconds rather than the hours
  an unbounded scan of one would cost, all of it held under the store, `generated` and
  service locks. `scan_text`'s own overlap bookkeeping had the same shape of problem one
  level up (round 16 E2): it used to scan every already-claimed span for every new match, an
  `O(matches^2)` cost that took 497s for 95k distinct AWS keys in a 2 MB file even though the
  AWS pattern itself is linear. Each pattern's own matches arrive left to right and
  non-overlapping, and the accepted set stays sorted and disjoint by construction, so a
  whole pattern's batch of new claims is now folded into the existing set with one merge of
  two already-sorted sequences, the same `O(a + b)` step a merge sort's merge is, rather
  than a fresh scan per match.

### Scan and hash boundaries for declared proof outside the package

A quest's declared proof commonly names files outside the attempt's evidence package
(`participant/context/**`, `participant/skills/**`); `scan_declared_proof`
(`quest_app/evidence.py`) scans those too, under the same rules, so that "no secret was
found" on the mark-evidence-ready gate, the submission gate, and every page that reports the
scan means the same thing everywhere. For a declared directory, the scan and the evidence
digest (`proof_file_digests`) use the same boundary — the declared path itself — so a link
that leaves that path is refused identically by both: it is an "outside the evidence
package" scan finding, not something that scans clean while the digest silently stops
covering it. A declared path that does not resolve inside `participant/` at all is reported
the same way, rather than skipped, and a directory reached through a symbolic link is a
finding rather than a silently unscanned subtree, since neither the scan nor the digest
descends into one.

An evidence directory or a declared directory that cannot be listed (permission denied) is a
blocking "could not be read to check it" finding from the scan and an `UnreadableFileError`
from the hash — the same treatment an unreadable file already gets — rather than being
silently absent from both.

## External-system writes

**Release one performs none.** Every quest declares `risk.external_write: false`, every
validator is registered `network: denied` (a declaration that review holds, not a socket
block: see `docs/VALIDATOR-CONTRACT.md`), and the application makes no outbound request of
its own. The requirements below are the conditions a write-capable quest must meet before it
is added — not a description of a mechanism running today. `tests/test_release_facts.py`
asserts the invariant while it holds, so the day a quest declares a write, the test that
fails says this section now has to be built.

Any quest that creates or modifies Jira, Trello, GitHub, or another service must require:

1. A preview showing the intended target and exact material changes.
2. Duplicate and permission checks where supported.
3. Explicit human confirmation immediately before the write.
4. A result record with external identifiers and timestamp.
5. Safe rerun behavior or clear idempotency limitations.

Opening a page, running a build, or viewing a quest must never perform an external write.

## Review integrity

- Review decisions contain stable review and attempt IDs.
- The application verifies the decision is internally consistent with the attempt, quest and
  version it names — not that it was made about *this participant's* attempt. Attempt IDs are
  not unique across participants by default, so a genuine approval, evidence package
  included, copied whole from another participant's repository into this one names the same
  attempt, quest and version and verifies with no warning. That is no stronger a claim than
  authoring a forged record by hand, a gap ADR-030 already documents; Git history of who
  committed `review.yaml` (or reviewing through pull requests) is the signal this application
  does not itself check.
- Participant-edited review files are displayed as untrusted until provenance is established.
- The first release may use Git review and reviewer identity conventions rather than cryptographic signing, but the limitation must be visible.
- Changing evidence after approval marks the review potentially stale when tracked artifact hashes differ.

## Privacy and telemetry

- No telemetry leaves the machine by default.
- A future central scoreboard receives only explicit opt-in, sanitized public progress.
- Public progress must not contain evidence paths, repository URLs, ticket contents, credentials, email addresses, or private organization names unless deliberately supplied.
- The application explains every outbound request it initiates.

## Required security tests

- `../` and encoded path traversal attempts
- symbolic-link escape attempts
- shell metacharacters in all text and ID fields
- malicious Markdown and script URLs
- oversized request and validator output
- missing and invalid request tokens
- cross-origin state-changing requests
- validator timeout and child-process cleanup
- secret-like values in logs and evidence
- forged verified state without approval
- modified evidence after approval
- external-write action without preview or confirmation — not yet reachable: no quest
  declares an external write, so the assertion that stands today is that none does
