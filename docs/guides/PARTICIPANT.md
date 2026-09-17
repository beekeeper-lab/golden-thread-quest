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

`make serve` builds the site and starts a service bound to `127.0.0.1` only. It prints the
address to open. It does not print a token — the pages it serves carry one, substituted as
they are served, so it never reaches a file.

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
| Locally validated | You, once the required checks have passed |
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
   `participant/evidence/<quest>/<attempt>/` with a `PROOF.md` template, and your progress
   file is created if you did not have one.
3. **Do the work in your repository**, not in the application.
4. **Fill in `PROOF.md`.** It asks what you built, where the artifacts are, how to reproduce
   the behavior, what you validated and what remains. A reviewer should not have to hunt.
5. **Run the checks.** A failing check is never a failed quest — it tells you what to fix,
   and your work is untouched.
6. **Mark the evidence ready.**
7. **Record local validation.** This is a button. The state means "I have run the required
   checks and they qualify", and the application refuses it if the results do not support
   that. It comes *before* submitting, not after.
8. **Submit for review.**
9. **Commit and push yourself:**

   ```bash
   git switch -c evidence/<quest-id>
   git add participant/
   git commit -m "Evidence for <quest-id>"
   git push -u origin evidence/<quest-id>
   gh pr create --fill
   ```

   The application runs none of these. Pushing your evidence is a claim that the work is
   finished and ready for someone else's attention, and that claim is yours to make.

## What the application writes

Under `participant/`, only these, and only through documented actions:

- `participant/progress.yaml` — your state, written atomically and validated first
- `participant/evidence/**` — evidence packages, validation results, submission and review records
- `participant/ACTIVITY.md` — one line per change it made, for you to read

It also rewrites `generated/` on every action. That directory is machine-owned, gitignored
and disposable: `make build` recreates it from your content and your progress.

It never commits, pushes, merges or cleans. `make clean` removes generated output and
refuses to touch anything of yours.

## If something goes wrong

**An action is refused.** The page says so at the top, in red, with the reason. Nothing
changed, and the reason names what to fix.

**A check fails.** Read the findings; they are ordered with the most serious first and each
says what it observed and what to do. Your state does not change.

**A reviewer asks for changes.** Your evidence is preserved exactly as it was. Resume the
quest and address the findings.

**Your work looks lost.** It is in Git. `git status`, `git stash list`, `git reflog`.

**The application refuses to start.** Content that does not validate is never published, so
a broken curriculum stops the build rather than reaching you. `make validate-content` names
the file, field and fix.
