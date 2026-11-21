# Decision: how the agent reaches Jira

Decided by Beau Brown on 2026-11-18. Written by an AI assistant (Claude) at his direction. The comparison this
rests on is `participant/context/jira/access-comparison.md`, and the marks like [S1] below point to its list of
sources.

This is a decision on paper. No connection to Jira was made, no account was created and nothing was set up.

## The purpose

An unattended agent that keeps one team's Jira project up to date. It runs on a schedule with nobody watching.
It reads the stories in one Jira Cloud project, and creates and updates stories in that project. It works for
a team and should not depend on any one person.

## The decision

**The agent reaches Jira through the REST API, signed in as an Atlassian service account.**

In practice that means:

- An organization admin creates a service account for the agent. It is "not associated with a person" [S1].
- The service account is given access to the one Jira project and nothing else.
- Its credential is scoped to reading and writing Jira stories, with delete left out [S2].
- The agent's code gets the credential from an environment variable or a secret store when it runs. It is never
  written into a file, a log or a screenshot.
- The code offers the agent a small fixed set of operations: read stories, create a story, update a story.

## The reason

Held against what the purpose makes important:

1. **Whose name is on each change.** The service account's. The team can see that the agent made a change, and
   no person is shown as having made it.
2. **Turning it off.** The service account's credential is revoked, or the account is deleted. No person's
   sign-in or token is involved, so no person's work stops [S2]. The documentation says revoking a token can
   take up to 10 minutes.
3. **How far it can reach.** It is limited twice. Scopes limit the kinds of action, so the credential cannot
   delete. The account's Jira permissions limit it to the one project. A credential cannot be limited to a
   project by itself, so the second limit depends on the account being given no other access [R3].
4. **Running with nobody there.** It needs no browser and no approval while it runs. What can happen is fixed
   by the code, not chosen by the model while it runs. Text in a story cannot add an operation that the code
   does not have.

A fifth reason is failure. The code sees every status and header, so it can wait when Jira says it is limited
and can tell a short or failed answer from a good one [R8].

## What it costs

- **The team owns the code** and has to keep it working as Jira changes. This is the most maintenance of the
  four methods.
- **Safety is only as good as that code.** Atlassian does not document a repeated create as safe [R9], so the
  code must not send a create again after a timeout unless it can tell that the first did not land.
- **The credential has to be replaced** before it expires, at most a year after it is made [S2].
- **The record of what the agent did is thinner than with MCP.** Jira's history shows each change and who made
  it [R4]. There is no central log of each call unless the code writes one.

## What was not chosen

- **MCP with a service account** was second. It has the better record, because every tool call is logged by
  Atlassian [M5], and no Jira code to keep. It was not chosen because the model picks the action while it runs,
  from what it has just read, and Atlassian's advice for making that safe is a person reviewing changes [M1].
  This purpose has no person present. Its route for running with no browser was also announced a week before
  this decision [M4].
- **The CLI** was not chosen because it gives the agent a shell and a delete command [A3], and because the
  documentation does not say that a service account can sign the tool in [A1] [S2].
- **A managed connector** was rejected most firmly. Its documented way of running unattended acts as one
  person [C4]. The reasons are in the `PROOF.md` of the attempt.

## What would change this decision

- **A person is present to approve each change.** The purpose would then be a different one, and MCP or a
  connector would fit it better, since both are built around a person approving.
- **The team cannot maintain code.** A method that someone else maintains would be worth its weaker points.
- **Service accounts are not available to the team.** The documentation gives five free to an organization and
  more with Atlassian Guard or Enterprise, but one part of that page reads as if a paid plan is needed [S1]. If
  the team cannot have one, the nearest substitute is an ordinary account kept only for the agent, which costs
  a seat.
- **MCP's unattended route proves itself**, and the agent's runner can hold the model to a fixed set of tools.
  The better record would then count for more.
- **Atlassian lets a credential be limited to one project.** That would close the gap in reason 3 for every
  method, and would be worth a fresh comparison.
- **The agent needs to delete.** The reach in reason 3 would no longer be narrow, and the decision should be
  looked at again before delete is switched on.

## Not checked

- Nothing here was tried. Whether a service account can be created on the team's plan, and whether a credential
  scoped this way can create and update stories in one project, is from the documentation only.
- The documentation was read by research agents through a tool that summarizes pages. See "Sources" in the
  comparison.
