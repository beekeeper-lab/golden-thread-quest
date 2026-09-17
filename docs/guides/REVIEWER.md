# Reviewer Guide

## Before anything else: start the service

```bash
make serve
```

Reading evidence works from the generated pages alone. **Recording a decision does not** — it
writes files, so like every other state change it happens through the running service. A
page built by `make build` shows the evidence and says "Start the local service to record a
decision" where the form would be.

Open `/review/` for the queue, then the quest you are reviewing.

## What you are deciding

Whether the evidence in front of you demonstrates the quest's outcomes strongly enough to
be called verified. Automated checks establish facts and support that judgment. They cannot
make it, and the application will not let them.

## Before you decide

The reviewer page shows the participant, the quest and its version, the attempt, the
submission and the evidence hash at the moment it was submitted. Check:

1. **Has the evidence changed since submission?** The page says so plainly. If it has,
   re-read it. Approving changed evidence means approving something you have not seen, and
   the application refuses unless you acknowledge the change.
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
