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
| Response headers | Content Security Policy `default-src 'none'; script-src 'self'; style-src 'self'; img-src 'self' data:; form-action 'self'; base-uri 'none'; frame-ancestors 'none'`, `X-Content-Type-Options: nosniff`, `Referrer-Policy: no-referrer`, `Cache-Control: no-store` | No remote script, style or frame; no framing by another page |
| Catch-all | Both handlers answer every exception with a status and the exception type, never a traceback | A traceback would print absolute paths and leave the client with no answer after a change had landed |

**Open (round 12, C1, Blocking).** The `Referrer-Policy: no-referrer` header and the origin
check conflict: Chromium sends `Origin: null` on a form post from such a page, and the check
refuses it. At `16a0b03` every browser form is refused and only the CLI changes state. The fix
is in progress on `fix/r12-web`.

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

**Open (round 12, E1, Blocking).** Three writes do not yet meet this rule. The activity line
is appended with a plain `open("a")`, which follows a symbolic link out of `participant/`, and
a FIFO named `ACTIVITY.md` hangs the action while it holds both locks. Validation results are
written into a `validation/` directory that can itself be a symbolic link leading outside the
package. The review archive is written with a plain `write_text`. Fixes are in progress on
`fix/r12-io`.

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
output and of every check field, schema validation of the result. They bound what a
validator does through the `Workspace` and the process. They are **not** an operating-system
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
  participant cannot switch the check off with the pragma. A file it cannot read, and a link
  leading outside the package, count as findings: the scan cannot clear what it may not read.
  Images and archives are skipped, which is why a screenshot is not scanned (a known
  limitation).
- **Redaction.** Validator output and every free-text check field pass through
  `redact_text` before they are stored or shown. Error messages replace path-shaped text with
  `<path>`.

**Why a gate and not a report.** A false positive costs the participant a minute. A missed
credential costs a rotation. The scan is a safety net, and the documents say so: widening the
detectors is deferred until there is a corpus to measure false positives against (D10).

**Open (round 12, E7, Medium).** Redaction runs after truncation, so a token cut at the
truncation boundary can be stored in clear.

## 5.8 Review integrity

- `verified` is re-derived from the review record on every load; an attempt that claims it
  without a matching approval is refused as an integrity error (Part 3, Section 3.5).
- An approval needs a verification statement; a request for changes needs a finding.
- An approval of evidence whose hash or proof-file digests changed since submission is
  refused unless the reviewer acknowledges it; after approval, a later change raises a
  warning that the approval may be stale.
- Reviewer identity is a display name plus Git history, not a signature (ADR-030). The
  limitation is stated in the reviewer guide and the interface.

**Open (round 12, E4, Medium).** A hand-edited `state: submitted` with no `submission.yaml`
loads and can be approved, which skips the secret-scan gate that submission applies.

## 5.9 Hostile repository files

A reviewer runs the application against a participant's repository, so participant files are
treated as hostile input:

- content discovery reads only regular files inside the content tree (a link to `/dev/zero`
  or a FIFO is refused);
- `progress.yaml`, `submission.yaml` and `review.yaml` are read through
  `safe_io.read_bounded_bytes`: an ordinary file under 2,000,000 bytes, checked with `stat`
  before reading;
- YAML is parsed with `StrictSafeLoader`: safe constructors, duplicate keys refused, deep
  nesting reported (ADR-025, ADR-029);
- the service-port files are read with a 16-byte bound.

**Open (round 12, E2 and E3, High).** Validation result files and `review*.yaml` files other
than `review.yaml` are read without that bound; a FIFO hangs `validate`, `build` and the
service, and a stray unparsable `reviewer-notes.yaml` crashes `build`. Fixes are in progress
on `fix/r12-io`.

## 5.10 External systems and privacy

Release one performs **no external write** and makes **no outbound request** of its own.
Every quest declares `risk.external_write: false`, every validator is registered
`network: denied`, and `tests/test_release_facts.py` fails the day a quest declares a write.
The preview-and-confirm requirements in `docs/SECURITY-AND-PRIVACY.md` are the conditions a
write-capable quest must meet before it is added, not a mechanism that runs today. No
telemetry leaves the machine.
