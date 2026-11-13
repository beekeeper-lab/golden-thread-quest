# Proof · context-staleness

Attempt: `context-attempt-001`

## In plain words

I wrote a freshness policy for an AI assistant: how long each kind of information stays
trustworthy, and what an answer does once it isn't. Then I built a small program that answers
"What is blocking release 3.0?" for a made-up app (Tixly), always says how old its information is,
and warns or refuses instead of giving a confident answer from stale data.

| Run | Clock | Result | What it proves |
|---|---|---|---|
| Fresh | 10-20-2026 5:00 PM | Answered; oldest note TEAM-61, 19 days 8 hours | A normal answer still states its oldest context |
| A bit stale | 10-21-2026 3:00 PM | **Warned**, naming the 5 notes past their 1-day limit | Stale context is named, not quietly relied on |
| Very stale (the quest's 9-day scenario) | 10-29-2026 9:00 AM | **Refused**, naming 5 too-old notes and 1 stale one | A badly out-of-date answer is withheld |
| Missing date | 10-20-2026 5:00 PM | **Refused**, naming BUG-33 | A note with no date is never treated as fresh |

Before each run I predicted the result from the policy alone. I got 6 of 7 parts right; the miss is
described under criterion 7.

## What was built

- **The policy**, `participant/context/freshness/policy.md`: five sources with a limit and a
  reason for each, the warn and refuse rule, what counts as untrustworthy, what every answer shows,
  and a worked example of all three clock settings.
- **The notes**, `participant/context/freshness/tixly-context.yaml` (and a copy with one undated
  note, `tixly-context-missing-date.yaml`): seven invented Tixly notes, each with its retrieval time.
- **The program**, `participant/tools/answer-blockers.py` (version 1.11.0): it reads the notes, takes
  the clock from `--now`, gives every note an age and a status, applies "worst status wins", and
  prints the answer with the oldest note, any stale or too-old notes by name, and which notes to
  refresh.

My decisions:
- **Five sources:** sprint board, bug list, test-run results (my addition), release plan, team roster.
- **The limits:** 1 day for the board, bugs and test results; 7 days for the release plan; 30 for
  the roster. I set the bug list to 1 day rather than 2 because heavy test runs can raise many bugs
  in a day.
- **The mix rule:** past the limit warn, past twice the limit refuse.
- **A missing date refuses**, like test results with no build or date not counting for sign-off.
- **Options in the answer:** an answer that warns or refuses lists the options (use it with
  caveats, or refresh exactly the notes named) rather than asking interactively, so every run is
  reproducible.

I built this with Claude (Claude Code). Claude drafted the policy, the program and this proof from
my decisions, explained each step, and I ran every command myself after predicting its result.

## Where the important artifacts are

| Artifact | Path |
|---|---|
| Freshness policy | `participant/context/freshness/policy.md` |
| Notes used by the runs | `participant/context/freshness/tixly-context.yaml` |
| Notes with an undated item | `participant/context/freshness/tixly-context-missing-date.yaml` |
| The program | `participant/tools/answer-blockers.py` |
| Fresh, warned and refused runs | `participant/evidence/context-staleness/context-attempt-001/logs/stale-run.txt` |
| Missing-date run | `participant/evidence/context-staleness/context-attempt-001/logs/missing-timestamp.txt` |

## How to reproduce the behavior

From the repository root. Nothing is written; the same commands give the same output on any day:

```bash
T=participant/tools/answer-blockers.py
N=participant/context/freshness
.venv/bin/python $T --context $N/tixly-context.yaml --now 2026-10-20T17:00:00-04:00   # answered
.venv/bin/python $T --context $N/tixly-context.yaml --now 2026-10-21T15:00:00-04:00   # warned
.venv/bin/python $T --context $N/tixly-context.yaml --now 2026-10-29T09:00:00-04:00   # refused
.venv/bin/python $T --context $N/tixly-context-missing-date.yaml --now 2026-10-20T17:00:00-04:00   # refused: BUG-33
```

## How I set the limits, and what the answer does instead of a confident claim

Each limit is how long that information usually stays true on a QA-heavy project, so a different
limit per source (criterion 2). Status changes many times a day, so the board, bugs and test results
get one day; a release plan is reviewed weekly; a team rarely changes mid-release.

Where a careless assistant would answer confidently, mine does one of two things. If some notes are
a little past their limit it still answers, but **warns** and names each stale note. If any note is
more than twice past, has no usable date, or can't be trusted for another reason, it **refuses**,
names every such note, and lists exactly which notes to refresh. It never hides a stale note to make
an answer look complete.

## What was tested or validated

Against the acceptance criteria:

1. **Every item records when it was retrieved:** each note in the YAML has `retrieved_at` with a
   time zone, and every run prints it in the "Notes used" table.
2. **Limits differ by kind and are stated with a reason:** policy section 1. The limits are built
   into the program to match the policy, and a notes file can't set its own.
3. **An answer lists the oldest context it used:** "Oldest note used: TEAM-61 …" in each
   `stale-run.txt` run; "Oldest dated note used: REL-51" in the missing-date run.
4. **Stale context is named:** the warned run names all 5 stale notes; the refused run names all 6
   untrustworthy notes.
5. **No retrieval time means stale:** `missing-timestamp.txt` refuses on BUG-33, "NOT RECORDED, age
   unknown", and doesn't call it the oldest note, because its age is unknown.
6. **A settable clock:** every run shows "Clock set to: … (from --now, not the computer's clock)";
   the program never reads the real time, so each run reproduces exactly.
7. **Another person can predict the result from the policy:** policy section 5 predicts all three
   clock settings, and the runs match it. I also predicted each run myself before running it. My one
   miss was the warned run, which I first predicted as refused; I had applied the 1-day limit where
   the policy refuses only past twice the limit (2 days). Checking it against the table corrected me,
   which is the point of the criterion.

**Review.** Before recording these runs, GitHub Copilot reviewed the program on a practice pull
request in my own copy (Hoosiertom50/golden-thread-quest#3) over 12 rounds, until it recommended
approval with no open issues. Between them, Copilot and Claude's own reviews found and fixed 7 High
findings. Every one was a way the program could give a confident, wrong "all clear":
- a repeated `notes:` heading silently hiding notes;
- a missing test failure count read as zero;
- a notes file loosening the policy's limits, or a misspelled source skipping every check;
- a lower-case "open" or an "In Progress" High bug being dropped from the blockers;
- an impossible time zone (`-04:60`) quietly "corrected" into a believable time, first by YAML's own
  time reading and then through an explicit `!!timestamp` label.

My rules for the reviews: fix every High, and fix Mediums that touch the quest's purpose. After any
code change, Claude re-reads the whole program before Copilot reviews it again. Medium findings
fixed along the way included crashes on odd input, a test run of 0 tests reading as "nothing
failed", two notes sharing an id, and ages shown rounded down so they seemed to contradict their
status.

The application's secret-scanning function found nothing in any of these files.

## Reflection: limits too tight compared with too loose

Too loose, and the assistant gives the nine-day-old confident answer the quest describes. That's
the expensive failure: a release decision made on a bug that was fixed, or not yet found. Too
tight, and nearly every answer warns, people learn to ignore the warning, and a refusal arrives
when nothing has really changed. That cost is real too, but it is visible and annoying rather than
silent and wrong. My limits lean tight for the fast-moving sources (board, bugs, tests) because
that's where a stale answer does the most damage. The warn stage, before refusing, keeps "a bit old"
usable.

## Remaining limitations

- The data is synthetic and local. Refreshing means re-retrieving the named notes yourself; the
  program lists them but fetches nothing, since this quest has no live connection.
- One notes format, and one question. The blocker rules are simple: anything on the board not
  "Done", High or Critical bugs that are Open or In Progress, and any failed tests.
- Staleness is per note, not per field (a stretch goal I didn't attempt).
- The limits are written twice, in `policy.md` and in the program. They match today, but a change
  must be made in both places.
- The release plan and the roster are checked for freshness and validity, but don't change the
  blocker list.

## Sensitive values

No real project, person, customer or credential is in this hand-in. Tixly and every note in it
are invented.
