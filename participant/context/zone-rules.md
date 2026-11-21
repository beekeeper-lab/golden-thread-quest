# Zone rules

Which part of this repository belongs to whom, for the base-camp-ownership-zones quest. People
read this file to know where a file goes; the write-guard (`participant/tools/zone-guard.mjs`)
reads the **Zones** table below as its rulebook, so the sign on the door and the keycard reader
can never disagree. Decisions by Tom Carter; wording drafted with Claude (Claude Code),
11-19-2026. It turns `participant/context/repository-ownership.md` (the same zones, with the
actors that work here) into rules a tool enforces.

**Credentials belong in no zone: they are never written anywhere in this repository.** They live
in environment variables, the GitHub CLI's keychain login, or a password manager.

## Zones

| Zone | Covers | Who may write | Git | Agent may write |
|---|---|---|---|---|
| Program | `content/` `schemas/` `quest_app/` `templates/` `assets/` `validators/` `docs/` `tests/` `tools/` `scripts/` `fixtures/` `vendor/` `prototype/` `artifacts/` `deploy/` `.github/` `.claude/` `.git/` `*` | Nobody here. Program files change only through `gtq update`; Git's own folder only through Git commands | tracked | no |
| Participant | `participant/` | Tom, an agent working for Tom, and the quest app (`progress.yaml`, `ACTIVITY.md`, `evidence/`) | tracked | yes |
| Generated | `generated/` `generated.building/` `generated.previous/` `generated.lock` `.venv/` `golden_thread_quest.egg-info/` `participant/.progress.lock` `.claude/worktrees/` `**/__pycache__/` `**/node_modules/` `**/test-results/` `**/playwright-report/` `**/.pytest_cache/` `**/.ruff_cache/` `**/.mypy_cache/` `**/dist/` `**/.DS_Store` | Only the tools that build them (`gtq start`, `make build`, `uv`, Playwright, Python). Safe to delete and rebuild | ignored | no |
| Private data | `local-data/` `.claude/settings.local.json` | Tom, his tools, an agent working for Tom, and the quest app's runtime files. Raw data from outside systems goes here, never into `participant/`; only a redacted copy may go there | ignored | yes |

How to read **Covers**:

- `content/` is a folder at the top of the repository and everything inside it.
- `generated.lock` is that one file at the top of the repository.
- `participant/.progress.lock` is that one file at that path.
- `*` is any *file* sitting directly in the top folder (`README.md`, `Makefile`, `.gitignore` …).
  It does not cover folders: a new top-level folder belongs to no zone until it is added here.
- `**/__pycache__/` is a folder with that name *anywhere*, with everything inside it.
  `**/.DS_Store` is a file with that name anywhere.

When more than one entry matches a path, the most specific wins:

1. a `**/` entry (a cache is generated wherever it sits, even inside `participant/`);
2. otherwise the longest matching path (`participant/.progress.lock` beats `participant/`,
   `.claude/worktrees/` beats `.claude/`);
3. otherwise `*`.

Names are compared without regard to capital letters, because macOS treats `.DS_Store` and
`.ds_store` as the same file. The same entry listed twice (in any capitals) makes the table broken,
and so does a line inside the table that isn't a table row; the table ends at a blank line.

## Where does a new file go?

1. Is it a password, token, key or other credential? **Not in this repository.** Stop.
2. Is it raw data from an outside system (an API response, a full transcript, a tracker export)?
   **`local-data/`.** A redacted copy may go into `participant/` if a quest needs it.
3. Is it made by a tool and can it be made again (build output, caches, test reports)? Let **the
   tool** write it in its own Generated folder. Nobody writes there by hand.
4. Is it your own work: notes, rules, tools, tests, evidence? **`participant/`.**
5. Anything else, including a change to a curriculum or app file: it belongs to the Program.
   **Don't write it.** Raise it with the program maintainers instead.

Run `node participant/tools/zone-guard.mjs zone <path>` to have the guard say which zone a path
is in and whether an agent may write there.

## How the guard decides

1. **It resolves the path first.** The operating system follows every `..` and every link, in
   order, to where the write would *really* land. Comparing the text it was given is how `..` and
   links get through.
2. **The real path must be inside the repository.** Anything outside is refused.
3. **It looks up the real path's zone in the table above.** No zone, or a zone where
   **Agent may write** is `no`, means refused. If the table is missing or broken, every write is
   refused.
4. **It writes only a brand-new file**, into a folder that already exists. It never overwrites,
   never creates folders, and never follows a link at the last step. It steps into the checked
   folder before creating the file, so the folder can't be swapped between the check and the
   write. It writes into a hidden temporary file first and then puts it in place in one step, so a
   half-written file never appears. A refused write leaves nothing behind, not even an empty file.
5. **Every refusal names the rule that refused it.**

## The second lock: the operating system

The guard checks only the writes handed to it. So agent commands, and the guard itself, run inside
a macOS sandbox, `bash participant/tools/zone-run.sh <command>`, that refuses **every** file write
except into the entries of zones where **Agent may write** is `yes`. Its rules are made from the
Zones table above (`node participant/tools/zone-guard.mjs profile`), so this file stays the only
rulebook. The lock knows only those folders; the guard knows the finer rules inside them (a cache
or test report in `participant/` is still Generated). A write that skips the guard is refused by the
system outside the agent's zones; a write through the guard is checked against every rule.
