# Proof · base-camp-ownership-zones

Attempt: `base-attempt-004`

Written by Tom Carter with Claude (Claude Code), 11-19-2026. The choices below are Tom's, from his
answers to one question at a time; Claude wrote the code and this page from them.

## What was built

Two locks on an agent's writes, both following one set of zone rules: a write-guard that checks
each write before it happens, and an operating-system lock that refuses any write the guard never
saw.

**The zone rules** (`participant/context/zone-rules.md`, criteria 1 and 6). Four zones, each with the
folders it covers, who may write there, whether Git tracks it, and whether an agent may write there
(Tom's choice: four zones, with credentials in none, never written anywhere in the repository):

| Zone | Covers (examples) | Agent may write |
|---|---|---|
| Program | `content/`, `quest_app/`, `tools/`, `.git/`, files at the top | no |
| Participant | `participant/` | yes |
| Generated | `generated/`, `.venv/`, caches and test reports anywhere | no |
| Private data | `local-data/` | yes (Tom's choice: raw data belongs here, not next to the notes) |

A "Where does a new file go?" list of five questions lets a person place a new file from the rules
alone. The rules build on `participant/context/repository-ownership.md` from the first quest.

**The guard** (`participant/tools/zone-guard.mjs`). One tool checks and then writes, in one step
(Tom's choice), so nothing can slip in between a "yes" and the write. Its rulebook is the Zones table
in `zone-rules.md`, read fresh on every run (Tom's choice): the rules people read and the rules the
tool enforces can't disagree, and a missing or broken table refuses every write.

**How it handles a path trying to leave the folder.** It doesn't trust the text it is given. It
first has the operating system follow every `..` and every link, in order, to where the file would
*really* land, the way a mail clerk checks the address on a map rather than the envelope. Then it
compares that real path:

1. the real path must be inside the repository, or the write is refused (rule 2);
2. its zone must be in the table and allow agent writes, or the write is refused (rule 3);
3. the file is created only as a brand-new file, in a folder that already exists, and a link
   standing at the last step is never followed (rule 4). The guard steps into the checked folder,
   writes a hidden temporary file there, and then puts it in place at the real name in one step
   that refuses if anything already stands there. Nothing half-written ever appears.

So `participant/../content/notes.md` and `participant/content-link/notes.md` (a link into
`content/`) are both seen as `content/notes.md` and refused, even though their text starts with
`participant/`. Every refusal names its rule, and the guard creates nothing until every check has
passed.

**The operating-system lock (Tom's choice, added after the practice review).** The guard only
checks writes that are handed to it; an agent that saved a file directly, or a shell redirection,
would skip it. So agent commands, and the guard itself, run inside a macOS sandbox
(`participant/tools/zone-run.sh`) that refuses every file write except into the zones where an agent
may write. Its rules are made from the same Zones table (`zone-guard.mjs profile`), so there is
still one rulebook. The lock knows only folders; the guard knows the finer rules (a test-results
folder inside `participant/` is Generated). Together they cover criterion 2: a write that goes
through the guard is checked against every rule, and a write that doesn't is refused by the system
outside the agent's two zones. The lock also limits the split-second gaps: whatever another program
swaps on disk during a write, nothing the guard writes can land outside those two zones.

**Both stretch goals (Tom's choice).** A path in no zone, such as a new top-level folder, is refused,
and `zone <path>` reports any path's zone and whether an agent may write there, without writing.

## Which zone is hardest to enforce with a tool, and what a person must catch

Tom: **Private data.** The guard checks *where* a file goes, never *what is in it*. An agent could
copy a raw private file, such as a full customer email or an API response, into `participant/`, and
the guard would allow it, because `participant/` is an allowed zone. That folder is committed and
shared. Only a person reading the file would see that raw private data doesn't belong there and that
only a redacted copy may go there.

## Where the important artifacts are

All paths are under `participant/`.

- The zone rules: `context/zone-rules.md`
- The guard: `tools/zone-guard.mjs`
- The operating-system lock: `tools/zone-run.sh` (its rules from `zone-guard.mjs profile`)
- The sandbox demonstration that recorded the logs: `tools/zone-guard-demo.sh`
- Refused writes, then proof nothing was created:
  `evidence/base-camp-ownership-zones/base-attempt-004/logs/refused-write.txt`
- The same write into participant-owned folders, succeeding:
  `evidence/base-camp-ownership-zones/base-attempt-004/logs/allowed-write.txt`
- Direct writes that skip the guard, refused by the lock:
  `evidence/base-camp-ownership-zones/base-attempt-004/logs/os-lock.txt`
- Stretch goals (the zone report, and a broken or missing table):
  `evidence/base-camp-ownership-zones/base-attempt-004/logs/zone-report.txt`

## How to reproduce the behavior

From the repository's top folder:

```sh
bash participant/tools/zone-guard-demo.sh <a new logs folder>
```

It builds a throwaway sandbox in a new temp folder (Tom's choice, so nothing is ever aimed at a real
program file), runs every case below, writes the four logs and deletes only that temp folder. It
needs macOS (the lock uses `sandbox-exec`). The tools can also be run on their own:

```sh
node participant/tools/zone-guard.mjs zone <path>
node participant/tools/zone-guard.mjs profile
bash participant/tools/zone-run.sh --root <a sandbox folder> \
  node participant/tools/zone-guard.mjs write <path> "<text>" --root <a sandbox folder>
```

## What was tested or validated

All recorded on 11-19-2026 at 11:10 AM with Node 22.23.3, at commit 7084e70 with the quest-23 files
uncommitted, in a sandbox holding a copy of the zone layout (`repo/`), the real `zone-rules.md` (its
SHA-256 matches the repository's, shown in each log), and a folder outside it (`outside/`).

- **Refused writes** (`logs/refused-write.txt`, criteria 2 to 4). The same write, a `notes.md`
  holding one line of made-up notes, was tried nine ways, and all nine were refused, each naming its
  rule:
  1. into `content/` (Program);
  2. `participant/../content/notes.md` (`..` from the allowed folder into Program);
  3. `participant/../../outside/notes.md` (`..` out of the repository);
  4. through a link in `participant/` that leads outside the repository;
  5. through a link in `participant/` that leads into `content/`;
  6. onto a link standing where the new file would go, pointing at a file outside that didn't exist;
  7. into `generated/`;
  8. into a folder in no zone;
  9. a new file at the top of the repository.

  The whole sandbox, inside and outside the repository copy, was fingerprinted before and after
  with `participant/tools/workspace-fingerprint.mjs` (from quest 22: every entry's kind, mode, owner,
  size, contents and link target). The two lists are identical, and no `notes.md` or `escape.md` file
  exists anywhere: no file, empty file or partial file was created.
- **Allowed writes** (`logs/allowed-write.txt`, criterion 5). The same write succeeded into
  `participant/`, `participant/notes/` and `local-data/`. Writing `participant/notes.md` again with
  different text was refused (rule 4: the guard never overwrites), and the file still holds its first
  text. Only those three new files appeared; every other entry is unchanged.
- **The operating-system lock** (`logs/os-lock.txt`, criterion 2). Ten direct writes that never went
  through the guard were refused by macOS itself ("Operation not permitted"): into `content/`,
  appending to a program file, a new top-level file, into `generated/`, a new folder in no zone,
  `..` out of the repository, through each of the two links, a copy into `content/`, and deleting a
  program file. Direct writes into `participant/` and `local-data/` worked. A direct write into a
  test-results folder inside `participant/` got past the lock, which knows only folders, and the
  guard, run inside the lock, refused the same write (Generated). The guard wrote into
  `participant/` from inside the lock and refused `content/`. Only the four allowed files appeared;
  the rest of the sandbox's fingerprint list is unchanged.
- **Stretch goals** (`logs/zone-report.txt`). `zone` reported the right zone for nine paths,
  including a test-results folder inside `participant/` (Generated) and the paths through both links.
  A table with an invalid value, and then a missing table, each refused a write that is normally
  allowed, and nothing was created.
- The real repository was never written by the demonstration: only the evidence logs changed, and
  the demo-app's `orders.json` is unchanged (`git diff --quiet`).
- The demonstration checks every result against the expected exit code (1 refused, 0 written) and moves the logs into place only if all of them, and every fingerprint, came out as
  expected.

## Remaining limitations

- **It checks where, never what.** A raw private file copied into `participant/` is allowed (see
  Tom's answer above). A person, and the quest app's secret scan, must catch that.
- **The lock covers commands started through `zone-run.sh`.** An agent whose own file tools write
  without going through a command (an editor tool built into the agent) is outside it; those tools
  need the same rule in the agent's own settings (deny writes outside `participant/` and
  `local-data/`). And the lock knows only folders: inside them, a direct write that skips the guard
  can still land in a Generated folder such as `participant/tests/playwright/test-results/`.
- **It only creates new files.** Editing, renaming and deleting are outside this quest; a full guard
  would check those the same way.
- **Another program changing things during a write.** The guard steps into the checked folder
  before creating the file, so swapping a folder on the way for a link can't redirect the write. A
  program changing files in that same folder at the same split second (replacing the guard's hidden
  temporary file, or the rulebook) could still change what is written, within the agent's two zones:
  the lock keeps it from landing anywhere else. If the checked folder is moved meanwhile, the guard
  stops and says so (exit 1).
- **Capital letters.** macOS treats `Content/` and `content/` as the same folder. The guard resolves
  folders to their real spelling and compares names without regard to capitals, so
  `participant/.ds_store` is still the Generated `.DS_Store`. On a system where capitals do matter
  (Linux), a differently-capitalised name is treated as the listed one: that can refuse a write
  that would be fine there, or, if a folder such as `LOCAL-DATA/` exists, treat it as Private data.
- **macOS only.** The lock uses `sandbox-exec`, which Apple marks as deprecated but still ships. On
  Linux the same profile idea would need another tool (bubblewrap, Landlock).
- **The demonstration script** needs macOS, bash, Node and the usual Unix tools. It
  replaces a log only if it is an ordinary file, and puts the logs in place only if every step
  worked.

## Sensitive values

No secret, token, password, customer name or real ticket content is here. The note text is made up,
the sandbox lives in a temp folder that is deleted afterwards, and every path in the logs is relative
to the sandbox, never showing this computer's folders.
