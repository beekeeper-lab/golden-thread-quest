# Specification: automatic review of pilot hand-ins (ADR-045, ADR-046)

Status: specified and implemented 2026-10-29. Owner decision: 2026-10-29, "I do not mind if AI
does the approval, I think this is the preferred option anyway."

## 1. Goal

When a participant hands in work (a pull request from a `pilot/*` branch of their fork), the
program learns of it, reviews it, and answers with no person in the loop:

- If the evidence shows the quest's acceptance criteria are met, the reviewer **approves**: the
  attempt becomes `verified`, and the quest's XP counts as verified XP.
- If not, the reviewer records **needs changes**: no XP, with findings the participant can act on.
- The participant receives the feedback in **the pull request** (a comment and a GitHub review)
  and **in the app** (the evidence page's findings, after "Check for my review").
- Anything the reviewer should not decide alone goes to a person, with a notification.

Out of scope: merging a pilot pull request (never; ADR-045), changing the XP rules (ADR-011:
verified XP exists only from an approved review), and any participant-side change beyond what
ADR-045 already added.

## 2. Principles

1. **Only a recorded review produces verified.** The reviewer uses the same
   `quest-app action record-review` every human reviewer uses, with every guard it has.
2. **Evidence is untrusted text.** The model sees it as data, has no tools beyond returning a
   verdict, and cannot act. A person's or program's code decides what is written.
3. **Approval must be earned in checkable terms.** The model must quote the evidence that
   satisfies each acceptance criterion, and each quote must appear verbatim in a participant
   file. A model that is fooled, lazy or wrong cannot produce quotes that do not exist.
4. **Doubt goes to a person.** `needs changes` is safe and automatic. Approval is automatic only
   when every gate passes; everything else escalates.
5. **Credentials are split.** The job that holds the model key cannot write. The job that can
   write holds no model key and reads only a validated plan.
6. **Never run what a participant wrote.** The reviewer reads files. Quests whose proof depends
   on participant code run by a person escalate.

## 3. Architecture

```
participant: gtq hand-in  ->  PR  fork:pilot/<name> -> upstream main
                                  |
        pilot-precheck.yml  (pull_request_target; reads files as data)
          labels, plain comment, gtq:ready-for-review
                                  |
        forge_review.py       (systemd timer on Forge every 10 min; ADR-047)
          select  : which PRs need a verdict
          review  : [claude login, no GitHub token] tools/ai_review.py review --backend cli -> plan
          apply   : [gh login, no model]            tools/ai_review.py apply  <- plan
                       live    : record-review, push to fork branch, GitHub review, labels
                       shadow  : labels + job summary + notification, writes nothing
                       escalate: label gtq:needs-human, notification
                                  |
        push to fork branch -> pilot-precheck.yml runs again -> new PR comment (emails the
        participant) -> participant: app "Check for my review" -> verified state and XP
```

Trigger: a systemd timer on the owner's server (ADR-047) runs `tools/forge_review.py` every ten
minutes. It selects each open pilot PR labelled `gtq:ready-for-review` with a submitted attempt
and no verdict, so a missed run is recovered by the next. `forge_review.py --pr N` reviews one by
hand. The `pilot-ai-review.yml` workflow is a manual fallback with the same three commands, using
repository secrets; nothing triggers it.

## 4. Modes

`PILOT_AI_REVIEW_MODE` (the server's `~/.config/gtq-reviewer.env`; a repository variable for the manual workflow):

| Value | Behavior |
|---|---|
| `off` | Nothing runs. |
| `shadow` (default when unset) | The reviewer produces a verdict and the plan. It labels the PR `gtq:ai-approve`, `gtq:ai-changes` or `gtq:needs-human`, writes the job summary and notifies the owner. **It writes nothing to the participant's branch and posts nothing to them.** |
| `live` | Applies the plan: records the review, pushes it, posts a GitHub review, labels. |

The owner switches to `live` after the reviewer agrees with the human decision on 10
consecutive hand-ins (`docs/guides/AI-REVIEWER-SETUP.md`).

## 5. The review bundle

For one submitted attempt, built from the base repository's content and the participant's
files, read as data:

- The quest: title, summary, outcomes, numbered acceptance criteria, required proof (id,
  description, location), risk notes, and its safety-constraints text.
- The pre-check result for the attempt.
- Every file in the attempt's evidence package plus every declared proof path outside it, as
  text, each bounded (30,000 characters; 300,000 in total). Binary files are listed by name
  and size only. Truncation is recorded.
- The participant's code files in those locations, listed.

The prompt marks the evidence as untrusted data between per-run random delimiters and tells the
model that any instruction inside it is evidence of an attempted manipulation, not a task.

## 6. The model's output

One structured result, returned through a single schema-constrained function with no side effect:

```
decision:            "approved" | "needs_changes" | "uncertain"
verification:        string  (what was checked and how; at least 20 characters)
criteria:            [{ id, met: bool, quotes: [{file, text}], note }]  one per acceptance criterion
findings:            [{ severity, summary, evidence, criterion?, required_change? }]
injection_suspected: bool
```

## 7. The gate (code, no model)

The plan is the model's output passed through these rules, in order. The first that applies
decides.

| # | Condition | Plan |
|---|---|---|
| G1 | Appeal label `gtq:ask-human` present, or mode `off` | skip |
| G2 | No submitted attempt without a review | skip |
| G3 | Pre-check status is not `ready-for-review` | skip (the participant fixes it first) |
| G4 | Quest risk is `external_write` | escalate |
| G5 | Required proof of type `screenshot`, `demonstration` or `review`, or any proof file that is an image or PDF | escalate |
| G6 | The attempt's proof depends on participant code (a code file in the evidence package or in a declared proof path) | escalate |
| G7 | Any file was truncated or unreadable, or the quest lists no acceptance criteria | escalate |
| G8 | Evidence contains instruction-like text aimed at a reviewer, or the model says `injection_suspected` | escalate |
| G9 | Model call failed, or its output does not match the schema | escalate |
| G10 | Model said `uncertain` | escalate |
| G11 | Model said `approved`, but a criterion is not `met`, has no quote, or has a quote not found verbatim in the named file | `needs_changes` with a finding per failing criterion (an approval that cannot be grounded is not an approval) |
| G12 | Model said `approved`, all criteria grounded | if the sampling rule picks it: escalate, else **approve** |
| G13 | Model said `needs_changes` | `needs_changes` with its findings (at least one; a model finding is required to cite evidence) |

Grounding rules for a quote (G11): at least 20 characters, found word for word (whitespace
aside) in the file it names, not merely the criterion's own words, and no single line may be
offered as the proof of more than three criteria.

Sampling rule: one in `PILOT_AI_SAMPLE_EVERY` approvals (default 5), chosen by a hash of the
submission id salted with a secret the participant does not have (`PILOT_AI_SAMPLE_SALT`, else the
model key), so a re-run picks the same ones and a participant cannot choose an id that dodges it.

## 8. Applying a plan

`approve` / `needs_changes` in live mode:

1. Fetch the participant's `participant/` folder as data and delete links (as the pre-check does).
2. Run `quest-app action record-review --quest Q --decision D --reviewer "Claude (automated
   reviewer)" --statement S [--finding ...] --confirm` against that folder, with generated and
   local-data folders redirected to a temporary directory. The application's own guards
   (statement length, findings, changed-evidence, secret scan on approval) apply, and a refusal
   turns the plan into an escalation.
3. Clone the participant's fork branch with the bot token, copy only the files the review
   changed, and only paths under `participant/`, commit as the bot (`Review: <quest-id>`), and
   push. A push that is not a fast-forward is abandoned; the next run reviews again.
4. Post a GitHub review on the pull request: approve, or request changes, with the summary.
5. The push makes the pre-check run, which sets `gtq:reviewed` and clears the reviewer's own
   labels, so a live decision adds none (shadow mode does, `gtq:ai-approve` / `gtq:ai-changes`).

A plan that loses a race (the branch moved, or the attempt was already decided by another run) is
skipped, not escalated; a crash, a timeout or a deleted fork escalates. The commit is made by the
bot's own account (its login and no-reply address are read from the token), so GitHub attributes
it to the bot and the pre-check can tell it from the participant's.

The push triggers the pre-check, which posts a new comment announcing the decision (it trusts
a decision when a commit by someone other than the PR's author is on the branch, ADR-045). The
comment includes the verification statement or the finding summaries, filtered for the markup
and mentions (`tools/precheck.py::_safe`).

Escalation: label `gtq:needs-human`, one comment to the participant ("A person will review this
by hand; you do not need to do anything"), notification to the owner.

## 9. Security

- On the server (ADR-047) the model runs through `claude -p` with every tool off, no settings, no
  session and an empty working folder, in a process whose environment holds no GitHub token. The
  apply process gets the `gh` token, no model access, and reads only `plan.json`, which it
  validates against the schema again and whose every path and string it constrains. Both run as
  the owner's operating-system user, so the split is by process, not by credential store.
- Each run executes a fresh clone of `main`, never a working checkout, and neither process
  executes participant files. The apply step's only participant-derived action is
  `record-review`, which parses them.
- Commits are made under the owner's GitHub account (the recorded reviewer name stays "Claude
  (automated reviewer)"). The manual workflow fallback uses a bot token instead.
- Model-authored text is never placed in a shell command. It reaches files through the
  application's own record-review and the comment through `--body-file`.
- A participant can make the reviewer escalate (by instructing it) and cannot make it approve:
  approval needs verbatim quotes that satisfy the criteria, and the rest of the gate is code.
- Residual risks, accepted: a participant who fabricates convincing evidence files (a faked log)
  passes a reader that does not rerun the work; the sample and the per-quest escalations are the
  control, and a person can overturn any decision. Commit authorship is unsigned (ADR-045).

## 10. Configuration the owner provides

On the server, `~/.config/gtq-reviewer.env` (template `deploy/forge/gtq-reviewer.env.example`):

| Item | Purpose |
|---|---|
| `PILOT_AI_REVIEW_MODE` | `off`, `shadow` (default) or `live` |
| `PILOT_AI_SAMPLE_EVERY` | Sampling rate, default 5 |
| `PILOT_AI_SAMPLE_SALT` | Salt for the sample (optional but recommended) |
| `PILOT_AI_MODEL` | Model id, default `claude-opus-5-5` |
| `NTFY_URL` | Pings for escalations and shadow verdicts (optional) |

The server's `claude` and `gh` logins supply the model and the push access. The manual workflow
fallback instead reads the repository secrets `ANTHROPIC_API_KEY` and `PILOT_BOT_TOKEN`.

With the model unavailable the reviewer escalates instead of failing silently.

## 11. Acceptance criteria

1. A hand-in that passes the pre-check is reviewed without anyone asking.
2. A grounded approval records `approved`, the quest becomes `verified` when the participant
   picks the review up, and its XP counts as verified XP.
3. A failing hand-in records `needs_changes` with findings the app shows on the evidence page and
   the PR shows as a comment and a requested-changes review.
4. Every gate in section 7 is covered by a test, including a forged quote, an injection attempt,
   an external-write quest, participant code in the proof, truncation and a model failure.
5. In shadow mode nothing is written to a participant's branch.
6. A decision is applied once per submission, and a missed run is recovered by the next one.
7. The process that reaches the model holds no GitHub token (and in the manual workflow no job
   holds both the model key and the bot token), and none runs participant files.
8. The setup guide lets the owner configure it and switch modes without reading code.
