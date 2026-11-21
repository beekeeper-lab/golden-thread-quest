# Decision: how the Tixly follow-up agent reaches Jira

Decided by Tom Carter, 11-02-2026; wording drafted with Claude (Claude Code). Tixly, its team and
its Jira project (TIX) are invented. The methods are compared in
`participant/context/jira/access-comparison.md`; numbers in brackets refer to its sources.

## Purpose

An AI agent that reads the Jira stories assigned to me in the Tixly project and drafts follow-up
stories, which it creates only after I have seen a preview and confirmed it. It reads often, writes
rarely, and never writes without a person's confirmation. This is the preview-and-confirm behavior
from `participant/context/write-preview-rules.md`, pointed at a real tracker instead of a simulated
one.

## Decision

**The REST API, signed in as a service account with its own scoped API token, behind the
preview-and-confirm step.**

- A service account named for the job (for example "Tixly follow-up agent"), not any person's
  account [2].
- Its own API token, with only the scopes needed to read and create stories [1][8], and given
  access only to the Tixly project through Jira's project permissions. A token expires within a
  year at most [1]; I would choose a shorter life, so a forgotten token stops on its own.
- The token is read from an environment variable when the agent runs, never written to a file, a
  log or a preview.
- Every write goes through the preview-and-confirm step first: the agent shows the full change, I
  confirm it by typing its fingerprint, and the story records who confirmed it and when.

## Reason

- **Whose name is on the action:** the agent acts as its own account, not as me or a colleague,
  so its changes are meant to be credited to that account. How Jira's history displays this
  is not verified in the comparison, so I don't rely on the display alone: the confirmation step
  records, in each story, who approved it and when, and the agent keeps its own record of every
  confirmed write.
- **Switching it off breaks nothing else:** revoking the service account's one token stops the
  agent and affects no one's own access [1][2]. That is the scenario's problem solved: no
  personal token to revoke.
- **It can reach only what it needs:** the scoped token and project permissions keep it to reading
  and creating stories in one project, instead of everything a person can do [1][8].
- **A person approves every write:** the confirmation step is my own code, so I decide exactly what
  the preview shows and when a confirmation is refused, instead of relying on an AI tool's approval
  setting.

What it costs: I own and maintain the code, replace the token before it expires, and stay within
the rate limits, slowing down when Jira answers with a 429 [5]. The organization's audit log shows
the service account's activity only on the plans that include it [9], so the agent also keeps its
own record of each confirmed write.

## What would change this decision

- **If the organization can't have another service account** (the free allowance is 5 [2]), I
  would use the managed connector with every write tool set to need approval [14], and accept that
  its changes are credited to me [12][14], stating in each story that the agent drafted it.
- **If the agent were to stay read-only for good** (not just at first), the managed connector
  signed in as me would be enough: with no writes, whose name is on a change no longer matters,
  and there is no code to maintain.
- **If the AI tool I use could show my full preview and require my typed confirmation before each
  write,** I would compare the MCP server with a service-account key again, since Atlassian runs
  the server and I would maintain less. A service account limited to the Tixly project would keep
  it to one project in the same way [11].
- **If the token or the account were ever shared with another job,** I would split them, so each
  job can be switched off on its own.

## Rejected

- **The Atlassian CLI,** most firmly: a public suggestion reports it doesn't accept service-account
  tokens [4], so the agent would have to sign in as a person: with a token, with all of that
  person's permissions [6]. That is exactly the mistake in the quest's scenario.
- **The managed connector signed in as me,** for now: the easiest to set up, but the agent's
  changes would be credited to me [12][14]. It stays the fallback above.
- **The MCP server with a service-account key:** it gives the agent its own account too, but it
  needs an admin to switch on token sign-in [10], and putting my own preview-and-confirm step in
  front of its write tools would mean building a program of my own anyway. That is my judgment,
  not a limit of MCP: with that program to build either way, calling the REST API directly is the
  simpler choice.
