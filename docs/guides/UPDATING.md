# Taking Upstream Changes

## The promise

You can take improvements to the curriculum and keep everything you wrote. That holds
because program-owned and participant-owned files live in separate top-level directories and
nothing upstream touches yours.

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
migration would do before anything runs. Migrations validate before and after, refuse to drop
an attempt or a field, and carry unknown fields forward rather than deleting data written by
a newer version you might go back to.
