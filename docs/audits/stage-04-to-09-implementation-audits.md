# Stage Audits — Stages 4 to 9

**Recorded:** 2026-09-17
**Nature: implementation self-audit, not independent review.** This is the distinction that
matters and it is stated first. Stages 0, 1, 2 and 3 were audited by an independent agent
with no knowledge of how the code was written, and the whole release was audited the same
way at Stage 10. Stages 4 to 9 were verified by the implementer against the plan's own
checklists. That is weaker, and this file exists so nobody has to infer which is which.

`CLAUDE.md` rule 7 requires an audit record per stage. This is that record, honestly labelled.

## Why these stages were not independently audited

Stages 4 to 9 were built in one continuous session under instruction to keep going without
stopping. Four independent audits were commissioned during it — Stage 1, Stage 2, Stage 3,
and the final release audit — and each took between seven minutes and nine hours to return.
Commissioning six more in sequence was not compatible with that instruction. The final Stage
10 audit covers the *product* those stages produced, and it found three blocking defects in
exactly this territory (see below), which is the honest measure of what the self-audits
missed.

## Stage 4 — Participant state and loopback service

**Verified by execution:** non-loopback bind refused (four addresses); missing, wrong and
correct tokens; cross-origin `Origin` and `Referer`; non-JSON content type; oversized body
refused before it is read; malformed and empty bodies; six attacker-shaped action IDs and six
quest IDs; four traversal shapes and a planted symlink against static serving; security
headers; token never written to disk. Transition table: nothing produces `verified` or
`needs_changes`, running a validator is not an action, invalid transitions leave the file
untouched, atomic write survives a simulated `fsync` failure with no debris.

**Found and fixed during the stage:** the origin check compared against the *configured*
port, so every same-origin request was refused once the kernel chose one.

**Missed, found later by the Stage 10 audit:** B1 — a participant with no progress file could
never create one, because every fixture began with one. B2 — the service view was a
build-time constant, so no action in the generated UI was ever enabled.

## Stage 5 — Evidence workspaces and validator framework

**Verified by execution:** unregistered IDs cannot run; six entrypoints outside the
`validators` package refused; enum values outside the allowlist and six attacker-shaped
strings refused; an unexpected parameter is an error rather than ignored; there is no string
parameter type; workspace containment against four traversal shapes and a planted symlink,
with and without write roots; every shipped validator has no write roots, no network, a
timeout and an output cap; a timeout produces `interrupted` and kills a validator that
spawned a child of its own; `inconclusive` does not qualify; output bounded and redacted; a
real run produces a schema-valid document.

**Found and fixed during the stage:** registry roots ignored the configurable participant
root, so every check read a directory that does not exist under test and came back
inconclusive.

## Stage 6 — Participant UI and interaction polish

**Verified by execution:** 31 browser-driven tests including axe-core over eleven pages with
serious and critical impacts failing; WCAG contrast computed from the tokens across twenty
pairings; four named viewports and 200% zoom with no horizontal scrolling; keyboard-only
navigation and skip-link focus; no-JavaScript browsing of the catalogue and tag pages; no
control hidden behind hover.

**Found and fixed during the stage:** three heading-outline defects; three contrast failures
in the inherited palette; and — found by axe, not by the token check — the participant
summary renders on the dark sidebar where the muted and accent colours sit at 2.58:1 and
2.91:1.

**Still open:** the eight quest states are all rendered, but `submitted` and `needs_changes`
appear only when a fixture is in those states; there is no fixture exercising all eight at
once.

## Stage 7 — Submission and reviewer integrity

**Verified by execution:** twelve routes to `verified` without a reviewer, eight refused at
load time with precise messages and two behaving as documented; approval refused without a
verification statement, with a token one, with changed evidence, and for an unsubmitted
attempt; needs-changes and reject refused without a finding; verified XP moves only on
approval; a superseded decision is archived rather than overwritten.

**Found and fixed during the stage:** the submission record changed the very hash it had just
captured, so a freshly submitted attempt read as changed-since-submission immediately.

**Missed, found later:** evidence edited *after* approval kept `verified` silently — the only
hash comparison happened inside `record_decision`. Fixed with
`progress._check_stale_approval` and four tests.

## Stage 8 — Fork updates, versioning and migrations

**Verified by execution:** a dirty working tree blocks with the command that fixes it; a
missing `upstream` remote blocks; the printed instructions create the backup branch before
anything else; no permitted Git command can rewrite history or the working tree and asking
for one raises; migrations refuse to drop an attempt or a field and carry unknown fields
forward; in-progress attempts are reported and never moved; verified work is not reported as
stale; an end-to-end test changes program-owned content in a real repository and asserts the
participant's files are byte-identical afterwards.

## Stage 9 — Documentation, hardening, release candidate

**Verified by execution:** 203 quests load and build in under a second; a page about one
entity does not grow with the catalogue; the content-error screen renders and does not
overwrite the published site.

**Found and fixed during the stage:** the content-error screen had never been rendered and
crashed on the first problem without a column number.

**Missed, found later by the Stage 10 audit:** five traceability rows were false or weaker
than the criterion, the release-note numbers were wrong, and `make check` ran none of the
browser suite so CI never exercised the accessibility claims.

## What this record is worth

Six of the defects listed above were found by the implementer. Five significant ones —
including all three blocking — were not, and were found by independent review. The pattern is
consistent enough to be the recommendation: **commission an independent audit for every
stage, and do not treat a self-audit as a substitute.**
