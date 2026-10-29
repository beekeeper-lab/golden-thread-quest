# Setting up the automatic reviewer

For the program owner. The reviewer is specified in
`docs/design/08-ai-reviewer-specification.md` and decided in ADR-046. Everything is already in
the repository; this guide is the three things only you can provide, and how to turn it on.

## 1. Give it a model key

Repository **Settings → Secrets and variables → Actions → New repository secret**:
`ANTHROPIC_API_KEY`, an API key from the Anthropic Console. Only the *review* job reads it.

## 2. Give it a bot account

Pushing a review to a participant's fork needs a person-shaped account; the workflow's own token
cannot push to forks.

1. Create a GitHub account for the program, for example `gtq-reviewer-bot`.
2. Add it to `beekeeper-lab/golden-thread-quest` with **Write** access.
3. As that account, create a personal access token. A fine-grained token scoped to the program
   repository with **Contents: read and write** and **Pull requests: read and write** is enough;
   a classic token needs the `public_repo` scope.
4. Save it as the repository secret `PILOT_BOT_TOKEN`. Only the *apply* job reads it.

It can push to a participant's branch because their pull request allows edits by maintainers,
which `gtq hand-in` leaves on.

## 3. Optional: phone notifications

Add the repository secret `PILOT_NTFY_URL` (an ntfy topic URL). You are pinged when a hand-in
needs a person, and in shadow mode when the reviewer would have approved or asked for changes.

## Modes

Set the repository **variable** `PILOT_AI_REVIEW_MODE`:

| Value | What it does |
|---|---|
| `off` | Nothing runs. |
| `shadow` (default) | Reviews every ready hand-in and labels it `gtq:ai-approve`, `gtq:ai-changes` or `gtq:needs-human`, with the reasoning in the run's summary. **Writes nothing to the participant's branch.** You still decide, so you can compare. |
| `live` | Records the review (the pull request then shows `gtq:reviewed`; the reviewer's own labels are shadow-mode only), pushes it to the participant's branch, posts a GitHub review (approve or request changes), and the participant is emailed. Approved quests count their XP when the participant picks the review up. |

Start in `shadow`. When the reviewer's label agrees with your own decision on ten hand-ins in a
row, set `live`. Optional variables: `PILOT_AI_SAMPLE_EVERY` (default 5: one approval in five goes
to you anyway) and `PILOT_AI_MODEL` (default `claude-opus-5-5`).

## What you will see

- **`gtq:needs-human`**: yours. The reasons are in the run summary and the comment the participant
  got. Review as before; pushing your decision clears the label.
- **`gtq:ask-human`**: a participant added it to ask for a person. The reviewer skips it.
- A run's **summary** lists, for each pull request, what was decided and why.
- To review one by hand now: **Actions → Pilot AI review → Run workflow**, enter the number.

## Overruling it

Its decisions are ordinary review records. To change one, record your own decision on the quest
the way `docs/guides/REVIEWER.md` says; yours supersedes it, and the earlier decision is archived
beside it so the participant can see both.

## If it stops working

The sweep runs every 30 minutes, so a missed trigger recovers by itself. With the key or token
missing, it escalates to you rather than doing nothing. Turn it off with `PILOT_AI_REVIEW_MODE=off`.
