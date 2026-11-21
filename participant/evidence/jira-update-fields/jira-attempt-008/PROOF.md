# Proof · jira-update-fields

Attempt: `jira-attempt-008`

## How this was made

An AI assistant (Claude) wrote the updater, a fake Jira, the tests, the recording scripts and this file, at the
participant's direction. The work was done in small steps, each shown to the participant before the next.

What the participant did themself:

- Chose the three supported fields and agreed the list of refused ones.
- Agreed the design before anything was written: preview, then a confirmation tied to a fingerprint, a
  15-minute limit, an allowlist, and a re-read of the story just before the write.
- Confirmed that the project `SCRUM` is their sandbox and told the assistant to add it to the allowlist.
- Ran every command against their real Jira sandbox in their own terminal, with a token the assistant was
  never shown. That includes the one real write, which they confirmed by its fingerprint after reading the
  preview on their own screen.
- Changed a priority by hand in Jira's own page, to play the other person in the real stale run.

The assistant ran nothing against the real Jira. It read the saved logs afterwards, which hold no site address.

Statements below are marked **recorded against the fake** (a log of a run against the made-up Jira shows it),
**observed** (a saved run against the real sandbox shows it), **tested** (a passing test shows it, with the
output in `logs/tests.txt`) or **not assessed**.

Each of the four required records, `preview.txt`, `confirmation.txt`, `stale-run.txt` and `rerun.txt`, has two
parts. First the runs against the fake Jira, with checks. Then, under the heading THE SAME ON THE REAL JIRA
SANDBOX, the participant's real runs, copied unchanged from the `live-*.txt` logs.

## How a moved field is detected (criterion 3)

By comparing values, as the quest's hint says.

1. The preview reads the story and records, for each field named in the change, the value Jira holds at that
   moment. That value is part of what the fingerprint is computed from.
2. The confirmation does all its other checks first. Then, as its last read before the write, it reads the
   story again and works the change out afresh.
3. For each field named in the change, it compares the value Jira holds now with the value the preview
   recorded. If any differs, it refuses, names the field and both values, and sends no write.

Details that matter:

- The comparison is on the value and not on Jira's `updated` time. The documentation does not say that every
  edit moves `updated`.
- A field named in the change that already held the wanted value is watched too, although it is not sent.
- If someone else has already set the field to the very value wanted, that is still a refusal. The preview the
  person read no longer describes what Jira holds.
- A field outside the change moving does not stop the update, and is not touched by it. Only the fields named
  are sent.
- Labels are compared as a sorted list, and a priority by its id.

**Recorded against the fake**, `logs/stale-run.txt`: a preview saw priority Medium, someone else set Highest, and
the confirmation was refused with the priority left at Highest.

**Observed**, the second part of `logs/stale-run.txt`: a real preview saw the priority as not set. The
participant set it to Low in Jira's own page. The real confirmation answered:

```text
REFUSED: a field changed in Jira after the preview was made: priority: the preview saw (not set) and Jira now holds "Low" (id 4). Someone or something else changed it, and writing now would overwrite that. Make a new preview and read it.
Nothing has been written.
```

**Tested**: seven tests in the class `Stale`, covering each of the three fields.

### What this cannot detect in time

Jira's documented edit request has no "only if the value is still the one I saw" condition. The API
specification was searched for one and none was found. So between the last read and the write there is a
moment, a fraction of a second, in which someone else's change would be overwritten. The re-read makes that
moment short. It does not remove it.

What is done about it: after the write, the workflow reads the story's history, finds the entry its own write
made, and compares the "before" value in that entry with the value the preview saw. If they differ, it says a
change may have been overwritten and exits with code 2. That reports the case afterwards. It does not prevent
it. **Tested** (`test_a_change_in_the_last_moment_is_reported_afterwards`). **Observed** only in the ordinary
case: on the real write, the history entry's "before" values matched the preview. The overwrite case itself was
**not assessed** against real Jira, because it cannot be staged by hand.

## The acceptance criteria, one by one

1. **The preview shows the old and new value of each field.** Recorded against the fake for all three fields
   (`logs/preview.txt`). Observed for labels and due date (second part of `logs/preview.txt`). Tested.
2. **Only fields in the supported list can be changed.** The list is `labels`, `duedate`, `priority`, in
   `participant/context/jira/update/supported-fields.md`. Recorded against the fake
   (`logs/unsupported-field.txt`): a change naming the assignee, and one naming the summary, were refused.
   Tested with eleven unsupported field names and sixteen bad values. The function that sends the write also
   refuses any field outside the list, so the rule is applied twice.
3. **A field changed in Jira after the preview stops the update.** See the section above.
4. **A preview shows the Jira site, the project and the exact changes, and nothing is written before the human
   confirms.** The preview command is given no way to send a write: its connection has only a read function.
   Recorded against the fake and observed: every request of a preview was a GET, and a snapshot of the whole
   story taken before and after the preview was the same. The site's address is shown on the participant's
   screen and replaced by a marker in the saved log.
5. **The preview records the permission check and the duplicate check, or states where Jira cannot perform
   one.** The permission check asks Jira about this identity and this story (`mypermissions` with the issue id)
   and asks which fields it lists as editable (`editmeta`). Observed: both permissions yes, all three fields
   editable. The duplicate check is explained in the preview: an edit creates nothing, so what could repeat is
   the same edit being sent twice, and the workflow checks which fields already hold the wanted value and does
   not send those. The preview also states the one thing Jira cannot check, the condition described above.
6. **The workflow writes only to a project on an explicit sandbox allowlist.** The allowlist is
   `participant/context/jira/update/sandbox-allowlist.json`. An entry is a project id with a fingerprint of the
   site's address. The site is part of it because Jira numbers projects from the same start on every site, so
   a project id alone could match a production project elsewhere. Observed: the first real preview was refused
   because `SCRUM` was not yet listed (first real block in `logs/confirmation.txt`). Recorded against the fake:
   refused at the preview for `PROD-9`, a story the identity is permitted to edit, and refused again at
   confirmation when the allowlist no longer listed the project. Tested, including the same project id on
   another site.
7. **The confirmation is tied to a fingerprint of the exact preview, is refused when missing or when the change
   differs, and expires after a stated time.** The fingerprint is a SHA-256 over the site fingerprint, the
   issue id, the project id, each field's old and new value and the time of the preview. The first 12
   characters are the code a person gives. The limit is 15 minutes. Recorded against the fake
   (`logs/confirmation.txt`): refused with no fingerprint, with no name, with a change file edited after the
   preview, and at 16 minutes. Tested, with an altered saved preview refused as well. Of these, only the
   approved run and the allowlist refusal were also made against the real sandbox.
8. **A result record holds the issue key, the identifier of what was changed, the project, the timestamp and
   the confirmer.** `participant/context/jira/results/update-fields.md`, written by the real approved run.
   Observed: issue key `SCRUM-1`, Jira changelog entry `10049`, project `SCRUM`, written at 2026-11-19 15:47:13
   UTC, confirmed by "the participant". It also holds each field's value before, so the change can be reversed.
9. **Running the approved workflow again creates no duplicate, repeated or conflicting change.** Observed
   (second part of `logs/rerun.txt`): the preview command run again reported NOTHING TO CHANGE, issued no
   fingerprint and sent only GETs. The confirm command run again with the used fingerprint was refused.
   Recorded against the fake: the same, with the story's history still holding exactly one entry. A write is
   sent once and never retried. If no answer comes back, the workflow says the result is not known, exits with
   code 2, and the preview cannot be used again.

## What was built

- `scripts/update.py`: the workflow. Two commands, `preview` and `confirm`. Standard library only.
- `scripts/fake_jira.py`: a made-up Jira that accepts edits and keeps a history, built from Atlassian's API
  specification.
- `scripts/record_evidence.py`: records the four required logs and `unsupported-field.txt` against the fake,
  and copies the saved real runs onto the end of each.
- `scripts/planted_bugs.py`: puts 26 bugs into the workflow one at a time and records which tests fail.
- `scripts/changes/`: the change files used in the recorded runs. `scripts/fake-allowlist.json` and
  `scripts/fake-allowlist-without-sand.json`: the allowlists used with the fake.
- `tests/test_update.py`: 49 tests.
- `participant/context/jira/update/supported-fields.md` and `sandbox-allowlist.json`.
- `participant/context/jira/results/update-fields.md`: the result record of the real write.

One of the two stretch goals is met. The old value of every field written is kept in the result record and in the
write record. A custom field with a validated list was not done: no custom field is supported.

## Where the important artifacts are

| What | Path |
|---|---|
| Supported fields | `participant/context/jira/update/supported-fields.md` |
| Sandbox allowlist | `participant/context/jira/update/sandbox-allowlist.json` |
| Result record | `participant/context/jira/results/update-fields.md` |
| Preview record | `participant/evidence/jira-update-fields/jira-attempt-008/logs/preview.txt` |
| Confirmation record | `participant/evidence/jira-update-fields/jira-attempt-008/logs/confirmation.txt` |
| Stale-run record | `participant/evidence/jira-update-fields/jira-attempt-008/logs/stale-run.txt` |
| Rerun record | `participant/evidence/jira-update-fields/jira-attempt-008/logs/rerun.txt` |
| Unsupported fields refused | `participant/evidence/jira-update-fields/jira-attempt-008/logs/unsupported-field.txt` |
| The real runs as saved | `participant/evidence/jira-update-fields/jira-attempt-008/logs/live-*.txt` (seven files) |
| Test output | `participant/evidence/jira-update-fields/jira-attempt-008/logs/tests.txt` |
| Planted bugs | `participant/evidence/jira-update-fields/jira-attempt-008/logs/planted-bugs.txt` |
| The workflow | `participant/evidence/jira-update-fields/jira-attempt-008/scripts/update.py` |

## How to reproduce the behavior

From the repository root. None of these uses the network.

```bash
cd participant/evidence/jira-update-fields/jira-attempt-008
python3 -m unittest discover -s tests -v
python3 scripts/record_evidence.py
python3 scripts/planted_bugs.py
```

`record_evidence.py` rewrites the five logs. Times and fingerprints in them will differ, because a fingerprint
includes the time of its preview.

A real run needs a Jira sandbox, the three environment variables `JIRA_BASE_URL`, `JIRA_EMAIL` and
`JIRA_API_TOKEN`, and an allowlist entry for the sandbox project. The first preview against a project that is
not listed is refused and prints the site fingerprint and project id an entry needs.

## What was tested or validated

| What | How | Result |
|---|---|---|
| The workflow against the fake Jira | 49 unit tests, `logs/tests.txt` | all pass |
| Whether the tests notice a broken workflow | 26 planted bugs, `logs/planted-bugs.txt` | all 26 caught |
| The four required records | `scripts/record_evidence.py`, checks inside each log | all checks passed |
| A real preview, write, rerun and stale run | the participant, in their terminal | as described above |
| No credential in the output | the workflow searches its output for the token, the email address and their encoded form before showing it | none found, stated at the end of each real log |

What the real runs added that the fake could not: that Jira answers 204 to the edit, that the read-back holds
the proposed values, that the history holds one new entry by this identity for the write, and that the entry
records "before" values in the form the workflow compares. Until the real write, that form was known only from
an example in the documentation.

## Remaining limitations

- **The moment between the last read and the write**, described above. Reported afterwards, not prevented.
- **Three of the four refusals were made only against the fake**: the missing confirmation, the changed change
  file and the expired preview. They are decided from local files and the clock, before Jira is asked. The
  allowlist refusal and the stale refusal were also observed on the real sandbox.
- **Priority was never written to the real Jira.** The real write changed labels and the due date. A real
  preview of a priority change was made, and Jira listed priority as editable and offered "High", but that
  preview was then refused as stale on purpose.
- **In the recorded fake runs the confirm command is started by the recording script**, which stands in for the
  person. The script says so in the log. In the real runs a person typed it.
- **The confirmer's name is whatever is typed.** The workflow does not check who is at the keyboard. In the
  evidence the name is "the participant", so that no personal name is recorded.
- **Jira may email the story's watchers** about an edit. The preview says so. The workflow does not turn that
  off, because the documentation is unclear about what happens when an identity without the right permission
  asks to.
- **Reversing is by hand.** The result record holds the old values. A field that was empty before cannot be put
  back by this workflow, because it does not clear fields. On the real story that is the labels field.
- **The fake Jira is built from the specification.** It adds no history entry when a value does not change.
  Whether real Jira does the same is not documented and was **not assessed**, because the workflow never sends
  an unchanged value.
- **Long histories.** The history is read up to 50 pages of 100 entries. Past that, the workflow says it could
  not pick out its entry and gives the read-back values as the record. **Not assessed** on a real long history.
- **The state folder is local.** Saved previews and write records are in a folder on the machine that ran the
  command. "Used once" holds for that folder. A second machine would be stopped by the stale check or by
  finding nothing to change, not by the fingerprint.
- **The real story was left changed**: the label `gtq-sandbox`, the due date 2026-12-15, and the priority Low
  that the participant set by hand.

## Reflection: which field would you never let an agent change?

The security level, the field that decides who can see a story.

Every other mistake this workflow could make is visible to the people it affects. A wrong label, date or
priority shows on the story, appears in its history, and someone notices and puts it back. A wrong security
level does the opposite. Set too tight, the story vanishes for the very people who would have noticed. Set too
loose, it shows private content to people who should not see it, and what they have read cannot be taken back.
It is the one field where the old value in a log does not undo the change.

The assignee, the field in the quest's scenario, is second. It is easy to reverse, but it is a statement about
a person: that this work is now theirs. An agent making that statement from a stale copy does harm between the
change and its correction, to the person handed work they did not agree to and the one who thinks it is no
longer theirs.

What the three supported fields have in common is that they describe the work and not the people or the
access, and that a wrong value is plain to see and simple to put back.

## Sensitive values

- No API token, password or other credential is in any file. The real runs took the connection from
  environment variables in the participant's terminal. The workflow searches its output for the token, the
  email address and their encoded form before showing or saving it.
- The Jira site's address is in no file. It was shown on the participant's screen and replaced by a marker in
  each saved log. The allowlist and the logs hold a 16-character fingerprint of the address instead.
- No personal name or email address is in any file. The confirmer is recorded as "the participant".
- The real story's text is not in any file. The workflow never prints a summary or a description. The real logs
  hold the project key `SCRUM`, the story key `SCRUM-1`, their ids, one label, two dates, two priority names
  and one changelog entry id.
- The people, the site and the stories in the fake Jira are invented.
