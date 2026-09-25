# Reviewer Guide

## Before anything else: pick your surface

Reading evidence works from the generated pages alone. **Recording a decision does not** — it
writes files, so like every other state change it goes through the application.

### In a browser

```bash
make serve
```

Open `/review/` for the queue, then the quest you are reviewing. A page built by `make build`
alone shows the evidence and says "Start the local service to record a decision" where the
form would be.

### Without a browser

On the installed Cowork app the server runs inside the sandbox and your browser is outside
it, so `make serve` is unreachable. Review through the command line instead. It is the same
code behind the same guards, not a shortcut around them:

```bash
quest-app action record-review --quest <quest-id> \
  --decision approved \
  --reviewer "Your Name" \
  --statement "What you checked and how, in your own words." \
  --confirm

quest-app action record-review --quest <quest-id> \
  --decision needs_changes \
  --reviewer "Your Name" \
  --finding "high:What is wrong:Where you saw it" \
  --confirm
```

`--decision` takes the same three values the browser form posts: `approved`,
`needs_changes`, `rejected`. Repeat `--finding` for each one; each needs all three fields,
`severity:summary:evidence`. Add `--acknowledge-changed-evidence` to approve evidence that
changed after submission, which is the checkbox the browser form shows for the same purpose.

## What you are deciding

Whether the evidence in front of you demonstrates the quest's outcomes strongly enough to
be called verified. Automated checks establish facts and support that judgment. They cannot
make it, and the application will not let them.

## Before you decide

The reviewer page shows the participant, the quest and its version, the attempt, the
submission and the evidence hash at the moment it was submitted. Check:

1. **Has the evidence changed since submission?** The page says so plainly and lists what
   changed: the evidence package, and each declared proof file outside it (a test under
   `participant/tests/`, a document under `participant/context/`). If anything has, re-read
   it. Approving changed evidence means approving something you have not seen, and the
   application refuses unless you acknowledge the change. After you approve, `validate`
   warns if the package or any of those files changes. Submissions and reviews recorded
   before proof files were tracked are checked on the package alone.
2. **What did the validators establish?** Their results are facts about artifacts, not
   verdicts about the work. `inconclusive` means nobody could tell, which is not a pass.
3. **Can you reproduce it?** The proof document should let you, from a clean clone.
4. **Was the secret scan clean?** It is a safety net, not a guarantee. Read the evidence as
   though it might still contain something.

## Deciding

**Approve** requires a verification statement of at least twenty characters, in your own
words, saying what you checked and how. It is the record that the approval was a judgment
and not a formality. Approval is the only thing in this application that produces verified
completion and verified XP.

**Needs changes** and **reject** require at least one finding, with a severity and what you
observed. A decision the participant cannot act on wastes both your time.

`needs_changes` and `rejected` move the attempt to the same state and show the same badge to
the participant — there is no separate "rejected" state. Use `rejected` when you mean the
submission is not close, and `needs_changes` for a smaller correction; the difference is
recorded for history, not enforced by the application.

A superseded decision is archived rather than overwritten, so a participant can see that you
changed your mind and not only the outcome.

## The provenance limitation, stated plainly

Release one identifies you by the display name in the review record and by Git history.
Review records are **not cryptographically signed**. A participant with write access to their
own repository could author a record naming you.

What the application does enforce is internal consistency: a review that does not match the
attempt, an approval with no verification statement, an approval of changed evidence, or a
`verified` state with no approval behind it are all refused. The remaining gap is social, and
it is documented rather than papered over. If your program needs stronger provenance,
review through pull requests so the Git history carries the identity.

## What you should never have to handle

Participant secrets, raw private ticket contents, or credentials. If you find any in an
evidence package, ask for changes and say so — that is itself a finding.
