# Proof · jira-compare-access-methods

Attempt: `jira-attempt-001`

Decisions by Tom Carter; research and wording drafted with Claude (Claude Code), 11-02-2026. No
connection to Jira was made, and no token was created or used.

## What was built

- **A comparison of four ways an AI agent can reach Jira:** the Atlassian CLI, the Jira Cloud REST
  API, the Atlassian Rovo MCP Server, and a managed connector (Claude's Atlassian connector). It
  covers, for each one, how it signs in, whose name is on its actions, what it can reach, what is
  logged and where, rate limits, upkeep, how it fails, how to switch it off without breaking anyone
  else, and one named risk. Each fact cites one of 21 public vendor pages; anything no page
  confirms is marked "not verified".
- **A decision record** for one purpose: an agent that reads my assigned stories in the invented
  Tixly project and drafts follow-up stories that I confirm before they are created. The choice is
  the REST API with a service account, behind the preview-and-confirm step from the quest
  "Build Preview and Explicit-Confirmation Behavior".

## Where the important artifacts are

| What | Path |
|---|---|
| Comparison | `participant/context/jira/access-comparison.md` |
| Decision | `participant/context/jira/access-decision.md` |

## How to reproduce the behavior

There is nothing to run: the quest is a written comparison. To check it, open the comparison and
follow any numbered source to the vendor's page; each fact was checked against its page on
11-02-2026, and vendor pages change over time.

## How the work meets the criteria

1. **All four methods are covered:** the CLI, REST API, MCP and managed connector each have a
   column in the comparison.
2. **How each signs in, and whose name is on its actions:** the first two rows. Where no vendor
   page states whose name appears, the cell says what it is inferred from and is marked "not
   verified".
3. **The scope of access each grants:** the "What it can reach" row, from everything a person can do
   (a personal, unscoped token) down to chosen scopes in one project (a scoped token with project
   permissions).
4. **What is logged and where:** the "What is logged, and where" row: the issue's history in Jira,
   the organization's audit log (only on plans that include it), and the tool's own logs where
   documented. Where Atlassian's pages disagree on which plans include the audit log, the cell
   says so.
5. **A purpose and the method chosen for it:** the decision record's "Purpose" and "Decision"
   sections.
6. **The reason, and what would change it:** the decision record's "Reason" section, including
   what the choice costs, and its "What would change this decision" section, with four conditions.
7. **A risk for each method:** the comparison's last row names one risk per method.

## The method I rejected most firmly

**The Atlassian CLI** (criteria 2, 3 and 7). It is Atlassian's own tool, but an open public
suggestion reports it doesn't accept service-account tokens, so an agent using it has to sign in
as a person, with that person's credential. With a token, the agent can do everything that person
can do; with a browser sign-in, its reach isn't documented. Its changes would be made in that
person's name (how Jira's history shows them is not verified), and a dedicated token can be revoked
without breaking other tools, but only if nobody reuses it. That is the quest's scenario: an agent
working with a person's credential instead of its own. Its other problems (manual
upgrades, each version supported for only 6 months) are smaller next to that one. If Atlassian
adds service-account support, I would compare it again.

## Reflection

**Which method would I choose if the agent could only be trusted a little?**

If the agent could only be trusted a little, the most important protection for me is that a
person approves every change before it happens, so nothing is approved automatically and a
mistake is caught before it reaches Jira. I would combine that with keeping its reach small (one
project, only what it needs) and having one switch that turns it off without breaking anyone
else's access.

I would also start it read-only: no writes at all until its drafts show it understands what I ask.
Only then would it create stories, still through the approval step. The method stays the same,
the REST API with a service account: it can start with a token that can only read, and later have
it replaced by one that can also create stories, without involving anyone else's account. A
token's scopes can't be changed after it is created (source 8 in the comparison), so widening its
access means a new token.

The method I would trust least is the CLI, because it would have to run on a person's own token,
with all of that person's permissions.

## What was tested or validated

- **Every fact has a source,** numbered in the comparison and listed with its address.
- **A second, separate check** opened nine of the key pages and compared each claim with what the
  page says. Five matched exactly. Four were stated more broadly than the page supports, and were
  corrected:
  - a departed person's tokens keep working only while their account still has access to the
    site;
  - tokens created before 12-15-2024 were set to expire in 2026, not "given an end date because
    they had none";
  - disconnecting the connector signs out the member's own account, not "only that member";
  - the burst rate limits apply per site and per endpoint, and the page says API-token traffic
    falls under them in a notice rather than in the limits section itself.
- **Statements no page confirmed are marked "not verified"** instead of being stated as fact, for
  example exactly how Jira's history shows an action made through an app.
- **Copilot review** in a practice pull request in my own fork, over 3 rounds: no High findings;
  5 Medium and 3 Low, all fixed. Every one was a statement stronger than its source supports, for
  example the decision promising whose name Jira would show, which the comparison marks as not
  verified. The final round listed no issues.
- **The app's secret scan** found nothing. Before that, it had flagged one phrase in the
  comparison that was laid out like a secret being set (the word for a token, a colon, then a
  word); it was reworded rather than excused.

## Stretch goals

Not attempted: a fifth method, and how each method behaves during a Jira outage.

## Remaining limitations

- **Nothing was connected.** The comparison describes the methods from their documentation, as the
  quest asks; behavior in a real Jira site wasn't observed.
- **Documentation changes.** The facts are as of 11-02-2026, and some features are new or in
  progress (for example the CLI's service-account support, and Atlassian's MCP pages, which
  disagree on audit-log plans).
- **Some points are unconfirmed,** each marked "not verified" in the comparison: how Jira's history
  displays an action made through an app or a service account, the CLI's local logs and rate-limit
  category, what a CLI browser sign-in can reach and what its logout revokes, whether Jira's own
  limits also apply to the MCP server, and the connector's own logs. The decision doesn't rely on
  the history display: the confirmation step records who approved each write.
- **The managed connector compared is one product.** Other hosted connectors (for example
  automation services) may behave differently; comparing one was the stretch goal not attempted.
- **The decision is for an invented project.** In a real organization, the service account, its
  scopes and the project permissions would need an administrator.

## Sensitive values

No secret, token, password, customer name, internal address or private ticket content is in this
hand-in. Tixly and its Jira project are invented; every link is to a public vendor documentation
page.
