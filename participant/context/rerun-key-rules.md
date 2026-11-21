# Rerun key rules

How the safe-rerun workflow (`participant/evidence/base-camp-safe-rerun/base-attempt-004/scripts/rerun.py`)
decides that an item is one it has seen before. Written by an AI assistant (Claude) at Beau Brown's direction.

## The rule

An item's key is two parts joined by a colon:

    <source name>:<the ID the source system gave the item>

Example: the input file says its source is `intake`, and an item carries `source_id: REQ-0007`.
Its key is `intake:req-0007`.

- The **source name** comes from the input file's `source` field. It says which system the items came from, so
  that `REQ-0007` from one system and `REQ-0007` from another get different keys.
- The **source ID** is assigned once, by the system the item came from, when the item is first made there. The
  workflow reads it. It does not make one up.

Each part is tidied in two ways before joining: white space at the ends is removed (spaces, tabs, line breaks
and the other characters Unicode counts as white space), and the letters A to Z are lower-cased. So `REQ-0007`, `req-0007` and ` Req-0007 ` are one key. Nothing else is folded: `REQ-7` and
`REQ-0007` are two keys, and so are `a.b` and `ab`.

Each part must start with a letter or digit and may hold the letters a to z (either case), the digits 0 to 9,
dash and underscore. An ID may also hold a dot. Each part may be at most 100 characters. Other characters are
not accepted: accented letters, look-alike characters such as `ß` or `①`, a colon, a slash, a space or
line break inside the ID. The reason is the reflection question in the quest. Unicode has rules that treat some different
characters as the same, and using them would let two different IDs land on one key. Refusing them means that
cannot happen through tidying. No colon also means a key splits into its two parts in one way, and no line
break means a key is safe to print on one report line.

## What the key does not depend on

| Not used | Why | Shown by |
|---|---|---|
| Title | Titles get edited. If the title were in the key, a retitled item would look new and be created a second time. A changed title is treated as a change to the same item. | `logs/retitled-run.txt`, test `test_title` |
| Body | Same reason. A body edit is an update to the record with that key. | `logs/changed-input.txt` |
| Input filename or folder | Files get renamed, moved and re-exported. The workflow opens the file it is given and makes no other use of its name. | The recorded runs use three different input filenames against one store; test `test_filename_or_folder` |
| Position in the file | Exports get re-sorted. | test `test_order_of_items` |
| Time or date of the run | It differs on each run, so a key built from it would never match. `rerun.py` has no code that reads the clock. | `logs/later-run.txt` (the same input run again 30 minutes after the others: 10 skipped) and test `test_run_time` (a rerun with the clock set 400 days ahead). |
| The simulated system's record ID (`SIM-0001`) | That is handed out when a record is created, so it cannot be known before the lookup. It is stored beside the key. | |

The key does depend on the input's `source` field. The next sections say what guards that.

## How a run uses the key

1. Work out every item's key before writing anything.
2. Look the key up in the store.
   - No record has it: **create** one.
   - A record has it, and title and body are the same: **skip**, and say why.
   - A record has it, and title or body differs: **update** that record in place. It keeps its record ID, and its
     revision number goes up by one.
3. Report one line per input item, then the counts.

Whether an item changed is decided by comparing its title and body with the stored record. (The plan was to
compare a content fingerprint. Comparing the fields directly does the same job here, because the simulated store
returns the whole record.) Fields other than title and body are not stored and not compared.

## When a key cannot be trusted

The workflow refuses the item and writes nothing for it. The run goes on with the other items and ends with
exit code 2.

- **No usable ID**: the `source_id` is absent, empty, only spaces, or not text. No key is invented from the
  title or anything else.
- **An ID that breaks the character or length rule above.** The ID is not echoed in the report. The item is named
  by its position in the input.
- **A collision**: two or more items in one input have the same key, and they differ in title or body, or one
  of them has a title or body that is missing, not text, or cannot be saved. The usable ones are refused with a
  line naming the other positions, and the unusable one is refused for its own reason. If a record with that key
  is already in the store, it is left as it is. Picking a winner would be a guess, and the loser's content would
  be lost without anyone being told.

Items with the same key and the same title and body are treated as one item listed more than once: processed
once, and each repeat is reported as skipped.

A source name the store has no records from is a special case. If the store already holds records, the whole
run is refused before any write, and the message names the source names the store does have. The usual cause is
the same system exported under a new name (say `intake`, then `intake-v2`), which would give every item a new
key and create all of them again. If the source really is new, the person running it adds `--new-source`.
Shown in `logs/source-change-run.txt`.

A second check covers what that one misses. Before any write, the workflow looks at each item it is about to
create. If a record under another source name has the same ID, the same title and the same body, the whole run is
refused. That is what the same item exported under the wrong source name looks like, whether the wrong name is
new to the store or one it already knows. Shown in `logs/relabel-run.txt`. If two sources really do hold the
same item, the person running it adds `--same-item-other-source-ok`. The same ID with different content under
another source is not stopped, because two systems may both number their items from 1.

The whole run is also refused before any write (exit code 1) if the input's source name is missing or breaks the
rule above, if the input file is not JSON or gives a field name twice, or if the store file fails its checks
(not JSON, a field name given twice, wrong shape, two records with one key or one record ID, a key or record ID of the wrong form, or a
next record number that is not above the highest record ID).

## What a collision would look like, and what this rule cannot see

Seen: different items with one key **in the same input file**. The report shows a `refused` line for each of
them (see `logs/collision-run.txt`).

Not seen by this workflow (known so far; there may be others):

- **The source reuses an ID over time.** If `REQ-0007` is closed and the source later gives `REQ-0007` to a
  different piece of work, a later run sees a known key with new content and updates the old record. From inside
  the workflow this cannot be told apart from an edit. The sign would be an `updated` line that lists both title
  and body for an item nobody edited.
- **Two exports labelled with the same source name that come from different systems.** Same effect as above.
- **A renamed source whose items were all edited on the way.** The second check matches on ID, title and body
  together. One unchanged item is enough to stop the run. If every item differs from its record under the old
  name, nothing matches and they are all created under the new name (with `--new-source` if the name is new to
  the store, with no flag if the store knows it). The sign would be a run where `created` equals the number of
  input items.
- **Both checks waved through.** A person who adds `--new-source` and `--same-item-other-source-ok` without
  looking gets every item created again. Neither check does anything on a store with no records, where there
  is nothing to double.
- **One real item entered twice in the source under two IDs.** Two keys, two records. The key rule treats what the
  source says as the truth about identity.
- **Two spellings a person would call the same ID**, such as `REQ-7` and `REQ-0007`, or `REQ_0007` and
  `REQ-0007`. These are two keys.
- **A real source whose IDs use accented or other non-English letters.** Those items are refused, not created.
