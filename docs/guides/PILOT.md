# Pilot Guide

Thank you for trying the Golden Thread Quest. It is a self-paced training application for
the AI Context Engineer: the person who connects what people ask for to delivery that has
been checked. It runs on your own machine. Your work is ordinary files in your own copy of
the repository, and a reviewer decides what counts as verified.

This is a pilot of version 0.2.0. It works, but it is new, so if something is confusing,
that is what we most want to hear about.

## What you are asked to do

| Quest | | Time |
|---|---|---|
| **Establish a Safe Local Quest Repository** (Base Camp) | Required | About an hour |
| **Ingest a Meeting Transcript Without Losing Its Source** (BA Ruins) | If you have time | One to two hours |

The second quest unlocks once the first is verified. Finish by the date in your invitation,
then answer the five feedback questions at the end of this guide.

## Before you start

- A Mac or Linux machine. On Windows, use WSL.
- Git, Python 3.10 or newer, `make`, and uv (<https://docs.astral.sh/uv/>).
- A GitHub account.

**Your fork is public.** Anything you commit can be read by anyone, so use fictional
material only: made-up tickets, a transcript you wrote yourself, fake names. Never commit a
real token, password, customer name or real meeting transcript.

## Set up (about ten minutes)

1. Fork <https://github.com/beekeeper-lab/golden-thread-quest> on GitHub, using the **Fork**
   button.
2. `git clone https://github.com/<your-github-name>/golden-thread-quest ~/golden-thread-quest`
3. `cd ~/golden-thread-quest`
4. `git switch -c pilot/<your-name>`
5. `make setup`
6. `make serve`
7. Open <http://127.0.0.1:8765/>. The home page recommends the Base Camp quest.

To stop the application, press Ctrl-C in that terminal. To start it again, run `make serve`
from the same folder. Your progress is kept in files, so nothing is lost.

## Doing a quest

1. Read the whole quest page first. The acceptance criteria are numbered, and a reviewer's
   feedback will refer to them by number.
2. Click **Start quest**. It creates your evidence folder, and the page shows its path.
3. Do the work in your editor and terminal, not in the application. Put each file where the
   quest page's **Required evidence** list says, and fill in the `PROOF.md` in your
   evidence folder.
4. On the evidence page, run the check. A failing check is not a failed quest: it tells you
   what to fix.
5. Click **Mark evidence ready**, then **Record local validation**, then **Submit for
   review**. Submission is refused while a required file is missing, and the notice names
   it.

`docs/guides/PARTICIPANT.md` is the one-page reference, and `docs/USER-GUIDE.md` is the full
guide.

## Hand in your work for review

After you submit in the application, run these commands in a second terminal, from the same
folder:

1. `git add participant/`
2. `git commit -m "Pilot evidence: <quest-id>"`
3. `git push -u origin pilot/<your-name>`
4. The first time only: open the link `git push` printed, or your fork's page on GitHub, and
   create a pull request to `beekeeper-lab/golden-thread-quest`. Title it
   `Pilot: <your name>`, and leave **Allow edits by maintainers** ticked.
5. Post in the pilot's Slack thread that a quest is ready for review.

While a quest is waiting for review, leave its evidence alone. The reviewer is told if it
changes, and has to re-read it.

Use this one branch and one pull request for the whole pilot. It is never merged; it is only
how your reviewer sees your work and hands the review back.

## Get your review back

The reviewer adds the decision to your pull request. Then:

1. `git pull`
2. `make serve`, or reload the page if it is already running.

**Verified** means you are done with that quest, and the next one unlocks. **Needs changes**
shows the reviewer's findings at the top of the evidence page. Click **Resume after
review**, fix what they listed, submit again, and repeat the hand-in steps. Step 4 is not
needed again, because the pull request updates itself.

## Feedback: five questions

When you finish, or when you stop, reply in the Slack thread or send a direct message:

1. Where did you get stuck, and for how long?
2. What confused you, even briefly?
3. How long did each quest take?
4. What one thing would you change?
5. Would you recommend this to a colleague learning the role? Why or why not?

Anything else you notice is welcome too, especially where the application said one thing
and did another.

## If something goes wrong

- **`make setup` cannot find uv.** Install uv, or see `docs/SETUP.md`.
- **Port 8765 is taken.** `.venv/bin/python -m quest_app.cli serve --port 8766`, then open
  that port instead.
- **An action is refused.** The red notice at the top of the page says why, and nothing
  changed.
- **Anything else.** Ask in Slack. A screenshot of the page, plus the last lines from the
  terminal running `make serve`, is enough to go on.

The known limitations are listed in `docs/RELEASE-NOTES.md`.
