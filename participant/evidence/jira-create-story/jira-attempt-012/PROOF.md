# Proof · jira-create-story

Attempt: `jira-attempt-012`

## How this was made

An AI assistant (Claude) wrote the workflow, a fake Jira, the tests, the recording scripts and this file, at the
participant's direction. The work was done in small steps, each shown to the participant before the next.

What the participant did themself:

- Chose how a lost create is found again: a marker label on each story, over a person looking by hand.
- Agreed the design before anything was written: the four commands, the order of events around the create, and
  what "equals the preview" means.
- Agreed to one real create in their sandbox, knowing the workflow cannot delete it.
- Ran every command against their real Jira sandbox in their own terminal, with a token the assistant was
  never shown. That includes the one real create, which they confirmed by its fingerprint after reading the
  preview on their own screen.

The assistant ran nothing against the real Jira. It read the saved logs afterwards, which hold no site address.

Statements below are marked **recorded against the fake** (a log of a run against the made-up Jira shows it),
**observed** (a saved run against the real sandbox shows it), **tested** (a passing test shows it, with the
output in `logs/tests.txt`) or **not assessed**.

`logs/preview.txt`, `logs/confirmation.txt` and `logs/rerun.txt` each have two parts: the runs against the fake
Jira, with checks, and then the participant's real runs, copied unchanged from the `live-*.txt` logs.

The real story is `SCRUM-23`, issue id `10022`. The local link is
`participant/context/jira/new-story/linked.md` and the result record is
`participant/context/jira/results/create-story.md`. Both were written by the real run.

## How I verified the created story equals the preview (criterion 1)

In three steps, each closing a different gap.

**1. What was sent is what was previewed.** The preview shows the payload and the SHA-256 of its bytes. At
confirmation the payload is worked out again, from the draft and from Jira as it is at that moment, and its
SHA-256 must equal the previewed one. The draft file must also be byte for byte the one previewed. The bytes
sent are then those bytes. **Observed**: the confirmation printed the SHA-256 `d044842a…ad3a2`, the one the
preview had printed. **Tested**: the body the fake Jira received is exactly the bytes of the saved payload. A
planted bug that sends a different summary is caught.

**2. What Jira stored is what was sent.** After the create the story is read back from Jira by the issue id
Jira returned, and each field the payload sent is compared with it.

| Field | The same when |
|---|---|
| Project, issue type, priority, a custom choice | the id read back is the id sent |
| Summary, due date | the value read back equals the value sent |
| Labels | the same labels, in any order |
| Components | the same component ids |
| Parent | the same parent key |
| Description | the same structure and text |

**Observed**, from the real run:

```text
READ BACK from Jira by issue id 10022, and compared with the payload field for field:
  summary            sent "Quarterly revenue by plan report for the finance team"
                     read "Quarterly revenue by plan report for the finance team": the same
  description        sent 2 block(s) of document
                     read 2 block(s) of document: the same, identical as sent
  labels             sent ["gtq-57dc5556", "reporting", "revenue"]
                     read ["gtq-57dc5556", "reporting", "revenue"]: the same
  duedate            sent "2027-01-15"
                     read "2027-01-15": the same
Result: every field the payload sent reads back the same.
```

All six fields the real payload sent read back the same, the project and issue type among them. The
description came back identical, not only equivalent. The comparison allows for Jira adding its own
identifiers to a description and says which it found. On the real run it found none.

**3. What Jira added is named.** A created story holds more than was sent. Those fields are listed as Jira's.
**Observed**: status "To Do", priority "Medium", a reporter and a creator, the creation time, and 12 more
fields that hold a value. So "equals the preview" means: every field the preview showed in the payload is in
the story with that value, and every other value in the story is Jira's and is listed.

A difference is not passed over. **Tested** with seven kinds of difference, one per field: the command reports
the field, records "NOT ALL THE SAME" in the link file and exits with code 2.

The comparison was done a second time, by `verify`, in a separate run. **Observed**: the same result.

## The acceptance criteria, one by one

1. **The story created matches the previewed payload field for field.** See the section above.
2. **The returned key and identifier are written to the local file.** `linked.md` holds `jira_key: "SCRUM-23"`
   and `jira_id: "10022"`. **Observed.** They are written as soon as Jira's answer arrives, before the
   read-back. **Tested**: when the read-back fails, the key and id are already in the link file.
3. **The local file is matched to the Jira item by identifier afterwards.** `verify` fetches the story by the
   issue id in the link file. **Observed**: "Matched to Jira by issue id 10022: found." **Recorded against the
   fake**, `logs/rerun.txt` part 5: the story is given another key in Jira, and `verify` still matches it by
   its id, reports the change and updates the key in the link file, keeping the earlier one. A planted bug that
   matches by key is caught by that case.
4. **A preview shows the Jira site, the project and the exact changes, and nothing is written before the human
   confirms it.** The preview is given a connection with no way to send a write. **Observed**: 8 requests, all
   GETs, and the same snapshot of the project before and after, 22 stories. The change is stated as one new
   story, with the whole payload.
5. **The preview records the permission check and the duplicate check, or states where Jira cannot perform
   one.** Permission: Jira is asked whether this identity may create stories in the project. **Observed**: yes.
   Duplicates, three checks: the draft's own link file; stories in the project with this title, asked of Jira;
   and the local catalog. **Observed**: no link, no story with this title, none in the catalog, with the
   warning that the catalog held 1 of the project's 22 stories. The preview states where Jira cannot check: it
   has no way to refuse a second create and none to try one.
6. **The workflow writes only to a project on an explicit sandbox allowlist.** The same allowlist as the
   `jira-update-fields` quest: a project id with a fingerprint of the site's address. **Recorded against the
   fake**: refused at the preview for a project the identity may create in, and refused again at confirmation
   when the allowlist no longer listed the project. **Tested**, with the same project id on another site.
7. **The confirmation is tied to a fingerprint of the exact preview, is refused when missing or when the change
   differs, and expires after a stated time.** The fingerprint is a SHA-256 over the site, the project, the
   issue type, the payload, the marker, the draft's own SHA-256 and the time of the preview. The limit is 15
   minutes. **Recorded against the fake**, `logs/confirmation.txt`: refused with no fingerprint, with no name,
   with the draft's due date edited after the preview, and at 16 minutes. **Tested**, with an altered saved
   preview refused as well. **Observed**: the approved run names the fingerprint `c931beb110b0`, and the
   confirmation and the create are in one run of the command.
8. **A result record holds the issue key, the identifier of what was created, the project, the timestamp and
   the confirmer.** `participant/context/jira/results/create-story.md`. **Observed**: key `SCRUM-23`, issue id
   `10022`, project `SCRUM`, created at 2026-11-19 21:34:26 UTC, confirmed by "the participant".
9. **Running the approved workflow again creates no duplicate.** **Observed**, `logs/rerun.txt`: the same
   preview command, run again after the create, was refused before it contacted Jira: "this draft has already
   been created in Jira as SCRUM-23 (issue id 10022) … It is not created twice." **Recorded against the fake**:
   the same, and the used fingerprint is refused too, with the fake Jira still holding one new story.

   The limit, as the criterion allows: Jira cannot prevent a repeat. It would accept this payload again. What
   prevents one is local. See the next section.

## Not creating the story twice, and the lost answer

Three layers, all in this workflow, because Jira offers none.

- **The link file.** A linked draft is refused. That is the ordinary rerun, observed above.
- **The intent is recorded before the create is sent.** The link file is written first, saying a create is
  being sent and its result is not recorded. So a run that dies after sending leaves a file that stops the next
  run.
- **The marker.** Each preview adds one label to the payload, `gtq-` and eight random characters. After a
  failure, `reconcile` asks Jira for stories carrying it.

**Recorded against the fake**, `logs/recovery.txt`: the create is sent, the fake Jira makes the story and does
not answer. The workflow says it is not known whether the story was created, and does not send again. The next
preview is refused. `reconcile` finds nothing on a first search that lags, creates nothing, and on the second
finds exactly one story by the marker, links it and compares it. One POST and one story through all of it. In
the other case, where nothing was created, `reconcile` reports not found and leaves the decision to a person.

**Observed**, the part that could be checked without breaking anything: the real `verify` asked Jira for the
marker `gtq-57dc5556` and exactly one story carried it, the one that was created. So the real Jira's search does
find a story by this label.

A lost answer was **not assessed** against the real Jira. It cannot be staged there.

## What was built

- `participant/skills/jira-create-story/SKILL.md` and `create.py`: the workflow, with `preview`, `confirm`,
  `verify` and `reconcile`. Standard library only, plus the three earlier skills it imports.
- `participant/skills/jira-create-story/fake_jira.py`: a made-up Jira that accepts a create.
- `participant/skills/jira-create-story/tests/test_create.py`: 53 tests.
- `participant/context/jira/new-story/linked.md` and `participant/context/jira/results/create-story.md`: the
  link and the result of the real create.
- `participant/context/jira/new-story/fixture-run/`: the draft, link and result of the recorded fake run.
- `scripts/record_evidence.py` and `scripts/planted_bugs.py`.

Both stretch goals were done. The stored story is compared with the preview automatically, at the create and
again by `verify`. And a timeout where the creation may or may not have happened is handled, as above.

The draft for the real create is `participant/context/jira/new-story/draft-sandbox.md`, the one previewed in
the `jira-create-story-preview` quest. It was not changed.

## Where the important artifacts are

| What | Path |
|---|---|
| The local link | `participant/context/jira/new-story/linked.md` |
| The result record | `participant/context/jira/results/create-story.md` |
| The preview record | `participant/evidence/jira-create-story/jira-attempt-012/logs/preview.txt` |
| The confirmation record | `participant/evidence/jira-create-story/jira-attempt-012/logs/confirmation.txt` |
| The rerun record | `participant/evidence/jira-create-story/jira-attempt-012/logs/rerun.txt` |
| The lost-answer record | `participant/evidence/jira-create-story/jira-attempt-012/logs/recovery.txt` |
| The real runs as saved | `participant/evidence/jira-create-story/jira-attempt-012/logs/live-*.txt` (four files) |
| The workflow | `participant/skills/jira-create-story/SKILL.md`, `create.py` |
| Test output | `participant/evidence/jira-create-story/jira-attempt-012/logs/tests.txt` |
| Planted bugs | `participant/evidence/jira-create-story/jira-attempt-012/logs/planted-bugs.txt` |

## How to reproduce the behavior

From the repository root. None of these uses the network.

```bash
python3 -m unittest discover -s participant/skills/jira-create-story/tests -v
python3 participant/evidence/jira-create-story/jira-attempt-012/scripts/record_evidence.py
python3 participant/evidence/jira-create-story/jira-attempt-012/scripts/planted_bugs.py
```

`record_evidence.py` rebuilds `fixture-run/` and rewrites the four logs. Times, fingerprints and markers in
them differ on each run. It does not touch `linked.md` or the result record, which belong to the real run.

A real run needs a Jira sandbox, the three environment variables, and an allowlist entry for the sandbox
project.

## What was tested or validated

| What | How | Result |
|---|---|---|
| The workflow against the fake Jira | 53 unit tests, `logs/tests.txt` | all pass |
| Whether the tests notice a broken workflow | 26 planted bugs, `logs/planted-bugs.txt` | all 26 caught |
| The four recorded logs | `scripts/record_evidence.py`, 42 checks inside the logs | all passed |
| A real preview, create, rerun and two verifies | the participant, in their terminal | as described above |
| No credential in the output | the workflow searches its output for the token, the email address and their encoded form | none found, stated at the end of each real log |

What the real run added that the fake could not: that Jira accepts this payload, a description in document
format and labels and a due date among it; that it answers 201 with a key and an id; that the story reads back
field for field as sent, with the description unaltered; which fields Jira adds; and that its search finds the
story by the marker label.

## Remaining limitations

- **The lost answer was shown only against the fake.** See above.
- **`reconcile` cannot prove a story does not exist.** A search that finds nothing may be a search that lags.
  It says so and leaves the decision to a person.
- **Three of the four refusals were shown only against the fake**: the missing confirmation, the changed draft
  and the expired preview. They are decided from local files and the clock. The allowlist refusal was observed
  on the real sandbox in the `jira-update-fields` quest, not in this one. The real refusal in this quest is the
  rerun.
- **The real payload was small.** Six fields. A component, a priority, a parent and a custom choice were
  compared only against the fake. That real Jira returns them in the shapes the comparison expects is **not
  assessed**.
- **The protection against a second create is local.** It lives in the link file. On another machine, or with
  the link file deleted, the workflow would preview again. The same-title check, asked of Jira, would then
  report the existing story, and a person would have to notice it. The workflow does not refuse on it.
- **A duplicate made outside this workflow is not stopped.**
- **The local duplicate search saw 1 of the project's 22 stories.** The preview said so. The same-title check
  covered all of them, and looks only at titles.
- **The marker is a label that readers of the story can see**, and that means nothing to them. It is the price
  of being able to find the story again. If someone removes it, `verify` reports that the labels differ and
  that the marker no longer leads to the story.
- **The story cannot be removed by this workflow.** `SCRUM-23` is in the participant's sandbox now. It is made
  up, and deleting it is done by hand in Jira.
- **In the recorded fake runs the confirm command is started by the recording script**, which stands in for the
  person and says so in the log. In the real run a person typed it.
- **The confirmer's name is whatever is typed.** In the evidence it is "the participant", so that no personal
  name is recorded.

## Reflection: what happens locally if the write succeeds but recording the key fails?

Without a plan for it, nothing happens locally, and that is the problem. The story is in Jira. The local files
look exactly as they did before. The next run sees a draft with no link and creates the story again. This is
the quest's scenario, and from the inside it does not look like a failure at all.

So the design decides what the local files say before the question can arise. The link file is written before
the create is sent, and it says a create is being sent and its result is not recorded. After that there are
three ways for recording the key to fail.

- **The answer never arrives, or the run dies before writing.** The link file still says "sent, not recorded".
  The next preview and the next confirmation both refuse and say to run `reconcile`. That command asks Jira for
  the marker, finds the story and writes the key and id that the first run could not.
- **The answer arrives and the link file cannot be rewritten.** The workflow prints the key and the id, says
  the file could not be written, and exits with an error. The earlier "sent, not recorded" file is still there,
  because the new one is written beside it and swapped in only when complete. So this becomes the first case.
- **The link file cannot be written even before sending.** Then the create is not sent. The order guarantees
  that there is never a create without a local trace of it.

All three are **tested**. What remains is the part no local file can settle. If a person deletes the link file, the trace is gone. If
`reconcile` searches before Jira's search has caught up, it finds nothing, and "nothing found" then means
"wait", which only a person can decide. The workflow's part is to never answer that uncertainty by creating
again.

## Sensitive values

- No API token, password or other credential is in any file. The real runs took the connection from
  environment variables in the participant's terminal.
- The Jira site's address is in no file. It was shown on the participant's screen and replaced by a marker in
  each saved log, which hold a 16-character fingerprint of the address instead.
- No personal name or email address is in any file. People Jira returned are shown as "a person, not shown".
  The confirmer is recorded as "the participant".
- The real project's name, "Work", is in `logs/live-confirmation.txt` and in the copy of it in
  `logs/confirmation.txt`, beside the project's key. It is a generic word. The workflow was changed afterwards
  to show a project by its key and id only, and the later verify log and `linked.md` do not have it.
- The creation time in the real logs carries the time-zone offset Jira returned.
- The story that was created is made up: a finance report cited to made-up meeting notes. No real story's text
  is in any file.
