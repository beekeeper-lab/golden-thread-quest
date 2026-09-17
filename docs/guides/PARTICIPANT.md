# Participant Guide

## What this is

A local application that presents a curriculum, helps you assemble credible evidence that
you did the work, and keeps a truthful record of what a reviewer has confirmed. Everything
it knows lives in ordinary files in your own repository. It reads them and writes a narrow
set of them; it does not own them.

## Getting started

```bash
make setup
source .venv/bin/activate
make serve
```

`make serve` builds the site, starts a service on `127.0.0.1` only, and prints a token for
that run. Open the address it prints.

Without the service you can still read everything — the generated pages are ordinary HTML.
What you cannot do is change state, because nothing that changes a file happens in the
browser alone.

## The states, and who sets them

| State | Who put it there |
|---|---|
| Locked | The application, from your prerequisites |
| Available | The application |
| In progress | You |
| Evidence ready | You, asserting the proof is assembled |
| Locally validated | Registered validators, when every required one passes |
| Submitted for review | You |
| Needs changes | A reviewer |
| Verified | A reviewer |

Two totals are shown everywhere and never added together. **Claimed XP** is your own record.
**Verified XP** is only ever the result of a reviewer approving your evidence. Nothing you do
and nothing a validator returns can produce it.

## Doing a quest

1. **Read the whole quest page first.** Acceptance criteria are numbered, and a reviewer's
   findings will refer to them by number.
2. **Start it.** An evidence package appears under
   `participant/evidence/<quest>/<attempt>/` with a `PROOF.md` template.
3. **Do the work in your repository**, not in the application.
4. **Fill in `PROOF.md`.** It asks what you built, where the artifacts are, how to reproduce
   the behaviour, what you validated and what remains. A reviewer should not have to hunt.
5. **Run the checks.** A failing check is never a failed quest — it tells you what to fix,
   and your work is untouched.
6. **Mark the evidence ready**, then **submit**. Submission scans for secrets and refuses if
   it finds one.
7. **Commit and push yourself.** The application prints the exact commands and runs none of
   them. Pushing your evidence is a claim that the work is finished, and that claim is yours.

## What the application writes

Only these, and only through documented actions:

- `participant/progress.yaml` — your state, written atomically and validated first
- `participant/evidence/**` — evidence packages, validation results, submission and review records
- `participant/ACTIVITY.md` — one line per change it made, for you to read

It never commits, pushes, merges or cleans. `make clean` removes generated output and
refuses to touch anything of yours.

## If something goes wrong

**A check fails.** Read the findings; they are ordered with the most serious first and each
says what it observed and what to do. Your state does not change.

**A reviewer asks for changes.** Your evidence is preserved exactly as it was. Resume the
quest and address the findings.

**Your work looks lost.** It is in Git. `git status`, `git stash list`, `git reflog`.

**The application refuses to start.** Content that does not validate is never published, so
a broken curriculum stops the build rather than reaching you. `make validate-content` names
the file, field and fix.
