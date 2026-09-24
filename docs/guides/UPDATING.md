# Taking Upstream Changes

## The promise

You can take improvements to the curriculum and keep everything you wrote. That holds
because program-owned and participant-owned files live in separate top-level directories and
nothing upstream touches yours.

## First, name where updates come from

A fresh clone has one remote, `origin`, pointing at wherever you cloned from. Every command
below fetches from `upstream`, which nothing creates for you:

```bash
git remote add upstream https://github.com/beekeeper-lab/golden-thread-quest.git
```

Until you do, `make update-check` reports `[fail] No 'upstream' remote is configured.` and
prints that command. That is the check working, not a broken clone.

## Before you merge

```bash
make update-check
```

It checks the things that make an update safe and prints the commands. **It runs no merge.**
Merging on someone else's repository, with their uncommitted work in it, is not a decision
an application should make.

A dirty working tree is a hard stop, not a warning. Merging on top of uncommitted work is how
people lose an afternoon.

## Doing it

The printed sequence creates the backup branch first, so there is always one command that
puts everything back:

```bash
git branch backup/pre-update-<timestamp>
git fetch upstream
git log --oneline HEAD..upstream/main
git merge upstream/main
make validate-content
make migrate      # only if validate-content says your progress schema is old
```

If it goes wrong: `git merge --abort`, or `git reset --hard backup/pre-update-<timestamp>`.

## What does not change

**Your in-progress attempts stay on the quest version you started.** If a quest moves from
version 2 to 3 while you are working on it, you keep working against version 2 and the quest
page tells you a newer one exists. Advancing it silently would change the acceptance criteria
under you mid-task.

**Verified work stays verified.** A newer quest version does not revoke an approval. If the
text changed materially, the build says the approval may be stale and a reviewer can decide.

## Conflicts

A merge conflict under `participant/` means you and upstream changed the same file — usually
a file the curriculum ships as a starter and you then edited. Yours is the one that matters:

```bash
git checkout --ours participant/<the file>
git add participant/<the file>
```

Read the incoming version first (`git show upstream/main:<path>`) in case it contains
something you want.

## Migrations

If the shape of `participant/progress.yaml` changes, `make update-check` says what a
migration would do before anything runs. After the merge, with your work committed, apply it:

```bash
make migrate
```

Until you do, the application refuses to load the older file and says so, rather than reading
it in a shape it no longer describes. A file written by a newer version of the application is
refused the same way, so an older checkout cannot rewrite it in the old shape.

Migrations validate before and after, and carry unknown fields forward rather than deleting
data written by a newer version you might go back to. If your state does not load after
migrating, the original file is put back.

What is actually guarded: a migration step that drops a *top-level* field (`selected_track`,
`focus_tags`, and so on) or that removes one of your *attempt IDs* from `attempts` is refused
outright, before anything is written. That check does not look inside an attempt — a
migration that renames or restructures a field nested inside one is not stopped by it, because
a legitimate migration sometimes needs to do exactly that (moving a field to a new name is not
losing it). The guard exists for the failure mode migrations actually have: a bug that drops
a whole quest or an entire top-level section, not one that reshapes a field within it.

If `make update-check` says a merge is in progress, finish it or undo it before anything else:
resolve each conflict and `git commit`, or `git merge --abort`. Committing everything at that
point would commit the conflict markers.
