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
- A secret scanner runs before submission preparation.
- Logs redact configured keys and token-like values.
- Raw external-system responses are stored only under Gitignored `local-data/` and are opt-in.
- Screenshots are the one kind of evidence the scanner cannot read: it scans text, and a
  token in a picture of a terminal is invisible to it. The `PROOF.md` template every
  attempt is given ends with a **Sensitive values** section asking the participant to
  confirm the package carries no secret, customer name or private ticket content, and
  redacting an image before it goes in is their judgment. There is no automated gate
  here, and release one does not claim one.

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
- The application verifies the decision references the current attempt.
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
