# Proof · jira-build-index

Attempt: `jira-attempt-009`

## How this was made

An AI assistant (Claude) wrote the generator, the made-up records, the tests, the recording scripts and this
file, at the participant's direction. The work was done in small steps, each shown to the participant before
the next.

What the participant did themself:

- Chose which records to index: the `stories/` folder, filled out with made-up stories, and not the older
  copies in `assigned/` and not their real sandbox story.
- Agreed the design before anything was written: the issue id as the identity, a gap marked and never guessed,
  every file accounted for, and no build time in the catalog.

Nothing here contacts Jira. Every record is made up, so nothing is redacted.

Statements below are marked **recorded** (the log `logs/index-run.txt` shows it), **tested** (a passing test
shows it, with the output in `logs/tests.txt`) or **not assessed**.

## Where the records came from

The participant had one story record in the reader's format, the sample from the `jira-read-story` quest. One
record cannot show a lookup by status or by assignee, so twelve more were made.

They were made by the story reader that quest approved, called unchanged by `scripts/make_records.py` and
handed a made-up Jira answer for each story. So each record is what that reader writes, and none was typed by
hand. The twelve are awkward on purpose: two with no assignee in Jira, one whose record has no status, one with
no assignee line at all, one moved to another project so that its key is `OPS-4`, one with a title worded as an
instruction, one with a title full of table characters, and one with a very long title.

## How I know every record was indexed (criterion 2)

Four ways, each independent of the one before.

1. **The generator accounts for every file.** Each `.md` file in the records folder ends in exactly one of
   three places: indexed as a row, reported as a repeat of a story already indexed, or listed as not indexed
   with a reason. The build adds the three counts and stops, writing nothing, if they do not equal the number
   of files found. **Recorded**, part 1: `accounted for: 13 of 13`.
2. **The generator counts what it is about to write.** After the catalog text is made it counts the story rows
   in it and stops if that is not the number indexed. So a row lost in the writing is caught as well as a file
   lost in the reading.
3. **The catalog shows the sum.** Its second section reads `13 + 0 + 0 = 13`, so a reader can see it.
4. **The recording script counts separately.** It shares no code with the generator. It lists the record files
   itself, reads the rows out of `catalog.md` itself, and checks 13 files, 13 rows and 13 different ids.
   **Recorded**, part 1. This is the quest's hint, done by a second party.

"Once" is by issue id. **Tested**: a second file holding an issue id already indexed does not become a second
row. It is counted as a repeat and reported with both file names. **Recorded**, part 6: 17 files found, 15
indexed, 1 repeat, 1 not indexed, 17 accounted for.

## The acceptance criteria, one by one

1. **The catalog is generated, never hand-edited.** `catalog.md` and `catalog.json` are written only by
   `index.py build`. The header of `catalog.md` says so. The `check` command compares the files on disk, byte
   for byte, with what a build from the records would write now, so a hand edit is found. **Recorded**, part 6:
   a status was changed by hand in the catalog, the check failed, and the next build put back what the record
   says. **Tested**, including a test that the catalog in the repository is exactly what the generator writes
   from the records in the repository.
2. **Every local record appears once.** See the section above.
3. **Lookup by key, status and assignee is possible from the index.** Two ways. By reading `catalog.md`, which
   has the table and the lists "By status" and "By assignee". And by `index.py lookup`, which answers from
   `catalog.json`. **Recorded**, part 3: by key `OPS-4` (1 story), by status `In Review` (2), by assignee
   account id (4), by `unassigned` (2), by title words (1), and a lookup that finds nothing. Assignees are Jira
   account ids, because the records hold no names.
4. **A record with a missing field is listed as a gap.** The story stays in the table, with `(missing)` in the
   column, and is listed under "Gaps" with the fields it lacks. Nothing is guessed. **Recorded**, part 1: the
   two gaps among the 13 records. Part 5: a record with an empty title and no update time is added and
   reported as `no title, no last update`. `unassigned` is not a gap: the record says the story has no
   assignee. **Tested** for each of the five fields.
5. **Two builds from the same records are identical.** No time, counter or machine path is in either file.
   **Recorded**, part 1: the same SHA-256 after both builds, and the second build did not rewrite the file.
   **Tested**, including a build into another folder with the clock set five years on.
6. **Adding a record changes the index without a hand edit.** **Recorded**, part 4: a fourteenth record was
   written by the story reader, the build command was run, and the catalog had 14 rows and a different
   SHA-256. Only the build wrote to the catalog.
7. **The index is not treated as the source of truth.** The header says the records are the source of truth
   and the catalog is not. A lookup runs the check first and gives no answer from a catalog that does not
   match the records. **Recorded**, part 4: between adding the record and rebuilding, the check failed and the
   lookup refused. Each lookup answer names the record file and says to read it for what the story holds.
   Either catalog file can be deleted and rebuilt, which part 1 does.

## What was built

- `participant/skills/jira-build-index/SKILL.md` and `index.py`: the generator, with `build`, `check` and
  `lookup`. Standard library only. No network code.
- `participant/skills/jira-build-index/tests/test_index.py`: 37 tests.
- `participant/context/jira/catalog.md` and `catalog.json`: the generated catalog of the 13 records.
- `participant/context/jira/stories/20001.md` to `20012.md`: the twelve made-up records.
- `scripts/make_records.py`: makes the records by calling the approved story reader.
- `scripts/record_evidence.py`: records `logs/index-run.txt`.
- `scripts/planted_bugs.py`: puts 22 bugs into the generator one at a time and records which tests fail.

Both stretch goals were done. Text search over titles is `lookup --text`. The index age is reported by each
lookup, worked out at that moment from the file's modified time, so that no time has to be stored in the
catalog and criterion 5 still holds.

One thing was added that the quest does not ask for: `catalog.json`. The lookup reads it, because reading a
Markdown table back into data would be fragile. Both files come from the same build and both are checked.

## Where the important artifacts are

| What | Path |
|---|---|
| The generator | `participant/skills/jira-build-index/SKILL.md`, `participant/skills/jira-build-index/index.py` |
| The catalog | `participant/context/jira/catalog.md` |
| The catalog as data | `participant/context/jira/catalog.json` |
| The records | `participant/context/jira/stories/` |
| The run record | `participant/evidence/jira-build-index/jira-attempt-009/logs/index-run.txt` |
| Test output | `participant/evidence/jira-build-index/jira-attempt-009/logs/tests.txt` |
| Planted bugs | `participant/evidence/jira-build-index/jira-attempt-009/logs/planted-bugs.txt` |

## How to reproduce the behavior

From the repository root. None of these uses the network.

```bash
python3 participant/skills/jira-build-index/index.py build
python3 participant/skills/jira-build-index/index.py check
python3 participant/skills/jira-build-index/index.py lookup --status "In Review"
python3 -m unittest discover -s participant/skills/jira-build-index/tests -v
python3 participant/evidence/jira-build-index/jira-attempt-009/scripts/record_evidence.py
python3 participant/evidence/jira-build-index/jira-attempt-009/scripts/planted_bugs.py
```

The recorded log comes out the same each time, except the line saying how long ago the catalog was written.

## What was tested or validated

| What | How | Result |
|---|---|---|
| The generator | 37 unit tests, `logs/tests.txt` | all pass |
| Whether the tests notice a broken generator | 22 planted bugs, `logs/planted-bugs.txt` | all 22 caught |
| The behaviours the quest names | `scripts/record_evidence.py`, 27 checks inside `logs/index-run.txt` | all passed |

One planted bug was not caught at first. A line break in a title could split one table row over several lines,
and the test for it looked only for an injected heading or row, which the escaping had already prevented. The
test now checks that the story's row is a single line. The log shows the result after that fix.

## Remaining limitations

- **The catalog can only be as right as the records.** It never reads Jira. If a record is out of date with
  Jira, the catalog agrees with the record and both are wrong. The "last update" column is the story's update
  time in Jira as the record has it, not when the record was saved, because the record format does not hold
  that.
- **A person reading `catalog.md` directly is not protected by the check.** The file cannot know it is stale.
  Its header says how to check, and a lookup always does.
- **The check uses the generator.** It asks whether the catalog is what the generator writes now. A mistake in
  the generator would be in both, and the check would pass. The count by the recording script is the only
  check here that does not share the generator's code, and it covers the number of rows and ids, not the
  content of each row.
- **Only `.md` files directly in the records folder are records.** A record saved in a subfolder or with
  another extension is not counted and not reported. **Tested** as the intended behaviour.
- **The older copies in `participant/context/jira/assigned/` are not indexed.** They are in another format,
  matched by key and without an assignee. That was the participant's choice.
- **A repeat is not judged.** When two files hold the same issue id, the one first in name order is the row.
  The other is reported, and a person decides.
- **Assignees are account ids.** A person looking for "their" stories needs their account id.
- **Titles are cut at 90 characters in `catalog.md`.** The whole title is in `catalog.json` and in the record.
  A title search uses the whole title.
- **The index age is the file's modified time on this machine.** After a fresh clone that is the checkout
  time.
- **Not assessed**: very large record sets. The generator reads every record on each build, check and lookup.
  With 13 records that takes a fraction of a second.
- **All records are made up.** The generator was not run on records saved from a real Jira.

## Reflection: what would make the index disagree with the records without anyone noticing?

Anything that changes one side while nobody runs the comparison.

The plainest case is a record changing after the build. A story is saved again with a new status, and the
catalog still shows the old one. The generator can detect that, but only when asked. Someone who opens
`catalog.md` in an editor or a browser, which is the very use it was made for, is asking nothing. The file
looks exactly as trustworthy stale as fresh. That is why the header says to check, why the lookup command
refuses a stale catalog, and why none of that is enough for a person who just reads the page.

The quieter cases are the ones where the comparison is run and still says yes:

- **A record the generator never looks at.** Saved in a subfolder, or with a different extension. It is not in
  the count, so the counts agree.
- **A file listed under "not indexed" or "repeat".** It was noticed by the tool and reported at the bottom of
  the catalog. Whether a person reads the bottom is another matter.
- **A fault in the generator itself.** The check compares the catalog with the generator's own answer. If the
  generator read the wrong field, the check would agree with it every time.
- **A value that is cut or escaped.** A long title is shortened in the table. Two stories that differ only
  after the ninetieth character look the same there.

What these have in common is that a count can agree while the content does not. Counting records and rows, as
the hint says, shows that nothing was lost. It does not show that what was kept is right. The honest position
is the one in the catalog's header: use it to find a record, then read the record.

## Sensitive values

- No credential is in any file. Nothing here connects to Jira or needs a token.
- No real Jira data is in any file. Every story, project and site is made up.
- No personal name or email address is in the records or the catalog. People are made-up account ids.
- The logs hold no home-folder path. The temporary folder used in parts 4 to 6 is shown as `COPY`.
