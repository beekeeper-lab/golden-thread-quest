# Part 5. The security model

A local application still has attackers. Every program on the machine can reach a loopback
port, every web page the participant opens can try to post to it, and the repository it
reads can arrive from someone else as a pull request. This part states the threats and the
control that answers each, with the code that implements it.

## 5.1 Threats

From `docs/SECURITY-AND-PRIVACY.md`, restated as what the application must prevent:

1. A web page in the participant's browser making the local service change state
   (cross-site request forgery, DNS rebinding).
2. Any caller running an arbitrary command or reading or writing an arbitrary path through
   the service or the CLI.
3. Malicious Markdown in curriculum or evidence running script in the generated pages.
4. A validator reading credentials, escaping its folders, hanging, or flooding output.
5. A secret reaching evidence, a log, a validation result or Git.
6. A forged `verified` state, or an approval of evidence the reviewer never saw.
7. A hostile repository (a participant's fork checked out by a reviewer) crashing or hanging
   the application through symbolic links, FIFOs, huge files or deeply nested YAML.

## 5.2 The loopback boundary

The service is the only component that accepts requests, so it carries most of the
controls. A request meets them in this order (`quest_app/serve.py`):

| Control | Rule | Why |
|---|---|---|
| Loopback bind | `assert_loopback` refuses any bind address other than `127.0.0.1`, `::1` or `localhost` at startup | Nothing off the machine can connect |
| Host check | A request whose `Host` is not a loopback name gets 403 before anything is rendered (ADR-041) | A page at an attacker's domain that resolves to `127.0.0.1` is same-origin to the browser and could read a served page and take the token from it |
| No body on GET | A GET with a declared body is refused | An undeclared body on a kept-alive connection would be parsed as a second request with attacker-chosen headers |
| Origin check | For state-changing requests, `Origin` and `Referer`, when present, must be `http` on a loopback name at the bound port | A page on another site cannot post here. A missing header is accepted because a command-line client sends none; the token is what authorizes |
| Strict body | JSON or form content type only, declared length at most 64 KiB, checked before reading | Bounds memory and parsing |
| Per-run token | Minted at startup, held in memory, substituted into served HTML, compared in constant time; never written to disk or printed | Only a page this run served can act. A page opened from disk has only the placeholder |
| Action allowlist | The action must be in `MUTATING_ACTIONS`; the quest ID must exist in loaded content; a validator must be declared by the quest | No path and no command crosses the boundary: the caller names IDs, the server resolves them |
| Confirmation | `start-quest`, `submit-for-review` and `record-review` need an explicit confirmation, checked in the action layer for every caller (ADR-033) | The actions that create files, hand work to someone else, or produce verified XP happen only when a person said so in that request |
| Response headers | Content Security Policy `default-src 'none'; script-src 'self'; style-src 'self'; img-src 'self' data:; form-action 'self'; base-uri 'none'; frame-ancestors 'none'`, `X-Content-Type-Options: nosniff`, `Referrer-Policy: same-origin`, `Cache-Control: no-store` | No remote script, style or frame; no framing by another page |
| Catch-all | Both handlers answer every exception with a status and the exception type, never a traceback | A traceback would print absolute paths and leave the client with no answer after a change had landed |

**Fixed since round 12 (finding C1, Blocking).** The header, and the matching
`<meta name="referrer">` tag on every page, used to be `no-referrer`, which strips the
browser's `Origin` header to `null` on a same-origin form POST too. The origin check then
refused every browser form as cross-origin; only the CLI, which sends no `Origin` at all,
could change state, and no test had submitted a form in a real browser. `same-origin` still
sends nothing off-site — a cross-origin POST is refused exactly as before — but a same-origin
POST now carries its real origin and passes the check. Verified against real Chromium; two
browser tests submit real forms and check the resulting files on disk.

## 5.3 No arbitrary command, no arbitrary path

- **Commands.** There is no code path from a request to a shell. Validators are Python
  callables imported by an allowlisted module path from the `validators` package, started in
  a child with a fixed argument list. Validator parameters are typed enumerations or numbers;
  there is no string parameter type. `git_status.py` runs exactly five read-only Git commands
  and raises if asked for another; `update.py` runs three read-only ones (ADR-014, ADR-032).
- **Paths.** Participant paths in records keep the contract prefix `participant/` and are
  resolved by `AppConfig.resolve_participant_path`, which rejects absolute paths, `..`
  segments and null bytes, resolves symbolic links, and re-checks that the result is inside
  the participant root (ADR-018). A validator's `Workspace` applies the same rule to its
  registered roots. The service resolves static file paths the same way under `generated/`.
  Writing uses a stricter, separate rule: `AppConfig.participant_write_path` keeps the
  *lexical* location rather than resolving links, because resolving a link and then checking
  the result is exactly what would hide a link a write should refuse (ADR-042, Section 5.4).
- **Deletion.** `tools/clean.py` (behind `make clean`) removes an exact allowlist of
  machine-owned paths and refuses anything reached through a symbolic link.

## 5.4 Allowlisted writes

The application writes to these places only:

| Target | Writer | Notes |
|---|---|---|
| `participant/progress.yaml` | `store.ProgressStore.write` | Schema-validated before writing, atomic, under the progress lock |
| `participant/ACTIVITY.md` | `store.append_audit` | One line per change |
| `participant/evidence/<quest>/<attempt>/` | `store`, `evidence.store_result`, `review` | Template files on start (never overwriting), validation results, `submission.yaml`, `review.yaml` and archives |
| `generated/`, `generated.lock`, `generated.building/`, `generated.previous/` | `build.py` | Disposable |
| `local-data/build-errors/`, `local-data/service-ports/` | `build.py`, `serve.py` | Disposable |
| A validator's registered write roots | The validator, through `Workspace.write_text` | None of the shipped validators declares a write root |

**Fixed since round 12 (finding E1, Blocking).** Three writes used to miss this rule: the
activity line, appended with a plain `open("a")` that followed a symbolic link out of
`participant/` and hung forever on a FIFO named `ACTIVITY.md` while holding both locks;
validation results, written into a `validation/` directory that could itself be a link leading
outside the package; and the review archive, written with a plain `write_text`. Every
participant write now goes through `safe_io.atomic_write` or `safe_io.append_to_regular_file`
(ADR-042), which walk from the participant root one component at a time with `O_NOFOLLOW`,
refuse a component that is a link or not a directory, refuse a target that exists and is not a
regular file, and never open anything in a way that can block. When the refused target is
`ACTIVITY.md`, the line is skipped and a warning goes to stderr, because the change it
describes is already on disk by the time it runs; for every other target the write is refused
before anything changes, like any other write failure.

**Ceilings on what is read from the participant tree.**

| Ceiling | Applies to | Over it |
|---|---|---|
| 2 MB (`MAX_STATE_BYTES`) | `progress.yaml`, `submission.yaml`, `review.yaml` and its archives | Reported by `validate`; not read |
| 8 MB (`MAX_VALIDATION_RESULT_BYTES`) | A validation result | Refused when written by `evidence.store_result`; reported by `validate` if found anyway |
| 2 MB (`MAX_EVIDENCE_FILE_BYTES`) | Each evidence file the secret scan reads (not images, PDF or zip) | A scan finding that blocks submission and tells the participant to trim the file (round 12 finding E8) |

Evidence hashing streams a megabyte at a time rather than holding a file whole in memory, so a
large file costs a build time, not memory.

## 5.5 Untrusted content in the pages

- Quest Markdown is rendered with raw HTML disabled, then sanitized by `nh3` with an explicit
  tag, attribute and URL-scheme allowlist (ADR-021).
- Jinja2 autoescapes every template value.
- `PROOF.md` is rendered through the same path. A symbolic link inside the package that
  resolves outside it is not rendered.
- Validator output is shown as text, never as HTML.
- The search index holds published quest text only, never evidence.
- Pages load no remote script, font, image or analytics, and the CSP forbids them.

## 5.6 Validator containment

Section 2.6 lists the controls: constructed environment, repository-first import path, own
process group, timeout that kills the group, 1 MiB stream ceiling, output limit, redaction of
output and of every check field before truncation, and validation of the result against its
schema, including of each individual check (round 12 finding E6). `Workspace.write_text`
carries the same write rule as the participant tree (Section 5.4): a special file at the
resolved target, such as a FIFO, is refused rather than opened, which used to block a
validator until its own timeout. They bound what a validator does through the `Workspace` and
the process. They are **not** an operating-system
sandbox: nothing blocks a socket, a direct `open()` bypasses the roots, and a process that
starts its own session escapes the group. Container or seccomp isolation is deferred (D9).
Validators are program-owned and reviewed like application code.

## 5.7 Secret scan and redaction

- **The detectors.** `quest_app/secret_patterns.py` holds one set of patterns (AWS keys,
  GitHub, Slack, Google, Anthropic, OpenAI, Atlassian, Stripe and npm tokens, JSON web
  tokens, private-key blocks, bearer headers, credentials in URLs, and keyword assignments
  such as a `password` or `secret` field with a value). Every scan and every redaction uses it.
- **Repository hygiene.** `tools/secret_scan.py` (`make secret-scan`, part of `make check`)
  scans every tracked text file and prints `path:line:column` and the pattern, never the
  value. A line ending in an allow pragma is skipped; this is how the scanner's own test
  fixtures live in the repository.
- **The evidence gate.** `evidence.scan_evidence` scans the whole evidence package before
  `mark-evidence-ready` and again before submission. It calls the detectors directly, so a
  participant cannot switch the check off with the pragma. A file it cannot read, a link
  leading outside the package, and a file over the 2 MB scan ceiling (Section 5.4) all count
  as findings: the scan cannot clear what it may not read. Every finding is one of three
  kinds — secret, link or oversize (`evidence.scan_kinds`) — and the evidence and review pages
  word each one separately, so a link or an oversize file is not reported as "something
  secret-like" (round 12 finding C3). Images and archives are skipped, which is why a
  screenshot is not scanned (a known limitation).
- **Redaction.** Validator output and every free-text check field pass through
  `redact_text` *before* truncation, never after: cutting first can sever a secret-shaped
  token at the boundary, and the half that survives matches no detector's pattern (round 12
  finding E7, fixed). Error messages replace path-shaped text with `<path>`.

**Why a gate and not a report.** A false positive costs the participant a minute. A missed
credential costs a rotation. The scan is a safety net, and the documents say so: widening the
detectors is deferred until there is a corpus to measure false positives against (D10).

## 5.8 Review integrity

- `verified` is re-derived from the review record on every load; an attempt that claims it
  without a matching approval is refused as an integrity error (Part 3, Section 3.5).
- An approval needs a verification statement; a request for changes needs a finding.
- An approval of evidence whose hash or proof-file digests changed since submission is
  refused unless the reviewer acknowledges it; after approval, a later change raises a
  warning that the approval may be stale.
- Reviewer identity is a display name plus Git history, not a signature (ADR-030). The
  limitation is stated in the reviewer guide and the interface.
- A `submitted` attempt needs a readable `submission.yaml` behind it: the loader refuses a
  hand-edited `submitted` with none as the integrity error
  `progress.unsubmitted_submitted_state`, and `record_decision` refuses to act on one even if
  it somehow reached that state some other way. Before this (round 12 finding E4, fixed), such
  an attempt loaded clean and could be approved straight to `verified`, skipping the
  secret-scan gate that `submit-for-review` applies before it ever writes that file.

## 5.9 Hostile repository files

A reviewer runs the application against a participant's repository, so participant files are
treated as hostile input:

- content discovery reads only regular files inside the content tree (a link to `/dev/zero`
  or a FIFO is refused);
- `progress.yaml`, `submission.yaml` and every review record are read through
  `safe_io.read_bounded_bytes`: an ordinary file under 2,000,000 bytes, opened `O_NONBLOCK`
  and checked with `fstat` on the open descriptor, not a `stat` on the path beforehand, so a
  path swapped for a FIFO between the check and the open cannot hang it either;
- a validation result is read the same bounded way, up to 8,000,000 bytes
  (`MAX_VALIDATION_RESULT_BYTES`), and a `validation/` directory that is itself a link is
  reported and nothing in it is read;
- review records are exactly the files one shared definition, `progress.review_archive_paths`,
  enumerates — `review.yaml` and its `review-<timestamp>.yaml` archives — used by the loader,
  `review.review_history` and the evidence hash alike;
- YAML is parsed with `StrictSafeLoader`: safe constructors, duplicate keys refused, deep
  nesting reported (ADR-025, ADR-029);
- the service-port files are read with a 16-byte bound.

**Fixed since round 12 (findings E2 and E3, High).** Validation result files, and every
`review*.yaml` beyond `review.yaml`, used to be read without any of the bounds above: a FIFO
hung `validate`, `build` and the service, a link to `/dev/zero` was read until the process was
killed, and a stray unparsable `reviewer-notes.yaml` — which the loader's own check missed,
because it globbed `review-*.yaml` while `review.review_history` globbed the looser
`review*.yaml` — passed `validate` and then crashed `build` with an absolute path in the
traceback. Both record kinds now go through the same bounded reader `progress.yaml` always
used, and review records are read from the one shared list above rather than two globs that
disagreed.

## 5.10 External systems and privacy

Release one performs **no external write** and makes **no outbound request** of its own.
Every quest declares `risk.external_write: false`, every validator is registered
`network: denied`, and `tests/test_release_facts.py` fails the day a quest declares a write.
The preview-and-confirm requirements in `docs/SECURITY-AND-PRIVACY.md` are the conditions a
write-capable quest must meet before it is added, not a mechanism that runs today. No
telemetry leaves the machine.
