# Pilot Guide

Thank you for trying the Golden Thread Quest. It is a self-paced training application for
the AI Context Engineer: the person who connects what people ask for to delivery that has
been checked. It runs on your own computer, and a reviewer decides what counts as done.

This is a pilot of version 0.2.2. It works, but it is new. If anything is confusing, even
for a moment, that is exactly what we want to hear.

You do not need to be a developer. You will paste a few short commands into a terminal
window, and this guide says what you will see each time.

## What you are asked to do

| Quest | | Time |
|---|---|---|
| **Ingest a Meeting Transcript Without Losing Its Source** (BA Ruins) | Required | One to two hours |
| **Establish a Safe Local Quest Repository** (Base Camp) | If you have time | About an hour |

Start with the transcript quest. The home page offers it first, and Base Camp after it.
Finish by the date in your invitation, then answer the five questions at the end of this
guide.

## Before you start

- **A Mac, or a Linux computer.** On Windows, tell the pilot lead before you start. If you
  already use WSL (Ubuntu on Windows), open Ubuntu and follow the steps below as written.
- **A free GitHub account.** If you do not have one, create it at <https://github.com/signup>.
  Your GitHub name will appear on your work.
- **About ten minutes** for setup, and your computer password if it asks for it.

**Use made-up material only.** Your work is stored on GitHub where anyone can read it. Use
fictional tickets, a transcript you wrote yourself and fake names. Never include a real
password, customer name or real meeting.

## Step 1: Set up (once)

1. **Open a terminal window.** On a Mac, press Cmd-Space, type `Terminal` and press Return.
   On Linux, open Terminal from your applications.
2. **Copy this line, paste it into the terminal and press Return:**

   ```
   curl -fsSL https://raw.githubusercontent.com/beekeeper-lab/golden-thread-quest/v0.2.2/install.sh | bash
   ```

3. **Answer its questions.** It works through seven steps and says which one it is on.
   - "Install ...? [Y/n]": press Return to say yes. It asks before it installs anything.
   - On a Mac, a window may ask to install "command line developer tools". Click
     **Install** and wait; the terminal carries on by itself afterwards.
   - If it asks for your password, type your computer password and press Return. Nothing
     appears as you type. That is normal.
   - **Sign in to GitHub:** it shows a code like `ABCD-1234` and opens your browser. Paste
     the code on the GitHub page and click **Authorize**.
   - "Your first name": type it and press Return. It labels your work for the reviewer.
4. **The application opens in your browser** when it asks "Start the application now?"
   and you press Return. The home page recommends the transcript quest.

If a step fails, the terminal says what went wrong in plain words. Fix that, then paste
the same line again. It picks up where it stopped, and it never deletes your work.

## Starting and stopping the application

- **To start it:** open a terminal window and type `gtq start`. Your browser opens it.
- **Leave that terminal window open** while you use the application.
- **To stop it:** click in that terminal window and press Ctrl-C.

Your progress is kept in files on your computer, so stopping loses nothing.

## Step 2: Do a quest

1. **Read the whole quest page first.** The acceptance criteria are numbered, and your
   reviewer's feedback refers to them by number.
2. **Tick the confirmation box and click Start quest.** This creates your evidence folder,
   and the page shows where it is.
3. **Write the files the quest asks for.** The **Required evidence** list on the quest page
   names each file and the folder it goes in. Your copy of the quest is the
   `golden-thread-quest` folder in your home folder. To open it, type
   `open ~/golden-thread-quest` in a terminal on a Mac, or `xdg-open ~/golden-thread-quest`
   on Linux.
   - The files are plain text. Any plain-text editor works. On a Mac, TextEdit works if you
     choose **Format → Make Plain Text** before saving. Visual Studio Code, which is free,
     is easier if you have it.
   - Fill in the `PROOF.md` file in your evidence folder. It tells the reviewer what you
     did and where to look.
4. **On the evidence page, run the check.** A failing check is not a failed quest. It tells
   you what to fix.
5. **Click Mark evidence ready, then Record local validation, then tick the box and click
   Submit for review.** If a required file is missing, the page says which one.

**Redacting.** Where a quest asks for redacted output, write `[REDACTED]` where the value
was, with nothing straight after it: `token: [REDACTED]`. If the check still flags the
line, reword it as "the token was redacted".

**The second quest.** After the transcript quest is verified, the home page recommends
Base Camp. After Base Camp it may suggest a Jira quest, which needs a Jira account; that one
is not part of the pilot.

## Step 3: Hand in your work

After you click **Submit for review**, open a second terminal window and type:

```
gtq hand-in
```

You will see **"Handed in. Your pull request is open."** and a link. The link is your
pull request: it is how your reviewer sees your work. You do not need to do anything on
that page.

If it also says **"Not sent"** and lists files, those files are named like passwords or
keys (for example `something.token`, or anything in a `secrets` folder), so they are never
handed in. If one of them is a file the quest asks for, take any secret out of it, save it
under the name the evidence page shows, and run `gtq hand-in` again.

Then post in the pilot's Slack thread that a quest is ready for review.

While a quest is waiting for review, try to leave its files alone. If you do change one,
run `gtq hand-in` again so your reviewer sees the latest version.

## Step 4: Get your review back

When your reviewer says in Slack that they have reviewed it, type:

```
gtq get-review
```

It shows the decision, for example **"ba-ingest-transcript: Verified"**. Reload the
application in your browser to see it there, or type `gtq start` if it is not running.

- **Verified** means that quest is done, and the next one unlocks.
- **Needs changes** means the reviewer's findings are at the top of the evidence page.
  Click **Resume after review** and fix what they listed. Then do step 2.4 and 2.5 again:
  run the check, click **Mark evidence ready**, **Record local validation** and **Submit
  for review**. Then run `gtq hand-in` again.

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

- **"gtq: command not found".** Close the terminal window and open a new one. Setup adds
  `gtq` for new windows. If it still happens, type `~/.local/bin/gtq start` instead.
- **"Not handed in" or "Review not brought in".** The message says why, and nothing was
  lost. "Nothing is waiting for review" means you have not clicked **Submit for review**
  yet. For a connection problem, run the same command again once you are back online.
- **The application says the port is taken.** It is probably already running in another
  terminal window. Use that one, or stop it there with Ctrl-C.
- **An action on a page is refused.** The red notice at the top of the page says why, and
  nothing changed.
- **Anything else.** Ask in Slack. A screenshot of the page, plus the last few lines in
  the terminal, is enough to go on.

The known limitations are listed in `docs/RELEASE-NOTES.md`.
