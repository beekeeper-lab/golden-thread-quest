# Pilot Lead Guide

For the person running the pilot: you invite the participants, review their work, and
collect their feedback. Participants follow `docs/guides/PILOT.md`.

## 1. The invitation

Participants are business analysts and manual testers. Setup is one pasted line
(`install.sh`), and hand-in and review pickup are one command each, so they need no Git.

**Before you send it, ask each participant which computer they use.** Setup works on a Mac,
on Linux, and inside WSL on Windows. It does not install WSL, and native Windows is not
supported yet. A Windows participant needs WSL set up already, or a Mac to borrow.

Fill in the date and paste this into Slack. The link points at the pilot guide exactly as
tagged for 0.2.2, so it will not change under anyone.

> Hi all, I'd love your help with a short pilot of *The Golden Thread Quest*. It's a
> self-paced training app for AI Context Engineers: the people who connect what was asked
> for to delivery that has been checked. It runs locally on your own machine.
>
> *What:* one required quest (one to two hours) and one optional one.
> *When:* by *<date>*.
> *You need:* a Mac or Linux computer (on Windows, tell me first) and a free GitHub account. No coding: setup is one line you paste, and
> the guide walks you through it.
> *Start here:* https://github.com/beekeeper-lab/golden-thread-quest/blob/v0.2.2/docs/guides/PILOT.md
>
> Your work is stored on GitHub where anyone can read it, so please use made-up material
> only. At the end I'll ask five quick questions. Anything confusing is exactly what I want
> to hear. Reply here or DM me. Thanks!

Two weeks is a reasonable window. Post the invitation as a thread, so hand-ins and questions
stay together.

## 2. Set up your review copy (once)

This is a separate clone. It never touches your working copy of the repository.

1. `git clone https://github.com/beekeeper-lab/golden-thread-quest ~/gtq-review`
2. `cd ~/gtq-review`
3. `make setup`

You also need the GitHub CLI signed in: `gh auth status`.

## 3. Review a hand-in

A participant posts in the thread when a quest is ready. Each participant has one pull
request, titled `Pilot: <name>`, which their `gtq hand-in` opened.

1. `cd ~/gtq-review`
2. `gh pr list`, and note the pull request's number.
3. `gh pr checkout <number>`
4. `make serve`, then open <http://127.0.0.1:8765/review/>.
5. Open the quest and read the evidence. `docs/guides/REVIEWER.md` says what to check.
   Record **Approve**, with a verification statement, or **Needs changes**, with at least one
   finding.
   If the page says the evidence changed since it was submitted, it did: the participant
   edited it after submitting. Ask them why before you tick the acknowledgement box.
6. Stop the service with Ctrl-C.
7. `git add participant/`
8. `git commit -m "Review: <quest-id>"`
9. `git push`
10. Reply in the thread with the decision. The participant then runs `gtq get-review` to
    see it.

`git push` in step 9 goes to the participant's branch, which works because their pull
request allows edits by maintainers, which `gtq hand-in` leaves on. If the push is refused,
ask them to tick **Allow edits by maintainers** on the pull request page.

**Never merge a pilot pull request.** Its evidence belongs to the participant, not to the
program's `main`.

Switching between participants is only `gh pr checkout <other number>`. Each branch carries
that participant's own `participant/` folder.

## 4. During the pilot

- Fix nothing mid-pilot unless it stops a participant from continuing. Everything else goes
  to `docs/PARKING-LOT.md`, so the pilot tests one version.
- Note where people get stuck, even if they get past it. Hesitation counts.
- If someone's setup fails, the last lines of their `make setup` or `make serve` output are
  what is needed.

## 5. Ending the pilot

1. Collect each participant's answers to the five questions in `PILOT.md`.
2. Close each pilot pull request without merging.
3. Bring the answers, your own notes from reviewing, and anything you parked to Gate 2. The
   pilot report is written from those, and it chooses what comes next among Phases 3 to 7 of
   `docs/design/07-status-and-remaining-work.md`.
