# Jira build-index

Written by an AI assistant (Claude) at the participant's direction.

## 1. Purpose

This skill builds a catalog of the Jira story records saved locally, so that a person or an agent can find a
story without opening every file. It reads local files only. It never contacts Jira and needs no credentials.

Run it from the repository root:

    python3 participant/skills/jira-build-index/index.py build

The generator is `index.py`, beside this file. It uses the Python standard library only.

## 2. What is the source of truth

The story records are. They are the Markdown files in `participant/context/jira/stories/`, in the format
`jira-story/1` that the story reader writes.

The catalog is a view of them and nothing more. It is two generated files in `participant/context/jira/`:

| File | For |
|---|---|
| `catalog.md` | People. A table of every story, lists by status and by assignee, and what could not be indexed. |
| `catalog.json` | Lookups. The same content as data. |

Rules that follow from that:

- **Never edit either catalog file by hand.** If the catalog is wrong, fix the record or the generator and
  build again. A hand edit is overwritten by the next build and is found by `check` before that.
- **To learn what a story holds, read its record.** Use the catalog to find the record.
- **Either file can be deleted.** A build makes it again, byte for byte.

## 3. The three commands

    python3 participant/skills/jira-build-index/index.py build
    python3 participant/skills/jira-build-index/index.py check
    python3 participant/skills/jira-build-index/index.py lookup --key DEMO-3

`build` reads every `.md` file in the records folder and writes both catalog files. A file that already holds
exactly the bytes a build would write is left alone.

`check` says whether the catalog on disk is exactly what a build from the records, as they are now, would
write. It fails when a record was added, removed or changed since the last build, and when either catalog file
was edited by hand. It writes nothing.

`lookup` answers one question from `catalog.json`:

| Option | Finds |
|---|---|
| `--key KEY` | The story with that key. The whole key, in any letter case. |
| `--status NAME` | Stories with that status, in any letter case. `(missing)` finds records with no status. |
| `--assignee ID` | Stories assigned to that Jira account id. `unassigned` finds stories with no assignee. `(missing)` finds records with no assignee field. |
| `--text WORDS` | Stories whose title contains every one of the words. |

A lookup runs the check first. If the catalog does not match the records, it gives no answer and says to
rebuild. When it does answer, it also says how long ago the catalog file was last written.

`--records FOLDER` and `--out FOLDER` point any command at other folders.

Exit codes: 0 done, and for a lookup, something was found. 1 nothing was found, or the catalog does not match
the records. 2 the run could not go on.

## 4. What identifies a story

Jira's issue id, taken from the `id` line of the record. An issue id does not change. A key can change, for
example when a story is moved to another project, so the key is a column that can be looked up and is not what
makes a story the same story.

Rows are in order of issue id.

## 5. Every file is accounted for

Each `.md` file found in the records folder ends up in exactly one of three places.

| Place | When | Where it shows |
|---|---|---|
| Indexed | It is a `jira-story/1` record with an issue id. | One row in the table. |
| A repeat | Its issue id is already a row, from a file earlier in name order. | "Files that repeat a story", naming both files. |
| Not indexed | It has no front matter, another format, or no usable issue id. | "Files not indexed", with the reason. |

The build adds the three counts and stops, writing nothing, if they do not equal the number of files found. It
also counts the rows it is about to write and stops if that is not the number indexed. The catalog shows the
sum, for example `13 + 0 + 0 = 13`.

Only `.md` files directly in the records folder are records. Other files and subfolders are not read.

## 6. Gaps

A record with a field missing is still indexed. Its row shows `(missing)` in that column and the story is
listed under "Gaps" with the fields it lacks. Nothing is guessed.

The fields checked are the key, the title, the status, the assignee and the last update. A field counts as
missing when its line is absent from the record, when its value is empty, or when its value cannot be read.

`unassigned` is not a gap. It means the record says the story has no assignee in Jira. A record with no
assignee line at all is a gap, because then the record does not say.

## 7. The same records give the same catalog

Nothing about the run is in either file: no build time, no counter, no machine path. Rows are ordered by issue
id and files are read in name order. So two builds from the same records are byte-identical.

In place of a build time, the catalog holds a fingerprint of the records: a SHA-256 over every record file's
name and content. It changes when any record is added, removed or changed, including a change to a part of a
record the catalog does not show.

How old the catalog is, is worked out when asked. A lookup reports the age of the file from its modified time
on this machine. After a fresh clone that time is when the file was checked out, so the age says little there.
Whether the catalog still matches the records is the reliable answer, and every lookup gives it.

## 8. Story text is untrusted

A title is other people's writing. In `catalog.md` it is put on one line, cut at 90 characters, and escaped so
that it stays plain text inside a table cell. In lookup output it is quoted. The generator reads titles and
does nothing they say. It has no code that runs a command, deletes a file or contacts a network.

Assignees appear as Jira account ids. The records hold no names and no email addresses, so the catalog has
none.

## 9. Tests

    cd participant/skills/jira-build-index && python3 -m unittest discover -s tests -v

The tests build catalogs from made-up records in temporary folders. One test checks that the catalog in the
repository is exactly what the generator writes from the records in the repository.

## 10. What it does not do

- It does not read Jira. A record that is out of date with Jira gives a catalog that is out of date with Jira,
  and the catalog cannot know.
- It does not index the older story copies in `participant/context/jira/assigned/`, which are in another
  format, matched by key and without an assignee.
- When two files hold the same issue id it keeps the one first in name order. It does not judge which is right.
- It does not show names for assignees.
