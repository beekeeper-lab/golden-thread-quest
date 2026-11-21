# Proof · jira-read-story

Attempt: `jira-attempt-007`

## How this was made

An AI assistant (Claude) wrote the reader, the converter, the fidelity check, a fake Jira, the tests, the
recording scripts and this file, at the participant's direction. The work was done in small steps, each shown
to the participant before the next.

What the participant did themself:

- Chose to take the required evidence from a local fixture and to add one real, read-only run.
- Agreed the design before anything was written: the issue id as the identity, people kept as account ids,
  and nothing about the run in the file.
- Ran the three recorded runs against their real Jira sandbox, in their own terminal, with a token the
  assistant was never shown.

Why the required evidence comes from a fixture. The quest asks for a story with a table, a list, a code block,
a custom field, a field with an unusual value and an instruction-like line. The one story in the participant's
sandbox has an empty description. Making it fit would have meant editing it in Jira, and the quest says to make
no change there. So the sample and the two required logs were made against a fake Jira holding a story built to
be awkward. The real runs were added because a fixture can hold only the fields its author thought of.

Statements below are marked **recorded against the fake** (a log shows it), **observed** (a recorded run
against the real sandbox shows it), **tested** (a passing test shows it, with the output in `logs/tests.txt`)
or **not assessed**.

## How the formatting was tested (criterion 2)

In four ways, each catching what the one before could miss.

**1. With the ugliest description that could be built.** The fixture story `UGLY-7` has 21 blocks of 12 kinds.
Each part was chosen because it breaks a careless converter:

- a table whose cells hold a list, inline code and a `|` character, which is what divides columns in Markdown
- a code block holding a line of three backticks, which is what ends a Markdown code block
- a list inside a list, a numbered list that starts at 3, and a checklist
- plain text typed to look like Markdown: `*not bold*`, `# This line is not a heading`, `- not a list item`
- a link, a mention of a person, an image, a line break inside a paragraph, a quotation and a panel
- a block of a kind the converter has never heard of

**2. By counting, in a separate program.** `scripts/fidelity.py` shares no code with the converter. It walks
Jira's description and counts what is there, reads the Markdown and counts what is there, and the two must
agree: headings and their levels, list items, tables and their rows, code blocks, links, images. It compares
each code block's language and text exactly, and checks that every run of text is present and in order.
**Recorded against the fake** in `logs/fidelity-check.txt`, part 1: 3 headings, 9 list items, 1 table of 4 rows,
1 code block, 1 link, 1 image, 49 runs of text, all matching.

The heading count also covers the opposite failure. Jira's description has 3 headings and one line of plain
text that reads `# This line is not a heading`. The Markdown has 3 headings, not 4.

**3. By spoiling a good file.** Seven tests in the group `TheCheckCanFail` take a correctly saved file, damage
it, and require the fidelity check to object: a table flattened into paragraphs, a changed line of code, a lost
sentence, plain text turned into a heading. Two of these tests were themselves wrong at first. They did not
manage to damage the file, so the check correctly found nothing. Each now first confirms that it changed
something.

**4. By breaking the converter.** `logs/planted-bugs.txt`: 22 bugs were put into the reader and the converter
one at a time. Eleven are in the converter, among them the quest's scenario, a table flattened into separate
paragraphs, which 6 tests catch. One bug showed that the fixture was not ugly enough. Fencing every code block
with three backticks was caught by a single test and not by the fidelity check, because the fixture's code had
three backticks only in the middle of a line, which does not close a fence. A line of exactly three backticks
was added to the fixture. The same bug now fails 4 tests.

What this does not show: the converter was never run on a real description with formatting in it. The story in
the sandbox has an empty description.

## One field that was hard to keep

**The description, where a table cell holds a list.**

In Jira a table cell can hold anything a page can: several paragraphs, a list, a code block. A cell in a
Markdown table is one line of text. There is nowhere to put a list.

In `UGLY-7` the last cell of the table holds a sentence and a list of two items. What the converter writes:

    | Gamma \| Delta | 3 | Exports, but:<br>\- totals are wrong<br>\- order is lost |

The sentence and both items are there, in order, on lines of their own within the cell. But the list is no
longer a list. It is three lines of text, two of which begin with a dash. A program reading the Markdown would
not find a list there, and a list inside that list would survive only as deeper indentation.

Three ways were open, and each loses something:

- **Write the table as HTML**, which can hold a real list in a cell. Nothing is lost, and the description stops
  being readable Markdown at exactly the point where it is most complicated.
- **Move the list out of the table** to below it. The list stays a list and no longer belongs to its cell.
- **Keep it in the cell as lines.** This was chosen. The content and its place are kept, and the kind of
  structure is not.

It is not hidden. The reader counts each time it happens, prints the count, and records it in the file's front
matter under `description_notes`: `list inside a table cell, kept as lines: 1`. The fidelity check counts the
same thing by its own method and the two agree (criterion 2).

Two other fields were hard for a different reason, and deserve a line each:

- **The people.** `assignee`, `reporter`, `creator`, a comment's author and a custom field can each hold a
  person, with a name, an email address and pictures. Criterion 1 says every field appears. Criterion 7 says no
  private personal data is stored. The field is kept and the person is reduced to an account id. So the field
  is in the file, and it is not what Jira sent.
- **`lastViewed`, `votes` and `watches`.** These came back from the real sandbox. They describe the person
  asking, not the story: when that person last opened it, whether they voted, whether they are watching. They
  are kept, because they are fields Jira returned. But a file holding them changes when someone merely looks
  at the story, which works against criterion 5. In the recorded runs they did not change between the two
  runs, so the file stayed the same.

## Reflection: what would be lost by saving only the summary and the description

Almost everything that says what state the work is in.

The summary and the description say what the story is about. On the real story they are a 6-character summary
and an empty description: 2 of 51 fields. The other 49 are everything else Jira knows.

What those other fields hold, in the sample:

- **Where the work stands.** The status, the priority, whether it is resolved. The summary of `UGLY-7` contains
  the words `status: Done`. Its status is `In Progress`. Someone holding only the summary would have the wrong
  answer, and no way to know it.
- **Who is involved.** The assignee and the reporter. Even reduced to account ids, they say that somebody owns
  this and that somebody else asked for it.
- **What it is tied to.** Its parent, and a link saying it blocks another story. Neither is mentioned in the
  description. A story read alone looks free-standing.
- **The numbers people plan with.** Story points, the sprint, the due date. In the sample the story points are
  `0`, which is a decision somebody made, and different from not having estimated it at all.
- **The conversation.** The comment confirming the fault was reproduced.
- **Everything the site added.** Seven custom fields here, ten on the real story. Nobody outside that site
  knows what they mean, which is the reason not to throw them away.

Two things would be lost that are less obvious.

The description would mean less. The acceptance criteria are in it, but whether they are met is in the status
and the checklist and the comments. Text about work, without the state of the work, reads as a plan when it may
be a history.

And the identity would be lost. The summary is a label that changes, and the key in the file name is another.
Saved without its id, the story could not be matched to itself after either one changed.

## What was built

- **The reader**, `scripts/story.py`. It asks Jira for one story with one GET request and writes it as
  Markdown: front matter holding the fields the format knows by name, a body holding the description, and a
  preserved section holding every other field as Jira sent it. It stops, and writes nothing, if the number of
  fields placed is not the number Jira returned.
- **The converter**, `scripts/adf.py`. It turns Jira's description, which is a tree and not text, into
  Markdown. Anything it does not recognise is carried along at the place it occurred.
- **The fidelity check**, `scripts/fidelity.py`. It asks Jira for the story again, reads the saved file by its
  own method, and compares them field by field.
- **A fake Jira**, `scripts/fake_jira.py`, holding the ugly story and one whose text is worded as instructions.
- **43 tests**, `tests/test_story.py`, and a script that plants 22 bugs, `scripts/planted_bugs.py`.
- **The sample**, `participant/context/jira/stories/story-sample.md`: the ugly story as saved by the reader.

The first stretch goal is done: an image in a description is kept as a reference, with its alternative text
and Jira's id for it. The image itself is not fetched. The second, converting the Markdown back to Jira's
format and comparing, is not done. The fidelity check compares the two by counting and by text, which is
weaker.

## Where the important artifacts are

`.../` stands for `participant/evidence/jira-read-story/jira-attempt-007/`.

| What | Path |
|---|---|
| One story as Markdown: front matter, body, preserved section | `participant/context/jira/stories/story-sample.md` |
| Retrieving and writing it, and running it again | `participant/evidence/jira-read-story/jira-attempt-007/logs/story-run.txt` |
| The check of every field, the formatting, the scan, and the instruction-worded story | `participant/evidence/jira-read-story/jira-attempt-007/logs/fidelity-check.txt` |
| Reading a real story, twice | `.../logs/live-run.txt`, `.../logs/live-run-2.txt` |
| The fidelity check against the real story | `.../logs/live-fidelity.txt` |
| The output of all 43 tests | `.../logs/tests.txt` |
| Twenty-two planted bugs, each caught by a test | `.../logs/planted-bugs.txt` |
| The reader, the converter, the fidelity check | `.../scripts/story.py`, `.../scripts/adf.py`, `.../scripts/fidelity.py` |
| The fake Jira, the tests, the scripts that record the logs | `.../scripts/fake_jira.py`, `.../tests/test_story.py`, `.../scripts/record_evidence.py`, `.../scripts/planted_bugs.py` |

## How to reproduce the behavior

Needs Python 3.9 or later and nothing else. From the repository root:

    cd participant/evidence/jira-read-story/jira-attempt-007
    python3 -m unittest discover -s tests -v
    python3 scripts/planted_bugs.py
    python3 scripts/record_evidence.py

None of the three uses a network or a credential. The last rewrites the two required logs and regenerates
`participant/context/jira/stories/story-sample.md`. Because the file holds nothing about when it was made, the
regenerated sample should have the SHA-256 printed in `logs/story-run.txt`.

To save and check one story by hand, against the fake:

    python3 scripts/story.py --source fake --story UGLY-7 --out /tmp/ugly.md
    python3 scripts/fidelity.py --source fake --story UGLY-7 --file /tmp/ugly.md

Against a real Jira, set the connection in the shell without putting it in a file or in the shell's history,
and give `--out` a folder outside the repository, since a real story holds real text:

    read -s JIRA_BASE_URL && export JIRA_BASE_URL
    read -s JIRA_EMAIL && export JIRA_EMAIL
    read -s JIRA_API_TOKEN && export JIRA_API_TOKEN
    python3 scripts/story.py --source live --story <id or key> --out /tmp/story-live/story.md
    python3 scripts/fidelity.py --source live --story <id or key> --file /tmp/story-live/story.md

## What was tested or validated

"The run log" is `logs/story-run.txt` and "the check log" is `logs/fidelity-check.txt`, both recorded against
the fake. "The real runs" are `logs/live-run.txt`, `logs/live-run-2.txt` and `logs/live-fidelity.txt`.

| # | Criterion | Recorded against the fake | Observed against real Jira | Tested |
|---|---|---|---|---|
| 1 | Every field returned for the story appears in the file. | The run log: `total placed: 28 of 28`. The check log, part 1: one line for each of the 28 fields, saying where it is and that its value is what Jira sent, then `all 28 fields are in the file, none missing`. | `total placed: 51 of 51`, and the fidelity check's line for each of the 51 fields. 33 of them are fields the fixture does not have. | `EveryField`, five tests, one of which adds a field nobody has heard of. `test_a_field_that_could_not_be_placed_stops_the_run`. |
| 2 | Headings, lists, tables and code blocks in the description survive. | The check log, part 1, section 3: the counts match for headings, list items, tables and rows, and code blocks, and each code block's text is exact. | **Not observed.** The real story's description is empty. | `Formatting`, ten tests. See "How the formatting was tested". |
| 3 | A custom or unknown field is kept in a preserved section. | The check log: `every custom field (7) is in the preserved section`, and `customfield_10016 Story Points preserved number: 0`. The sample's `## Preserved fields` section holds 11 fields. | `every custom field (10) is in the preserved section`, with 23 more fields that are not custom and not known to the format, each with Jira's name for it. | `test_a_custom_field_is_kept_in_the_preserved_section_with_jiras_name_for_it`, `test_zero_empty_and_null_stay_what_they_were`. |
| 4 | The story is identified by its stable identifier. | The run log: `issue id 10042, key UGLY-7. The id is what identifies it.` The file's first field is `id: "10042"`. Run 2 asks by id and gets the same file as run 1, which asked by key. | The file's `id` is Jira's issue id, `10000`, with the key as a separate field. | `IdentityAndSameBytes`: a changed key changes one line of the file and not the id. |
| 5 | Running the retrieval again leaves an unchanged file byte-identical. | The run log: the same SHA-256 after run 1 and run 2, `File: UNCHANGED`, and a modified time that did not move. | `logs/live-run-2.txt`: `File: UNCHANGED. It already holds exactly these 5030 bytes`, with the SHA-256 that `logs/live-run.txt` printed. | `test_a_second_run_leaves_the_file_byte_identical_and_does_not_rewrite_it`, `test_the_file_holds_nothing_about_when_it_was_made`. |
| 6 | Ticket text is stored as content and never executed. | The check log, part 2: a story worded as instructions is saved as text. Afterwards the other file in its folder is untouched, the saved status is Jira's and not `Done`, one GET was sent and nothing was sent back. | The reader sent one GET for the story and wrote one file. The story's text holds no instruction, so this shows only that nothing else was done. | `TextStaysText`, five tests: typed text cannot become a heading or a list, a summary cannot add a front matter line, and a description cannot imitate the preserved section. |
| 7 | No credential or private personal data is stored. | The check log, part 1, section 4: Jira's answer held 10 private strings, and 0 are in the file. No email address of any kind is in it. | Jira's answer held 5 private strings, and 0 are in the file. The file was searched for the real token, the account's email address and their encoded form: none. | `NothingPrivate`, four tests. `TheCheckCanFail`: a name or an email address left in is noticed. |

Six of the seven were seen against real Jira. The seventh, formatting, could not be, for want of a real
description with any formatting in it.

The safety constraints:

- **A sandbox or a local fixture, and only reads.** The required evidence is from a local fixture. Three GET
  requests were sent to the participant's sandbox, one in each of the three real runs, and nothing else. **Tested**:
  `story.py` builds one kind of request.
- **Authenticate through an environment variable.** Three environment variables, set by the participant.
- **Untrusted text, and redacted or synthetic records.** The committed sample is synthetic. The real story was
  saved to a folder outside the repository. The logs of the real runs hold field ids, Jira's names for fields,
  counts and kinds of value. They hold none of the story's text.

## Remaining limitations

Known so far. There may be others.

What could not be done:

- **Formatting was never seen on real data.** The one story in the sandbox has an empty description. Every
  claim about tables, lists and code blocks rests on a fixture written by the same assistant as the converter.
- **A real story that changes between two runs was not seen.** The second real run found it unchanged.

What is kept, but not kept well:

- **A list or a code block inside a table cell** is kept as lines of text within the cell. See "One field that
  was hard to keep".
- **Comments are in the preserved section, in Jira's own structure.** Their text is not converted to Markdown.
  Nothing is lost, and a person would find them harder to read than the description.
- **Merged table cells** are written as ordinary cells, and counted.
- **A mark the converter does not know**, such as text colour, is kept as a comment after the text. The text is
  readable. The colour is in the comment and nowhere a person would see it.

What is taken out on purpose, so the file is not exactly what Jira sent:

- **People** are reduced to an account id, an account type and whether the account is active.
- **Links that hold the site's address**, which Jira puts on almost every object.
- **Email addresses typed into text.** Each is replaced by a marker, so that part of the text is altered.
- **A person's name typed into text cannot be found**, and is not removed. Only what looks like an email
  address, or sits where Jira puts a person, is caught. A shared file still needs a person to read it.

About the same bytes:

- **Fields about the person asking are kept**: `lastViewed`, and whether they voted or are watching. A file
  holding them changes when someone opens the story, though the story has not changed.

About the checking:

- **The fidelity check compares counts and text, not meaning.** It would not notice two list items swapped
  within a list, or a table's columns in a different order with the same cells.
- **Five of the 22 planted bugs are caught by exactly one test.**
- **No independent review has been run on this attempt.**

What would be done next: convert the Markdown back to Jira's format and compare it with the original, which
would turn the counting into an exact check; and render comments as Markdown.

## Sensitive values

No token, password or cookie is in any file. The assistant was never shown the API token, the account's email
address or the site's address. The project's secret scan finds nothing in the attempt folder or the sample.

The committed sample is a made-up story. The people named in the fixture, Ada Fixture and Bo Sample, and the
site, `fixture-site.example.invalid`, were invented for it, and none of them is in the sample: the reader
removed them, which is part of what the sample shows.

The real story was saved to a folder outside the repository and is in no committed file. The three logs of real
runs hold one issue id and key (`10000`, `SCRUM-1`), field ids, Jira's own names for those fields, counts and
kinds of value. They hold none of the story's text, no account id, no person's name, no email address and no
site address.

The participant is called "the participant" throughout. The token is the one made two quests ago. It can do
everything the account can and should be revoked now that these runs are done.
