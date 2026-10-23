# Freshness policy for the Tixly context library

Tixly is a made-up event-ticket app. The library holds saved notes copied from five sources.
An answer built from those notes must say how old they are, and must not lean on notes that are
too old. This page says exactly when an answer is fine, warned or refused, so anyone can predict
the result before running it.

## 1. Sources and their limits

| Source | Fresh for | Why this limit |
|---|---|---|
| Sprint board (task status) | 1 day | Tasks move several times a day. |
| Bug list (status and severity) | 1 day | During heavy test runs a lot of new bugs can be raised in a single day. |
| Test-run results | 1 day | Results describe one build, and builds are made daily, so yesterday's results may be for code that no longer exists. |
| Release plan (date and scope) | 7 days | The plan is reviewed weekly. |
| Team roster | 30 days | People rarely join or leave in the middle of a release. |

These limits are the only ones used: a notes file can't set its own, and a note from a source not
in this table is not trusted.

## 2. The rule

A note's **age** is the clock time the answer is given at, minus the note's retrieval time.
Retrieval times, and the clock, are written as date and time with a time zone, for example
`2026-10-20T09:00:00-04:00` or `2026-10-20T13:00:00Z`; ages are shown down to the second.

| Age | Status | What the answer does |
|---|---|---|
| Up to the limit | **fresh** | Answers normally. |
| More than the limit, up to twice the limit | **stale** | Answers, but **warns** and names every stale note. |
| More than twice the limit | **too old** | **Refuses** to answer and names every note that is too old. |

The answer takes the worst status of any note it used: one too-old note means a refusal, and
otherwise one stale note means a warning.

## 3. Notes that can't be trusted

A note with a missing or unreadable retrieval time, or one without a time zone, is treated as
**too old**, so the answer **refuses**. Its age is unknown, and an unknown age can't be trusted,
just as test results with no build or date would not count for sign-off.

The same goes for a note that is **missing a fact its source needs** (a board note's status, a
bug's severity, a test run's failed or total count, a release plan's target date, the roster's
QA list), or that holds one in the wrong form, and for a note whose source has **no limit** in
the table above. It is treated as too old and named, never quietly filled in: a test run with no
failure count, or a run of 0 tests, must not be read as "nothing failed". Values are matched ignoring capitals and extra spaces ("open"
is Open), but a value that isn't recognised ("Opne") makes the note untrustworthy, so an unknown
status is never read as "not blocking". A note retrieved after the clock time is treated the same way, since
the clock or the note must be wrong. If two notes share an id, the notes contradict each other, so
no answer is given at all.

## 4. What every answer shows

- The clock time it used. The clock can be set, so the same notes and the same clock always
  give the same result.
- The **oldest note** it used, with its age. Notes with no usable age (no retrieval time, or one
  after the clock) are listed separately with the reason, since they can't be called the oldest;
  the oldest dated note is still shown.
- When warned or refused: every stale or too-old note by id, with its age and limit.
- When warned or refused, the options: use the answer with these caveats (warned only), or
  refresh exactly the notes listed first. Fresh notes never need refreshing.

## 5. Worked example

Board, bug and test notes retrieved 10-20-2026 at 9:00 AM; the release plan on 10-17-2026 at
9:00 AM; the team roster on 10-01-2026 at 9:00 AM.

| Clock | Board / bugs / tests | Release plan | Roster | Answer |
|---|---|---|---|---|
| 10-20-2026, 5:00 PM | 8 hours: fresh | 3 days 8 hours: fresh | 19 days 8 hours: fresh | **Normal answer** |
| 10-21-2026, 3:00 PM | 1 day 6 hours: stale | 4 days 6 hours: fresh | 20 days 6 hours: fresh | **Warns**, naming the 5 board, bug and test notes |
| 10-29-2026, 9:00 AM | 9 days: too old | 12 days: stale | 28 days: fresh | **Refuses**, naming the 5 board, bug and test notes as too old, and the release plan as stale |
