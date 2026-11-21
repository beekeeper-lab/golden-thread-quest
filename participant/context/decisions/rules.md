# Decision log rules

The rules for `participant/context/decisions/log.md`, from the context-decision-log quest. The
project is made up: the demo shop in `participant/tests/playwright/demo-app/` (one event, the
Spring Concert, $25.00 a ticket plus a $2.50 service fee per ticket). Every person, meeting and
work item named here is invented. Decisions by Tom Carter; wording drafted with Claude (Claude
Code), 11-19-2026.

The checker (`participant/tools/decision-check.mjs`) reads the **Who may approve** table below, so
the people a reader sees here are the only people it accepts as approvers.

## The three kinds of entry

Every entry has exactly one status:

- **decision**: approved by a person with the authority to approve it, in writing. It is in force
  until another decision replaces it.
- **proposal**: an idea someone has put forward. However many people like it, it is not decided.
- **question**: something nobody has answered yet.

## What makes an entry a decision

An approval needs **both**:

1. **A named approver with authority** for that kind of decision, from the table below.
2. **A written record** of their approval: a line in the meeting notes or a comment on a work item
   in which that person approves it, saying what it covers:
   "Approved by Avery Lane (area: fees): …", and, when it applies, which proposal it promotes or
   which decision it replaces ("(area: ticket limits; replaces: D-02)"). The entry quotes that line
   exactly, names where it is, and must agree with it: the same approver, area, proposal and
   replaced decision, and the date the record was made.

**People agreeing is not an approval.** "Everyone agreed", "sounds good" or a nod in a meeting
leaves the entry a proposal until someone with authority approves it in writing. Nobody records a
decision on someone else's behalf: the approval must be in the approver's own words.

## Who may approve

| Approver | Role | May approve |
|---|---|---|
| Avery Lane | Product owner (made up) | `fees` `ticket limits` `pages` |
| Sam Ortiz | Tech lead (made up) | `calculation` |

Each decision names its **Area**, one of: `fees` (prices and fees), `ticket limits` (how many
tickets an order may have), `pages` (what the shop's pages show or let a buyer do) and
`calculation` (how amounts are worked out and stored). The area is the one the **record** gives,
not one the log entry chooses. A decision approved by anyone else, or by one of them outside their
areas, is not a decision. Replacing a decision takes it out of force, so the replacement's approver
must also be allowed to approve the replaced decision's area.

## How a proposal becomes a decision

Entries are never rewritten, like lines in a checkbook. When a proposal is approved:

1. a **new decision** entry is added, with `From: P-nn`; its approval record must say
   `promotes: P-nn`;
2. the proposal stays as it was, and gets one added line: `Became: D-nn`.

## How a decision is replaced

1. a **new decision** entry is added, with `Replaces: D-nn`; its approval record must say
   `replaces: D-nn`;
2. the old decision stays as it was, and gets one added line: `Replaced by: D-nn`.

The only lines ever added to an existing entry are `Became` and `Replaced by`. Nothing in an entry
is ever changed or removed.

## The current decisions

The **Current decisions** list at the top of the log shows only the decisions in force: those not
replaced. For each it shows the approver's own approved words, not the entry's title, so what a
reader sees as decided is exactly what was approved. Each approval backs one decision only. Nobody writes it by hand: the checker builds it from the entries
(`node participant/tools/decision-check.mjs --write-view`), and only when every other check passes,
so it can never show an entry that isn't a valid decision. It writes the result to `log.md.new` and
never replaces `log.md` itself. It prints the SHA-256 of the `log.md` it read; whoever moves
`log.md.new` into place first checks that `log.md` still has that SHA-256. If it doesn't (someone
edited it in between), or a `log.md.new` is left over from an earlier run, they delete `log.md.new`
and run `--write-view` again; an old one is never moved into place. A decision's title is exactly its approver's words, so its heading can't say
more or less than was approved.

## Work items

The work-items table in `sources.md` is where work and decisions are linked: each made-up work
item names the decisions it rests on. New work is a new row, so no decision entry is ever rewritten
to link it. A decision may also list the work it affected when it was written (`Affects: SHOP-nn`,
or `none`): a snapshot, like the rest of the entry. Each item it lists must be in the table and, while
the decision is in force, rest on it; work added later appears only in the table.

A work item must rest on a decision in force, never on a proposal, a question or a replaced
decision: that is how an idea quietly becomes "the decision" without anyone approving it. Only a
proposal can be promoted to a decision; a question is answered by a new proposal or decision.
