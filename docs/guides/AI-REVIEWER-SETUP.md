# Setting up the automatic reviewer

For the program owner. The reviewer is specified in
`docs/design/08-ai-reviewer-specification.md` and decided in ADR-046. Everything is already in
the repository; this guide is the three things only you can provide, and how to turn it on.

## 1. Install the timer on Forge (once)

The reviewer runs on Forge (ADR-047). It uses Forge's own `claude` login for the model and `gh`
login (`beekeeper-lab`) to push, so there is no API key or bot account to create. For a safer push, create a fine-grained token for the program repository only (Contents and Pull requests: read and write) and put it in the env file as `PILOT_BOT_TOKEN`; otherwise the broad `gh` token is used. Run these one
at a time from a checkout of the repository on Forge.

- `mkdir -p ~/.local/share/gtq-reviewer ~/.config/systemd/user`
- `cp tools/forge_review.py ~/.local/share/gtq-reviewer/`
- `cp deploy/forge/gtq-reviewer.service deploy/forge/gtq-reviewer.timer ~/.config/systemd/user/`
- `cp -n deploy/forge/gtq-reviewer.env.example ~/.config/gtq-reviewer.env`
- `systemctl --user daemon-reload`
- `systemctl --user enable --now gtq-reviewer.timer`
- `loginctl enable-linger $USER` (so the timer runs with nobody logged in; skip if already set)

`forge_review.py` is the only file copied to the server; everything else it runs comes from a
fresh clone of `main` on each run. After the runner itself changes, copy it again.

It pushes to a participant's branch because their pull request allows edits by maintainers,
which `gtq hand-in` leaves on.

## 2. Optional: phone notifications

Put `NTFY_URL=<your ntfy topic URL>` in `~/.config/gtq-reviewer.env`. You are pinged when a
hand-in needs a person, and in shadow mode when the reviewer would have approved or asked for
changes.

## Modes

Set `PILOT_AI_REVIEW_MODE` in `~/.config/gtq-reviewer.env` (the next run picks it up):

| Value | What it does |
|---|---|
| `off` | Nothing runs. |
| `shadow` (default) | Reviews every ready hand-in and labels it `gtq:ai-approve`, `gtq:ai-changes` or `gtq:needs-human`, with the reasoning in the journal. **Writes nothing to the participant's branch.** You still decide, so you can compare. |
| `live` | Records the review (the pull request then shows `gtq:reviewed`; the reviewer's own labels are shadow-mode only), pushes it to the participant's branch, posts a GitHub review (approve or request changes), and the participant is emailed. Approved quests count their XP when the participant picks the review up. |

Start in `shadow`. When the reviewer's label agrees with your own decision on ten hand-ins in a
row, set `live`. Optional settings in the same file: `PILOT_AI_SAMPLE_EVERY` (default 0, off; N sends one approval in N
goes to you anyway), `PILOT_AI_SAMPLE_SALT` and `PILOT_AI_MODEL` (default `claude-opus-5-5`).

## What you will see

- **`gtq:needs-human`**: yours. The reasons are in the journal and the comment the participant
  got. Review as before; pushing your decision clears the label.
- **`gtq:ask-human`**: a participant added it to ask for a person. The reviewer skips it.
- `journalctl --user -u gtq-reviewer -n 50` lists, for each pull request, what was decided and why.
- To review one now: `python3 ~/.local/share/gtq-reviewer/forge_review.py --pr 27`, or `systemctl --user start gtq-reviewer.service` to sweep.

## Overruling it

Its decisions are ordinary review records. To change one, record your own decision on the quest
the way `docs/guides/REVIEWER.md` says; yours supersedes it, and the earlier decision is archived
beside it so the participant can see both.

## If it stops working

The timer polls every ten minutes, so a missed run recovers by itself, and a Forge that was off
catches up when it is back. `systemctl --user list-timers gtq-reviewer.timer` shows the next run.
Turn it off with `PILOT_AI_REVIEW_MODE=off`, or `systemctl --user disable --now gtq-reviewer.timer`.
The `Pilot AI review` workflow remains as a manual fallback that needs the repository secrets
`ANTHROPIC_API_KEY` and `PILOT_BOT_TOKEN`; nothing triggers it.
