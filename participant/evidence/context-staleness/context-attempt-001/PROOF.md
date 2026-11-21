# Proof · context-staleness

Attempt: `context-attempt-001`

## How this was made

An AI assistant (Claude) wrote the policy, the made-up library, the tool, the tests, the recording scripts and
this file, at the participant's direction. The work was done in small steps, each shown to the participant
before the next.

What the participant did themself:

- Chose the four kinds of context and their limits.
- Chose what an answer does when context is stale: split the answer by what it rests on, over a warning on top
  or a refusal.
- Agreed the rule that a stale release scope spoils the whole answer, where a stale status spoils only what is
  said about that one item.

Nothing here connects to any system. The release, the work items, the team and the decision are made up.

Statements below are marked **recorded** (a log in `logs/` shows it), **tested** (a passing test shows it, with
the output in `logs/tests.txt`) or **not assessed**.

## How the limits were set (criterion 2)

By asking, for each kind, how often it changes and what a wrong answer from an old copy would cost.

| Kind | Limit | Reason |
|---|---|---|
| Work item status | 24 hours | Near a release an item's status and what blocks it change several times a day. Yesterday's blocker is often gone and a new one is missed. |
| Release scope | 3 days | Which items are in a release changes at planning and triage, a few times a week. |
| Team and ownership | 30 days | Who owns what changes rarely, and a slightly old copy is still mostly right. |
| Decision | 90 days | A recorded decision does not change. It can be superseded, so it is not trusted for ever. |

The limits get longer as the kind changes more slowly. The scenario's nine-day-old snapshot is past the first
two and inside the last two, which one limit for everything could not say.

**These numbers are judgment.** There is no measurement behind them of how fast a real team's blockers or
scope change. They are a starting point that a team would correct from its own experience. The policy is where
they are changed: the tool reads its limits from the policy's table and has none of its own. **Tested**:
editing the table changes the answer, and a planted bug that fixes the limits in the code is caught.

## What the answer does in place of a confident claim (criterion 4)

It splits itself by what each statement rests on. Every statement is tied to the items it came from, and a
statement is made as fact only if all of those are inside their limits.

When something it used is stale, the answer has up to three parts.

1. **What fresh context supports.** Stated plainly.
2. **Last known, not a current claim.** What each stale item said, with its age. The reader keeps the last
   known state and is told it is old.
3. **The stale items, each named**, with how far each is over its limit, and the list of what to refresh.

The first line changes with what is stale, because the first line is what a hurried reader takes away.

| What is stale | First line | Recorded |
|---|---|---|
| Nothing | "2 work items are blocking release REL-2.4." | run 1 |
| Two statuses, scope fresh | "PARTIAL: 2 work items are blocking release REL-2.4 as far as fresh context shows. 2 cannot be assessed." | run 3 |
| The release scope | "CANNOT SAY what is blocking release REL-2.4." | run 2 |

How far a stale item spoils the answer depends on its kind. A stale status spoils what is said about that one
item. A stale scope spoils everything: without knowing what is in the release, no list of blockers can be
called complete, even if every status were fresh. **Tested** with exactly that case, a stale scope and fresh
statuses. In run 2 no count is given and no item is stated as blocking or as not blocking.

Two things the answer never does, which is the quest's third safety rule. It never leaves a stale item out:
all ten items are in the list of context used in every run. And it never states something stale as current.
**Tested** at 58 clock values across twelve days: at each one, every work item is mentioned, every item used is
listed, and no item whose status or scope is stale appears among the statements of fact.

## The acceptance criteria, one by one

1. **Every context item records when it was retrieved, shown in the data the runs use.** Each item has a
   `retrieved_at` line. **Recorded**: `logs/stale-run.txt` opens by showing two of the item files, and every
   run lists the retrieval time of each item it used. **Tested**: all nine files in the repository's library
   have a readable retrieval time.
2. **Limits differ by kind of context and are stated with a reason.** See above, and
   `participant/context/freshness/policy.md`.
3. **An answer lists the oldest context it used.** Every answer, fresh or not, lists what it used oldest first
   and then names the oldest. **Recorded**, run 1: "Oldest context used: decisions/D-12.md, retrieved
   2026-10-01T10:00:00Z, age 48d 23h 00m, limit 90 days: fresh." An item of unknown age is treated as the
   oldest and named as such.
4. **An answer relying on stale context says so and names the items.** See above. **Recorded**, run 2: eight
   stale items, each named with its age and how far it is over its limit.
5. **An item with no retrieval time is treated as stale.** **Recorded**, `logs/missing-timestamp.txt`: with the
   line taken out of one work item, that item is stale "because it records no retrieval time", is no longer
   stated as not blocking, and the answer becomes PARTIAL. The same holds for a time that cannot be read and for
   one later than the clock. **Tested** with nine unreadable values, a missing item and an item of the wrong
   kind. The rule in the policy is general: anything that cannot be shown to be fresh is stale.
6. **The clock used for the check can be set so the result is reproducible.** `--now` sets it, and every run
   prints the value used. **Tested**: the same clock value gives the same output, byte for byte. The recording
   script sets the clock on every run, so the logs come out the same whenever it is run. A planted bug that
   ignores `--now` is caught.
7. **Another person can predict from the policy when an answer will be qualified.** The policy gives the limits,
   five rules and a table of first lines, and a section on how to work an answer out by hand. **Recorded**: the
   working for run 3 is written out by hand in the log, and the tool's `ages` output agrees with it.
   **Tested**: a second working of the rules, written in the test from the policy and sharing no code with the
   tool, predicts the first line at 343 clock values across a hundred days, and the tool gives the same line
   every time. The boundary is tested too: at exactly its limit an item is fresh, and one second later it is
   stale, for each of the four kinds.

## What was built

- `participant/context/freshness/policy.md`: the policy.
- `participant/context/freshness/library/`: nine made-up item files. One release scope, six work items, a team
  and one decision.
- `participant/skills/context-freshness/SKILL.md` and `answer.py`: the tool, with `blockers`, `ages` and
  `refresh`. Standard library only. No network code.
- `participant/skills/context-freshness/tests/test_answer.py`: 35 tests.
- `scripts/record_evidence.py` and `scripts/planted_bugs.py`.

Both stretch goals were done.

- **Per-field staleness.** An item can give one field a retrieval time of its own. **Recorded**, run 3: WI-104's
  status is 14 hours old and stated as fact, and the reason it is blocked is 33 hours old and shown as last
  known. The answer's list of context has ten entries for nine files because that field is listed separately.
- **Refresh only the stale items.** **Recorded**, `logs/refresh.txt`: three stale items are fetched again from
  a folder of newer copies and six fresh ones are not touched, checked by the recording script from each file's
  SHA-256 and modified time. The answer then changes from 2 blockers to 3, because the stale copy of one item
  said In Review and it had since become Blocked. The source is a made-up folder. The quest allows no live
  connection, so a refresh from a real system was **not assessed**.

## Where the important artifacts are

| What | Path |
|---|---|
| The policy | `participant/context/freshness/policy.md` |
| The library | `participant/context/freshness/library/` |
| The fresh and stale runs | `participant/evidence/context-staleness/context-attempt-001/logs/stale-run.txt` |
| The missing retrieval time | `participant/evidence/context-staleness/context-attempt-001/logs/missing-timestamp.txt` |
| The refresh | `participant/evidence/context-staleness/context-attempt-001/logs/refresh.txt` |
| The tool | `participant/skills/context-freshness/SKILL.md`, `answer.py` |
| Test output | `participant/evidence/context-staleness/context-attempt-001/logs/tests.txt` |
| Planted bugs | `participant/evidence/context-staleness/context-attempt-001/logs/planted-bugs.txt` |

## How to reproduce the behavior

From the repository root. None of these uses the network.

```bash
python3 participant/skills/context-freshness/answer.py blockers --release REL-2.4 --now 2026-11-19T09:00:00Z
python3 participant/skills/context-freshness/answer.py blockers --release REL-2.4 --now 2026-11-28T09:00:00Z
python3 participant/skills/context-freshness/answer.py ages --now 2026-11-19T21:00:00Z
python3 -m unittest discover -s participant/skills/context-freshness/tests -v
python3 participant/evidence/context-staleness/context-attempt-001/scripts/record_evidence.py
python3 participant/evidence/context-staleness/context-attempt-001/scripts/planted_bugs.py
```

The first two are runs 1 and 2 of `logs/stale-run.txt`. Because the clock is set, they print the same today as
on any other day.

## What was tested or validated

| What | How | Result |
|---|---|---|
| The tool | 35 unit tests, `logs/tests.txt` | all pass |
| Whether the tests notice a broken tool | 19 planted bugs, `logs/planted-bugs.txt` | all 19 caught |
| The three recorded logs | `scripts/record_evidence.py`, 31 checks inside the logs | all passed |

## Remaining limitations

- **The limits are judgment**, as said above.
- **It measures the age of the copy, not the truth of it.** A copy fetched a minute ago can already be wrong,
  and one fetched last month can still be right. Freshness is a reason to trust a copy less, not a test of it.
- **A retrieval time is believed.** The tool checks that the time can be read and is not later than the clock.
  It cannot check that the item was really fetched then. Whatever writes items into the library has to stamp
  them honestly.
- **One question.** The tool answers "what is blocking the release?" The policy and the freshness check are
  general. Which items a question rests on, and how far a stale one spoils the answer, was written by hand for
  this question and would have to be written again for another.
- **The limit is per kind, not per field.** A field can have its own retrieval time, and it is judged against
  its item's limit. A title and a status are held to the same 24 hours.
- **A stale decision is not applied, which can raise the count.** With the decision past its limit, the item it
  set aside is reported as blocking, with a note. That is the cautious reading, and it could alarm someone over
  a decision that still stands.
- **The library and the tool have the same author.** The items were written to show each case.
- **Refresh was shown against a folder**, not a real system.
- **Not assessed**: a large library, and items written by several tools with clocks that disagree.

## Reflection: what is the cost of a limit set too tight compared with too loose?

Too loose costs a wrong answer that nobody questions. Too tight costs the warnings their meaning.

A limit that is too loose is the scenario. The snapshot is nine days old, the limit says that is fine, and the
answer comes out confident and wrong. The cost lands on whoever acts on it, and it is hidden: nothing in the
answer invites a second look. With limits of ten days on status and scope, run 2 here would have said "2 work
items are blocking" about a release nobody had looked at for over a week.

A limit that is too tight fails the other way, and more slowly. If statuses went stale after an hour, nearly
every answer would be PARTIAL or CANNOT SAY. People would learn that the qualification is always there, and
stop reading it. Then the one time it matters it is skipped with the rest. There is a second cost: an answer
that keeps saying "cannot say" about context that is in fact good enough stops being used, and people go back
to asking each other, or to a tool with no check at all.

So the two are not symmetric. Too loose is a rare, large, invisible cost. Too tight is a small cost paid on
every answer, which in the end buys the same failure by teaching people to ignore the signal.

That is the case for different limits by kind, and against one cautious number for everything. Each limit
should be about as long as the thing really stays true, so that a qualification is unusual enough to be read.
It is also why the answer keeps its fresh parts and shows the last known state: a tight limit then costs a
caveat, not the whole answer.

## Sensitive values

- No credential is in any file. Nothing here connects to any system or needs a token.
- No real project, work item or person is in any file. The release, the work items, the team names and the
  decision are made up. Owners are teams and roles, not people.
- The logs hold no home-folder path. The temporary folder used for two of them is shown as `COPY`.
