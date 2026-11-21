# Proof · jira-compare-access-methods

Attempt: `jira-attempt-003`

## How this was made

An AI assistant (Claude) wrote the comparison, the decision record and this file, at Beau Brown's direction.
The work was done in small steps, each shown to Beau before the next.

Beau chose the purpose: an unattended agent working for a team, out of three purposes offered. He asked for
the public documentation to be read before the comparison went further. He chose the method, the REST API with
a service account, after the assistant set out the four methods against the purpose and recommended it.

The approach was: state the purpose first, compare each method on the eight points the quest lists, hold each
against the purpose, then decide.

The facts in the comparison come from two places, and the comparison marks which:

- **Vendor documentation.** Three research agents, started by the assistant, read Atlassian's public
  documentation and, for the managed connector, Anthropic's. Each was asked open questions, told to give the
  page and a short quotation for each answer, and told that "not found" was an acceptable answer. Statements
  from this reading carry a mark such as [R8], and the pages are listed at the end of the comparison.
- **The assistant's general knowledge.** Statements with no mark. These were not checked.

No connection to Jira was made at any point. The agents read public web pages only. They did not sign in to
anything and did not call Jira.

## The method rejected most firmly

**The managed connector, in its per-person form.** Marks like [C4] point to the list of sources at the end of
`participant/context/jira/access-comparison.md`.

The purpose is an unattended agent that works for a team. This is the one method of the four whose documented
way of running unattended is to act as a person.

- **Whom actions are attributed to (criterion 2).** The connector "inherits each person's permissions from the
  connected service" [C3]. Its way of running with nobody present is a scheduled task, which belongs to one
  person's account, and what such a task does through connectors "appears as you" [C4]. So every story the
  agent created or changed would carry a colleague's name. That is the first half of the quest's scenario.
- **Turning it off.** The agent's access is that person's sign-in. To stop the agent, the person's connector is
  disconnected, which also stops their own use of it. If the person leaves or loses access, the agent stops.
  That is the second half of the scenario.
- **Scope of access (criterion 3).** It reaches whatever that person can reach, which for a working team
  member is far more than one project. It can be narrowed with per-tool switches, but no setting that limits it
  to named Jira projects was found.
- **Its named risk (criterion 7)** is the same point: unattended, it runs as a person.
- **Failure.** In a scheduled run, a tool that is set to need approval "may wait for your answer or finish
  without the tool" [C6]. A run could end without having done its Jira work.

The other three methods can each be set up badly, with a person's token. This one is different in kind: for
this purpose, borrowing a person is how it works when it is set up as documented.

What this rejection does not say:

- It is a rejection for this purpose. For a person working at their desk with an assistant, and approving what
  it does, the same connector may be the best of the four. The decision record lists "a person is present to
  approve each change" as something that would change the decision.
- It rests on one vendor's documentation, Anthropic's for Claude. Anthropic is also the maker of the assistant
  that wrote this. Other vendors' connectors were not read.
- The shared-account form of connector does give the agent its own name [C2]. It was set aside for other
  reasons: its token has no scopes, the vendor holds it, and the product it belongs to is made for chat.

## Reflection: the method for an agent that can be trusted only a little

The same method, the REST API with a service account, made smaller. And no longer unattended for writes.

What decides it is one question: at the moment of acting, who chooses what happens? With MCP and with a
managed connector, the model chooses a tool and fills it in. With a CLI, the model writes a command. With the
REST API, the model can only ask the team's code for one of the few things that code offers. An agent that is
trusted a little should be choosing from the shortest list, and the REST API is where the team writes that
list.

A little trust then shrinks three things:

- **The credential.** Read-only scopes to begin with [T1] [S2]. An agent that cannot write cannot write the
  wrong thing, whatever it is told.
- **The list.** Read stories, and nothing else, until it has earned more.
- **The moment of writing.** When writes are added, the agent does not make them. It proposes them, and a
  person confirms a preview of the exact change, as in the write-preview quest. The agent holds the read
  credential and the confirming step holds the write one.

That last point changes the purpose. An agent trusted only a little should not be writing unattended at all,
so the honest answer is partly "a different purpose", not only "a different method".

There is a fair case for MCP here, and it should be said. With a person present, MCP and the connector have
approval built in: each tool can be set to need approval, delete is off by default, and every call is logged
by Atlassian [M5] [M7] [C3]. For a little-trusted agent working beside a person, that is less to build and a
better record. It comes second because approving a tool call one at a time is the thing a tired person waves
through, and because the model still chooses what to put in front of them.

## What was built

Two documents. Nothing was built to run.

- **The comparison**, `participant/context/jira/access-comparison.md`. It states the purpose, compares the
  four methods side by side in one table on eight points, gives each method a section with the detail and the
  sources, and lists the pages read.
- **The decision record**, `participant/context/jira/access-decision.md`. It names the purpose and the method
  chosen, gives the reason and the cost, says what was not chosen, and lists what would change the decision.

## Where the important artifacts are

| What | Path |
|---|---|
| The comparison of the four methods | `participant/context/jira/access-comparison.md` |
| The decision record | `participant/context/jira/access-decision.md` |
| This file | `participant/evidence/jira-compare-access-methods/jira-attempt-003/PROOF.md` |

## How to reproduce the behavior

There is nothing to run. To check the work:

1. Read the table under "The four methods side by side" in the comparison.
2. For any statement with a mark such as [R8], find the page under "Sources" in the same file, open it in a
   browser, and compare. The pages are public and need no sign-in.
3. Read the decision record against the comparison, and see whether the reasons follow from it.

The pages were read on 2026-11-18. Vendor documentation changes, so a page may say something different later.

## What was tested or validated

Nothing was run, so nothing is observed in the sense of a recorded command. Each criterion is met by text, and
the place is given.

| # | Criterion | Where |
|---|---|---|
| 1 | The comparison covers CLI, REST API, MCP and a managed connector. | The comparison: one column each in "The four methods side by side", and sections 1 to 4. |
| 2 | Each method states how it authenticates and who the actions are attributed to. | The first two rows of each method's table, and of the side-by-side table. |
| 3 | Each method states the scope of access it grants. | The "Scope of access" row for each method. |
| 4 | Each method states what is logged and where. | The "What is logged, and where" row for each method. |
| 5 | The decision names a purpose and the method chosen for it. | The decision record, "The purpose" and "The decision". |
| 6 | The decision gives the reason and what would change it. | The decision record, "The reason" and "What would change this decision". |
| 7 | The comparison names a risk of each method. | The "One named risk" row for each method. The four are: a shell is wider than Jira; everything that keeps it safe is code the team writes; the model chooses the action from what it has just read; unattended, it runs as a person. |

The comparison also covers rate limits, maintenance and failure behavior for each method, which the evidence
description asks for and the criteria do not number.

The safety constraints:

- **No connection is made in this quest.** None was. The existing `jira-read-assigned` skill was read as a
  file, to see how Jira is reached today, and was not run.
- **Authenticate through an environment variable or a signed-in CLI.** Nothing was authenticated. The decision
  record says the credential is to reach the code from an environment variable or a secret store and is never
  written to a file.
- **Do not paste a real token or an internal URL.** The three documents contain no token. The only web
  addresses in them are public documentation pages.

Which statements were checked against documentation and which were not is set out under "Remaining
limitations".

## Remaining limitations

Known so far. There may be others.

What could not be done:

- **Nothing was tried.** The quest allows no connection, so every statement about how a method behaves is from
  reading, not from use. Whether a service account can be created on the team's plan, and whether a credential
  scoped to read and write can create and update stories in one project, has not been tried by anyone here.

How far the documentation reading can be trusted:

- **Neither the assistant nor Beau opened the pages.** Research agents did, through a tool that fetches a page
  and summarizes it. Their reports say that quotations should be checked against the page. That check was not
  done. A mark such as [R8] means "an agent reported that this page says so".
- **Statements with no mark were not checked at all.** They are the assistant's general knowledge. The rows
  that lean on it most are: what each method does during a Jira outage, what the CLI does when it is limited,
  how a failed MCP tool call is handled, and rate limits for the managed connector.
- **One finding is a week old.** That a service account can use MCP with no browser was found only in a
  changelog entry of 2026-11-12, not yet in the guide for that feature.

Questions the documentation left open, as the agents reported:

- Whether a scoped token, the only kind a service account can have, can sign `acli` in.
- Where `acli` keeps its sign-in on the machine, and what its exit codes are.
- Whether a story's history tells a change made through the API from one made in a browser.
- Rate limits for Atlassian's MCP server, and whether its log holds the content of a call.
- What a scheduled run through a managed connector does when the Atlassian sign-in has expired.
- Whether service accounts need a paid plan. One page says five are free and also reads as if they are not.
- How long Atlassian's audit log is kept. Two pages give figures that do not fit together.

What the comparison leaves out:

- **One product for each method.** Atlassian's `acli`, Atlassian's own MCP server, and one vendor's connector.
  Community command-line tools, other MCP servers and other vendors' connectors were not read. The connector
  vendor is the maker of the assistant that wrote this.
- **Jira Cloud only.** A Jira run on the team's own servers authenticates differently and was not looked at.
- **Cost.** Seats, plans and credits are mentioned where the documentation raised them, and not compared.
- **Neither stretch goal was done.** No fifth method was added. Outage behavior is touched on in each
  "Failure behavior" row, mostly from general knowledge, and is not the fuller account the stretch goal asks
  for.

What would be done next: open the dozen or so pages the decision rests on and check the quotations by eye, then
try the decision for real in a test project, starting with whether the service account can be created.

## Sensitive values

None. The three documents contain no token, password, key or cookie. No Jira site address appears, real or
made up. The web addresses in the comparison are public documentation pages of Atlassian and Anthropic. No
customer name and no ticket content appears. The only person named is Beau Brown, as the participant.
