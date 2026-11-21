# Proof · jira-create-story-preview

Attempt: `jira-attempt-011`

## How this was made

An AI assistant (Claude) wrote the preview, a fake Jira, the draft, the made-up source notes, the tests, the
recording scripts and this file, at the participant's direction. The work was done in small steps, each shown
to the participant before the next.

What the participant did themself:

- Chose to take the required evidence from a fixture and to add one real, read-only preview.
- Agreed the design before anything was written, with three judgment calls: a required field that Jira has a
  default for is shown and not refused, duplicates are shown and do not block, and a project off the sandbox
  allowlist is refused.
- Ran the real previews against their Jira sandbox in their own terminal, with a token the assistant was never
  shown. The assistant read the saved logs afterwards, which hold no site address.

Nothing in this quest writes to Jira. `preview.py` has no code that could.

Statements below are marked **recorded against the fake** (a log of a run against the made-up Jira shows it),
**observed** (the saved run against the real sandbox shows it), **tested** (a passing test shows it, with the
output in `logs/tests.txt`) or **not assessed**.

`logs/preview-run.txt` has two parts: the run against the fake Jira, with checks, and then the participant's
real run, copied unchanged from `logs/live-preview.txt`.

## How I know the payload equals what a later write would send (criterion 5)

What can be shown here is that there is only one payload, and that everything the preview shows, saves and
writes is that one. What cannot be shown here is the later write itself, because this quest does not have one.

1. **One function makes the payload.** `build_payload` is the only place a payload is made. **Tested**: it is
   called exactly once in a preview, even when the payload file is also written. A planted bug that builds it a
   second time for the file is caught.
2. **One function turns it into bytes.** `body_bytes` gives the exact request body: the payload as JSON, no
   spaces or line breaks, names in alphabetical order. It is also called once. The SHA-256 the preview prints
   is of those bytes.
3. **What is shown is what is saved.** **Tested**: the payload printed on screen, parsed back, equals the
   payload saved in the state folder, and equals the one in `payload.md`. The SHA-256 of its bytes equals the
   one printed and the one saved. Two planted bugs, one that saves a payload with an extra field and one that
   hashes the wrong thing, are both caught.
4. **A second party agrees.** The recording script shares no code with the preview. It reads the payload out of
   the preview's printed output, turns it into bytes itself, takes the SHA-256 itself, and finds the one the
   preview printed. **Recorded against the fake.**
5. **The payload is the exact request body, shown whole.** It is not described or shortened. **Recorded against
   the fake** (982 bytes) and **observed** (892 bytes).

What the later write must do for the equality to hold, and what this quest leaves ready for it: the preview
saves the payload, its SHA-256 and its length under a fingerprint, with a 15-minute expiry. A write that loads
that record, checks the SHA-256 and sends `body_bytes` of the saved payload sends exactly what was previewed. A
write that built its own payload from the draft again could differ, if the draft or Jira's field list had
changed in between. That is a rule for the next quest. It is **not assessed** here.

## The acceptance criteria, one by one

1. **The preview lists the target project, issue type and every field.** Every field Jira lists for the issue
   type is put in one of three groups, and the counts add up to Jira's total. **Recorded against the fake**: 12
   fields, 9 set by the draft, 2 left to Jira, 1 optional and not sent. **Observed**: 20 fields, 6 set, 1 left
   to Jira, 13 optional and not sent. The field list is read through all its pages. **Tested**, with a planted
   bug that reads only the first page.
2. **Required fields that are missing stop the preview with a reason.** **Recorded against the fake**,
   `logs/missing-field-run.txt`: a draft with no component is refused, naming `"Components" (components)`. No
   payload is shown, none is saved and no payload file is written. A draft with no summary is refused before
   Jira is asked anything. **Tested**, including a draft missing two required fields, both named.

   The same log shows the case that is not a refusal: a draft with no Team, where Jira requires Team and has a
   default, Support. The preview is made, and Team is listed as left to Jira with that default. This is the
   quest's scenario. The draft was meant for the Data team, and the preview shows that Jira would have sent it
   to Support.
3. **A duplicate search result is shown in the preview.** The search is the one from the
   `jira-duplicate-search` quest, called unchanged. **Recorded against the fake**: one candidate, RPT-3, medium
   confidence, recommendation link, with how the draft differs from it. **Observed**: none, with a warning. See
   "What the real run found" below.
4. **A permission check result is shown in the preview.** Jira is asked whether this identity may create
   stories in this project (`mypermissions` with `CREATE_ISSUES`). **Recorded against the fake** and
   **observed**: yes. A "no" is a refusal. **Tested** against a project the identity can see and cannot create
   in.
5. **The preview contains the exact payload, not a summary of it.** See the section above.
6. **Running the preview changes nothing in Jira.** Three things show it. `preview.py` builds one kind of
   request, a GET, and a test reads its source to confirm there is no other. Every request is listed in the
   output: 12 against the fake and 7 against the real sandbox, all GETs. And the preview takes a snapshot of the
   project's stories before and after, their number and a code for their ids and update times, and finds them
   the same. **Observed**: 22 stories and the same code before and after. If the snapshots differ the preview
   refuses. **Tested.**
7. **Source citations are included for the content.** Every piece of content in the draft needs a citation: the
   summary, the description, and each of the labels, component, parent, due date and custom field. Each is
   checked against the file. **Recorded against the fake**: 10 citations, all true. **Tested**: content with no
   citation is refused, and so is a citation whose quoted words are not on the line named, one that points
   outside `participant/context/`, and one whose source was changed after the draft was written.

## What the real run found

The preview read the real project's field list without any change to the code. Until then that format was
known only from Atlassian's documentation. Three things came out of it.

- **The real project requires very little.** Apart from the fields the draft sets, the only field it requires
  for a Story is the reporter, which has a default. So this draft could not be refused there for a missing
  field. That is why the refusals are shown on the fixture.
- **The reporter is left to Jira, and Jira does not say who.** Jira reports that the field has a default and
  gives no default value. The preview says so.
- **The duplicate search had seen 1 story of 22.** The assistant had assumed the sandbox held one story and had
  the participant save one local copy. The first real preview reported 22 stories in its snapshot and "none"
  from a search of a one-story catalog, without connecting the two. The preview was then changed to compare the
  counts and to warn when Jira holds more stories than the local catalog. The second real run, the one saved,
  shows the warning: 21 stories in Jira have not been searched. Three tests and a planted bug cover it.

It is a warning and not a refusal. The other 21 stories were not saved locally, so the real search stayed
incomplete, and the "none" in the real log means "none in the one story searched".

## What was built

- `participant/skills/jira-create-story-preview/SKILL.md` and `preview.py`: the preview. Standard library only,
  plus the `jira-duplicate-search` and `jira-build-index` skills, which it imports.
- `participant/skills/jira-create-story-preview/fake_jira.py`: a made-up Jira that can only be read, with a
  project whose Story requires a component, a team with a default, and a priority with a default.
- `participant/skills/jira-create-story-preview/tests/test_preview.py`: 52 tests.
- `participant/context/jira/new-story/draft.md` and `sources/intake-notes.md`: the draft and the made-up notes
  it cites. `payload.md`: its payload, generated.
- `participant/context/jira/new-story/draft-sandbox.md` and `payload-sandbox.md`: the same story aimed at the
  real sandbox, and its payload.
- `participant/context/jira/new-story/refused/`: three drafts with lines taken out, for the refusals.
- `scripts/record_evidence.py` and `scripts/planted_bugs.py`.

Both stretch goals were done. The preview shows how the draft differs from the nearest existing story. And the
payload is checked against the project's field list: each field must be one Jira lists for the issue type and
of the kind the preview builds, and each chosen value must be one Jira allows.

## Where the important artifacts are

| What | Path |
|---|---|
| The story draft | `participant/context/jira/new-story/draft.md` |
| Its sources | `participant/context/jira/new-story/sources/intake-notes.md` |
| The payload | `participant/context/jira/new-story/payload.md` |
| The preview record | `participant/evidence/jira-create-story-preview/jira-attempt-011/logs/preview-run.txt` |
| The refusal record | `participant/evidence/jira-create-story-preview/jira-attempt-011/logs/missing-field-run.txt` |
| The real run as saved | `participant/evidence/jira-create-story-preview/jira-attempt-011/logs/live-preview.txt` |
| The real run's draft and payload | `participant/context/jira/new-story/draft-sandbox.md`, `payload-sandbox.md` |
| The preview | `participant/skills/jira-create-story-preview/SKILL.md`, `preview.py` |
| Test output | `participant/evidence/jira-create-story-preview/jira-attempt-011/logs/tests.txt` |
| Planted bugs | `participant/evidence/jira-create-story-preview/jira-attempt-011/logs/planted-bugs.txt` |

## How to reproduce the behavior

From the repository root. None of these uses the network.

```bash
python3 participant/skills/jira-create-story-preview/preview.py --source fake --draft participant/context/jira/new-story/draft.md --allowlist participant/skills/jira-create-story-preview/fake-allowlist.json --catalog participant/context/jira/duplicates/fixture --state /tmp/gtq-preview-state --today 2026-11-19
python3 -m unittest discover -s participant/skills/jira-create-story-preview/tests -v
python3 participant/evidence/jira-create-story-preview/jira-attempt-011/scripts/record_evidence.py
python3 participant/evidence/jira-create-story-preview/jira-attempt-011/scripts/planted_bugs.py
```

The time and the fingerprint of a preview differ on each run. The payload and its SHA-256 do not.

## What was tested or validated

| What | How | Result |
|---|---|---|
| The preview against the fake Jira | 52 unit tests, `logs/tests.txt` | all pass |
| Whether the tests notice a broken preview | 25 planted bugs, `logs/planted-bugs.txt` | all 25 caught |
| The two required records | `scripts/record_evidence.py`, 16 and 5 checks inside the logs | all passed |
| A real preview | the participant, in their terminal, twice | as described above |
| No credential in the output | the preview searches its output for the token, the email address and their encoded form | none found, stated at the end of the real log |

## Remaining limitations

- **The preview cannot promise the create would succeed.** Jira's documentation gives no way to try a create
  without making one. It also does not say whether a required field with a default may really be left out, and
  its list of required fields does not cover a project's workflow rules or automation. A payload can pass every
  check here and be refused.
- **Nothing was created, so none of it was checked against a real create.** That the real Jira accepts this
  payload's shapes, a component and a custom choice by id, a parent by key, the description in this document
  format, is **not assessed**. The shapes follow the example in Atlassian's API specification.
- **No refusal was observed on the real sandbox.** The real project requires too little to refuse this draft.
  All refusals are recorded against the fake or tested.
- **The real duplicate search covered 1 story of 22**, as described above.
- **The fake Jira and the draft have the same author as the preview.** The fake was built to show each case.
- **"Unchanged" covers the project's stories only**: their number, ids and update times. A change elsewhere on
  the site, or to a story's comments if that does not move its update time, would not be seen. The stronger
  evidence is that the preview has no code that writes.
- **The description is plain.** Paragraphs and simple lists. Formatting typed into the draft is sent as the
  characters typed.
- **Only single-choice custom fields can be set.** On the real project that leaves fields such as the sprint
  and the story point estimate out of reach.
- **A citation shows where words came from, not that they are right.** The check is that the quoted words are
  on the line named. Whether the draft says what the source meant is for a person to judge.
- **The saved preview is not yet used by anything.** Its fingerprint and expiry are for the later write quest.

## Reflection: what would a reader of the preview still not be able to predict?

Everything that Jira decides after it accepts the request, and whether it accepts it at all.

Whether it is accepted. The preview checks what Jira says it requires. Jira has no rehearsal for a create, and
a project can have rules the field list does not mention. The reader sees a payload that should work.

What Jira fills in. The real run made this concrete. Jira said the reporter is required and has a default, and
did not say what the default is. The reader can guess it is the account the token belongs to. The preview
cannot tell them. Twelve other fields were listed as optional with no default reported, and that is not the
same as staying empty: who it is assigned to, where it lands in the backlog and which status it starts in are
all decided by the project.

What it will be called. The key and the id do not exist until the story does.

What happens next. A project can run automation when a story is created: assign it, notify people, move it,
set more fields. None of that is in a payload, and none of it is in the list of fields.

How it will look. The description is sent as a document structure. The preview shows the structure and not the
rendered page.

Whether it is a duplicate after all. On the real run the search had read one story of twenty-two. The preview
now says so, which is the honest version of the same gap: the reader knows how much was not looked at, and
still does not know what is in it.

So the preview makes the request predictable and leaves the result partly open. The useful thing it can do
about the rest is to name it: say which fields Jira will decide, say when Jira will not tell, and say how much
the duplicate search did not see.

## Sensitive values

- No API token, password or other credential is in any file. The real runs took the connection from
  environment variables in the participant's terminal.
- The Jira site's address is in no file. It was shown on the participant's screen and replaced by a marker in
  the saved log and in `payload-sandbox.md`, which hold a 16-character fingerprint of the address instead.
- No personal name or email address is in any file.
- No real story's text is in any file. The local copy of the one real story searched for duplicates is in a
  scratch folder outside the repository. The real log holds the project key and id, an issue type id, the names
  of 20 fields as the real project calls them, and the number of stories in the project.
- The draft's content, the notes it cites, and everything in the fake Jira are made up.
