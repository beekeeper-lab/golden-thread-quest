# Proof · jira-list-projects

Attempt: `jira-attempt-006`

## How this was made

An AI assistant (Claude) wrote the skill, a fake Jira to test it against, the tests, the recording scripts and
this file, at the participant's direction. The work was done in small steps, each shown to the participant
before the next.

What the participant did themself:

- Chose to take the required evidence from a local fixture and to add one real, read-only run, over using a
  fixture alone.
- Agreed the design before anything was written: the project id as the identity, one file for each project
  named by the id, and a list with a lookup by each label.
- Ran the two recorded runs against their real Jira sandbox, in their own terminal, with a token the assistant
  was never shown.

Why the required evidence comes from a fixture. The quest asks for projects past the first page, a project
renamed between two runs, and a project that has vanished. The participant's sandbox has one project, which
nobody has renamed. Making those things true there would have meant creating, renaming and deleting projects,
and the quest says to make no change in Jira. So the list and the run log were made against a fake Jira, where
a rename changes nothing real. The quest allows a local fixture and asks for synthetic records.

Statements below are marked **recorded against the fake** (a log shows it), **observed** (a recorded run
against the real sandbox shows it), **tested** (a passing test shows it, with the output in `logs/tests.txt`)
or **not assessed**.

## Which field is treated as the identity

**The project id.** The field Jira calls `id`, for example `10003`.

Jira returns three labels with each project: an id, a key and a name. An administrator can change the key and
the name. The id is given once and stays. So the skill treats them differently:

| Label | Example | Treated as |
|---|---|---|
| id | `10003` | **The identity.** Records are matched on it. Files are named by it. Links point to it. |
| key | `DPAT`, later `DATA` | A field that can change. Stored, shown, and used to look a project up. Never used to match one. |
| name | `Data platform` | The same. |

What that means in each place the quest asks about:

- **Criterion 2, three separate fields.** Each record in `projects.json` has `id`, `key` and `name`, and each
  record file lists the three on their own lines.
- **Criterion 3, files and links.** A project's file is `projects/<id>.md`. Every link in `projects.md` points
  to such a file. No file is named by a key or a name, so a changed key cannot leave one orphaned.
- **Criterion 4, a rename.** On a second run each project Jira returns is looked up by its id. If the id is
  held, that record is updated, and what the key or name used to be goes into the record's history. Nothing
  about the key or the name decides whether two records are the same project.

Why not the key, which is what most people use. A key is printed on every item in the project, `DPAT-12`, so
it looks permanent. It is not: the scenario in this quest is a key being changed. Two things the tests try
show how it fails. Two projects can swap keys, and a new project can be given a key that another project used
to have. Matching on the key gets both wrong. Matching on the id gets both right
(`test_two_projects_that_swap_keys_stay_the_right_way_round`,
`test_a_new_project_given_another_projects_old_key_is_a_separate_record`).

Why not the name: two projects can have the same one. The recorded run adds a second project named `Billing`,
and they stay two.

What rests on trust: that Jira's project id does not change. The skill has no way to check that. If Jira ever
gave an existing project a new id, the skill would see a vanished project and a new one.

## Reflection: what else in Jira has a label that people believe is an identity

The key of an issue. `SCRUM-12` is the most trusted label in Jira. It is on every board, in every link people
paste, and in commit messages. It is two labels joined: a project key, which this quest shows can change, and
a number. Change the project's key and every issue in it has a new key. Move one issue to another project and
it gets a new key by itself. Under it Jira keeps an issue id, a plain number that does not change, and almost
nobody uses it.

This is closer to home than the project key. `participant/skills/jira-read-assigned/` matches stories on
their Jira key, and names each story's notes file by it. That was the right step up from matching on the
title. It is the same mistake as the scenario in this quest, one level down: after a project key change, every
story would look new, and every notes file would be an orphan.

Three more, briefly:

- **A person's display name.** It changes, and two people can share one. The account id is the identity. The
  earlier skills here already keep the account id and never the name.
- **A status name.** `In Progress` in one project and `In Progress` in another can be two statuses with the
  same word on them, and an administrator can rename either. Each has an id underneath.
- **A custom field's name.** `Story Points` is a name. The field is known to Jira by an id such as
  `customfield_10016`, and that id differs from one site to the next.

What they have in common is the reason the mistake is so easy. Jira shows people the label and hides the id,
because the label is what a person can read. So the label is what gets copied into file names, links and
scripts. The id only turns up when someone goes looking for it in what the API returns.

## What was built

- **The skill**, `scripts/projects.py`. It reads every project the connection can see, across every page, and
  keeps each by its project id. It writes a list, one record file for each project, and a memory file. It sends
  GET requests only.
- **A fake Jira**, `scripts/fake_jira.py`: made-up projects, handed out in pages, which can be renamed, removed
  and added to, and which can be made to page wrongly.
- **34 tests**, `tests/test_projects.py`, and a script that plants 15 bugs to see whether the tests notice,
  `scripts/planted_bugs.py`.
- **The project list**, `participant/context/jira/projects.md`, with twelve record files in
  `participant/context/jira/projects/` and `participant/context/jira/projects.json`. All of it was generated
  by the skill from the fake. Every project in it is made up, and the list says so on its first line of data.

The first stretch goal is done: each record keeps a history of its former keys and names, with the time each
change was noticed, and the list shows a former label beside the current ones so that an old key still leads
to its project. The second, projects that appear in two accounts, is not done.

## Where the important artifacts are

`.../` stands for `participant/evidence/jira-list-projects/jira-attempt-006/`.

| What | Path |
|---|---|
| The project list, with the three lookups | `participant/context/jira/projects.md` |
| One record for each project, named by project id | `participant/context/jira/projects/` |
| Retrieving the projects, and again after a rename | `participant/evidence/jira-list-projects/jira-attempt-006/logs/projects-run.txt` |
| A copy of that log, at the path the quest names | `participant/evidence/jira-list-projects/attempt-001/logs/projects-run.txt` |
| Two runs against the real sandbox | `.../logs/live-run.txt`, `.../logs/live-run-2.txt` |
| The output of all 34 tests | `.../logs/tests.txt` |
| Fifteen planted bugs, each caught by a test | `.../logs/planted-bugs.txt` |
| The skill | `.../scripts/projects.py` |
| The fake Jira, the tests, and the scripts that record the logs | `.../scripts/fake_jira.py`, `.../tests/test_projects.py`, `.../scripts/record_evidence.py`, `.../scripts/planted_bugs.py` |

## How to reproduce the behavior

Needs Python 3.9 or later and nothing else. From the repository root:

    cd participant/evidence/jira-list-projects/jira-attempt-006
    python3 -m unittest discover -s tests -v
    python3 scripts/planted_bugs.py
    python3 scripts/record_evidence.py

None of the three uses a network or a credential. The last rewrites `logs/projects-run.txt` and regenerates
`participant/context/jira/projects.md`, `projects.json` and `projects/`. The times in them will differ from the
ones committed here. Everything else should be the same.

A run against a real Jira needs a sandbox site and an API token, set in the shell without putting them in a
file or in the shell's history:

    read -s JIRA_BASE_URL && export JIRA_BASE_URL
    read -s JIRA_EMAIL && export JIRA_EMAIL
    read -s JIRA_API_TOKEN && export JIRA_API_TOKEN
    python3 scripts/projects.py --source live --out /tmp/projects-live

Give `--out` a folder outside the repository, so that real projects do not land beside the made-up ones. The
skill refuses a folder that already holds projects from the other kind of run.

## What was tested or validated

"The run log" is `logs/projects-run.txt`, recorded against the fake. "The real runs" are `logs/live-run.txt`
and `logs/live-run-2.txt`. Test names are in `tests/test_projects.py`, and their output is in `logs/tests.txt`.

| # | Criterion | Recorded against the fake | Observed against real Jira | Tested |
|---|---|---|---|---|
| 1 | Every visible project is retrieved, including those past the first page. | The run log, part 1: 11 projects over 3 pages of 5, 5 and 1. Part 2, at 50 to a page: 49, 50, 51, 100 and 101 projects, all received. 51 is one more than a page, the case the hint names. | 1 project over 1 page, and Jira's own count was 1. A second page was **not observed**: the sandbox has one project. | `EveryProjectAcrossPages`, nine tests, among them a Jira that gives fewer to a page than asked and one whose pages do not move forward. |
| 2 | Each record stores the id, the key and the name as separate fields. | `participant/context/jira/projects/10003.md` lists `Project id`, `Key` and `Name` on three lines, and `projects.json` holds the three as three fields. | The record written for the real project has a numeric id and its key as a separate field. It is in a scratch folder and is not committed. | `test_each_record_stores_the_id_the_key_and_the_name_as_separate_fields`. |
| 3 | Files and links use the identifier, not the key or name. | The run log, part 1: 11 files, `10001.md` to `10011.md`, and after the rename no file named `DATA.md` or `DPAT.md`. | The real runs: `1 file(s) in projects/, each named by project id`. | `ThreeFieldsAndFilesById`: every link in the list points to `projects/<digits>.md`, and that file exists. |
| 4 | A rename is matched to the existing record. | The run log, run 2: `RENAMED: project id 10003, key was 'DPAT' and is now 'DATA'. Same id, same record, same file.` The only new file after run 2 is for the project that was added. | **Not observed.** Nothing was renamed on the sandbox. The second real run shows the unchanged project matched by id: `new: 0, unchanged: 1`. | `Renames`, six tests, among them two projects swapping keys and a new project taking another's old key. |
| 5 | A project that disappears is flagged, not deleted. | The run log, run 2: `NOT RETURNED: project id 10006 ... Kept and flagged, not deleted.` It is still in `projects.md`, marked, under `Not returned by Jira (1)`, and `projects/10006.md` still exists. | **Not observed.** Nothing disappeared. | `Vanished`, three tests: flagged once, kept with its last labels, and cleared if it comes back. |
| 6 | The run output shows the page count. | Every run in the run log: for example `11 project(s) received over 3 page(s)`, with a line for each page. | Both real runs: `1 project(s) received over 1 page(s)`. | `test_projects_past_the_first_page_are_retrieved_and_the_page_count_is_shown`. |
| 7 | Another person can find a project by any of its three labels. | The run log, "FINDING THE RENAMED PROJECT": the same project is found in the list by its new key, by its old key, by its name and by its id, and each row leads to `projects/10003.md`. | | `FindableByAnyLabel`: every project is in all three tables with its other two labels, and each table is sorted by its own label. |

Criterion 7 is about a person, and no person other than the assistant has tried it. What is shown is that the
rows are there and lead to the right file.

Whether the count is whole. **Recorded against the fake**, the run log, last case: a Jira whose first page
wrongly says it is the last, holding 51 projects. The skill received 50, saw that Jira's own count was 51,
stopped, and wrote nothing.

The checks were themselves checked. `logs/planted-bugs.txt`: 15 bugs were put into `projects.py` one at a
time, among them matching by key, matching by name, naming files by key, four ways of losing projects while
paging, and deleting a project that disappeared. The first time, one was caught by no test: leaving the site's
address out of the search of the output. Two tests were added. All 15 are now caught, 6 of them by exactly
one test.

The safety constraints:

- **A sandbox or a local fixture, and only reads.** The required evidence is from a local fixture. The two real
  runs each sent one GET request to the participant's sandbox, and nothing else. **Tested**: `projects.py`
  builds one kind of request.
- **Authenticate through an environment variable.** Three environment variables, set by the participant. The
  skill holds no credential and no site address.
- **Redacted or synthetic records.** Every project in the committed list is made up. The real project's key and
  name are in a scratch folder outside the repository and in no committed file. Both real runs end with the
  skill's search of its own output for the token, the email address, their encoded form and the site's
  address: none found.

## Remaining limitations

Known so far. There may be others.

What could not be done:

- **A rename, a disappearance and a second page were never seen against real Jira.** The sandbox has one
  project, and the quest forbids changing Jira. All three are shown against the fake only. The real runs show
  that the skill can list projects, count pages and match an unchanged project by its id.
- **Whether a real Jira keeps a project's id through a change of key** was not confirmed by trying it. It is
  what Jira's documentation describes, and the whole design rests on it.

About the fake:

- **It was written by the same assistant as the skill**, from Jira's published specification. A wrong idea
  about how Jira pages would be in both. The real runs agreed with it on the one page they touched.

About the skill:

- **It trusts Jira's own count.** If Jira gave no count and said too early that a page was the last, the skill
  would accept a short list. With a count, it does not.
- **It cannot say why a project was not returned.** Deleted, and no longer visible to the connection, look the
  same. The connection check from the previous quest is what tells them apart.
- **The time a rename is recorded is the time the skill noticed it**, not the time it happened in Jira. A
  project renamed twice between two runs shows one change.
- **It keeps three labels and nothing else about a project.** No lead, no category, no type.
- **A project's name is other people's text.** It is flattened to one line and stripped of the characters that
  start Markdown structure before it is written. It is not otherwise changed.
- **The list is long for a large site.** It holds every project three times.

About the checking:

- **Six of the fifteen planted bugs are caught by exactly one test.**
- **Criterion 7 was not tried by another person.**
- **No independent review has been run on this attempt.**

What would be done next: make the existing story sync, `participant/skills/jira-read-assigned/`, record each
story's project by this id, so that a changed project key does not orphan its stories.

## Sensitive values

No token, password or cookie is in any file. The assistant was never shown the API token, the account's email
address or the site's address. The project's secret scan finds nothing in the attempt folder, the project list
or its records.

The committed list holds made-up projects only. Their names, keys and ids were invented for the fake.

The two logs of real runs hold counts, times and the words the skill prints. They hold no project key, no
project name, no account id, no site address and no person's name. The real project's own record was written
to a folder outside the repository.

The participant is called "the participant" throughout. The token used is the one made for the previous quest.
It can do everything the account can, and should be revoked now that these runs are done.
