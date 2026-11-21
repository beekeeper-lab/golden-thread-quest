# Jira access methods compared

Four ways an agent can reach Jira, compared for one purpose. Written by an AI assistant (Claude) at Beau
Brown's direction.

No connection to Jira was made to write this. Nothing here was checked against a live system. Statements
marked like [A1] come from Atlassian's public documentation, listed under "Sources" at the end. A statement
with no mark is the assistant's general knowledge and was not checked.

## The purpose

**An unattended agent that keeps one team's Jira project up to date.**

- It runs on a schedule, a few times a day. Nobody is watching when it runs.
- It reads the stories in one Jira project, and creates and updates stories in that project.
- It works for a team, not for one person. It should keep working when any one person is on leave, changes
  role or leaves.
- The Jira site is Jira Cloud.

What this purpose makes important:

- **Whose name is on each change.** Other people on the team will see stories appear and change. They need to
  be able to tell that the agent did it.
- **Turning it off.** It must be possible to stop the agent's access at once, without stopping any person's own
  work.
- **How far it can reach.** Nobody is there to stop a wrong action, so what the agent is able to do has to be
  narrow to begin with.
- **Running with nobody there.** A method that needs a person to sign in through a browser, or to approve each
  step, does not fit as it stands.

## The four methods side by side

Each cell is a short form of what the method's own section says below. The sources are given there.

| | 1. CLI | 2. REST API | 3. MCP | 4. Managed connector |
|---|---|---|---|---|
| **How it authenticates** | The tool is signed in once. Unattended: an API token piped in. | Sent by the team's code: an account's API token, OAuth for a person, or a service account's scoped token or 60-minute credential. | Browser approval by default. Unattended: an API token if the admin allows it, or a service account's credential. | Per-person: a browser sign-in. Shared-account: the vendor holds a dedicated account's token. |
| **Whom actions are attributed to** | The account whose token signed the tool in. | The token's owner, the person who approved, or the service account. | The account that signed in or owns the token. | Per-person: that person, also in scheduled runs. Shared-account: the dedicated account. |
| **Scope of access** | All the account can do, delete included. Not narrowed by the tool. | Scopes limit the kinds of action. Jira permissions limit the project. | Never more than the account. Tools in groups, with delete and manage off by default. Also reaches other Atlassian products. | All the account can do, narrowed by per-tool switches: allow, needs approval, blocked. |
| **What is logged, and where** | The story's history in Jira. On the machine, only what the runner keeps. | The story's history in Jira. Token creation and revoking in Atlassian's audit log. Otherwise what the code writes. | Every tool call in Atlassian's audit log, with tool, action and user. | Atlassian's audit log as for MCP. The AI product's log is administrative and Enterprise-only. |
| **Rate limits** | Jira's. What the tool does when limited is not documented. | Published per-second limits. Status 429 with `Retry-After`. | No figure found. Some calls use Rovo credits. | Not found. Two sets apply, neither tunable. |
| **Maintenance** | Install and update the tool. Replace the token yearly. | The most: the team's own code. Replace the token yearly. | No Jira code. Tools can change without notice to the code. | The least: settings and sign-in only. |
| **Failure behavior** | A message, and JSON if asked for. Exit codes not documented. No retry. | The clearest: the code sees every status. A repeated create is not documented as safe. | An error message to the model, which decides what to do. | The least visible: a run may finish without the tool. |
| **One named risk** | A shell is wider than Jira. | Everything that keeps it safe is code the team writes. | The model chooses the action, from what it has just read. | Unattended, it runs as a person. |

## 1. CLI

A command-line tool that the agent runs. The one compared here is Atlassian's own, `acli`. The tool calls Jira
for the agent, so underneath it is method 2 with a wrapper.

| | |
|---|---|
| **How it authenticates** | The tool is signed in once with `acli jira auth login`. There are two ways: approval in a web browser, or an API token read from standard input together with the site and an email address [A1]. An unattended agent cannot use a browser, so it is the API token, piped in from an environment variable or a secret store. Atlassian's guide for automated runs does this with "a bot account" [A2]. |
| **Whom actions are attributed to** | The Atlassian account whose token the tool is signed in with. A token acts with the permissions of the user who made it [T2]. If that is a person's account, the agent's changes are that person's. The tool adds no identity of its own. |
| **Scope of access** | Everything that account is allowed to do, in every project it can see. The tool does not narrow it, and it has a delete command that can delete by query with no prompt (`--yes`) [A3]. A token can be limited to kinds of action (a "scoped" token) [T1], but the `acli` pages show sign-in only with a token "without scopes" and do not say whether a scoped token works [A1]. Narrowing to one project is done in Jira, by what the account is given access to. |
| **What is logged, and where** | In Jira: see method 2, since the tool's requests are Jira requests. On the machine: only what the agent's runner keeps of the commands and their output. The documentation does not describe any log kept by the tool. |
| **Rate limits** | Jira Cloud's limits, as for method 2. The `acli` pages read do not say what the tool does when it is limited. |
| **Maintenance** | The tool has to be installed and kept up to date on the machine the agent runs on. The API token expires: one year by default, and one year at most [T1]. |
| **Failure behavior** | Commands can print JSON (`--json`). An expected error prints a message, and an unexpected one prints a trace id [A4]. Exit codes are not documented. Nothing in the pages read describes a retry, or says how far a command that fails part-way got. During a Jira outage every command fails and nothing is queued. |
| **One named risk** | **A shell is wider than Jira.** To use a CLI the agent must be able to run commands. An agent that can run `acli` can run any of its subcommands, including `acli jira workitem delete --jql ... --yes`, and unless the runner restricts it, any other command on the machine. |

Against the purpose: it can run unattended. Whether it can carry the agent's own name is the open question.
Atlassian's account type made for machines, the service account, can only have scoped tokens [S2], and the
`acli` documentation does not say that a scoped token can sign the tool in. If it cannot, the tool has to be
signed in as an ordinary user account, a person's or a spare one kept for the agent. A person's is the situation in the quest's scenario.

## 2. REST API

The agent's own code sends requests to Jira's web interface and reads the answers. This is what the existing
`jira-read-assigned` skill does, with a person's token and for reading only.

| | |
|---|---|
| **How it authenticates** | Three documented ways for something that is not a Marketplace app. (a) An account's email address and API token, sent with each request [R1]. (b) OAuth 2.0 on a person's behalf: the person approves once in a browser, and the code keeps working with a refresh token, which expires after 90 days without use [R2]. (c) A **service account**, an account "not associated with a person", with either a scoped API token or an OAuth 2.0 credential whose access token lasts 60 minutes and is asked for again by the code [S1] [S2] [S3]. The secret reaches the code from an environment variable or a secret store. |
| **Whom actions are attributed to** | With (a), the account that owns the token [T2]. With (b), the person who approved: the code acts "on a user's behalf" [R2]. With (c), the service account. Only (c) gives the agent a name that is not a person's. |
| **Scope of access** | Two limits apply together. Scopes limit the kinds of action: a scoped token or an OAuth credential can be read-only, or read and write without delete [T1] [R3]. Jira permissions limit where: the account can be given access to the one project. No credential can be limited to a single project by itself. That is done only through what the account may see [R3] [S4]. A token without scopes can do everything its account can [T2]. |
| **What is logged, and where** | In Jira: each story's history records "the user who made the change" and when [R4]. The documentation does not say that history tells a change made by the API from one made in a browser. Jira's audit log is for settings, and "isn't intended to record all activity": creating and editing stories is not in it [R5]. Atlassian's organization audit log lists the creation and revoking of API tokens, including a service account's, and with the higher plans "Created Jira issue" [R6]. An admin can see when each token was last used, with Atlassian Guard [R7]. On the agent's side: whatever the code writes. Nothing is kept unless the code keeps it. |
| **Rate limits** | Published. Requests made with an API token have per-second limits for each kind of request (100 for reads, 50 for updates), and writes to a single story are limited to 20 in 2 seconds [R8]. Apps using OAuth on a person's behalf also have an hourly points quota. How a service account's OAuth credential is counted is not stated. A limited request gets status 429 with a `Retry-After` header [R8]. |
| **Maintenance** | The most of the four. The code is the team's to write and keep working as Jira's interface changes. The token has to be replaced before it expires, within a year at most [T1] [S2]. |
| **Failure behavior** | The clearest of the four, because the code sees everything: the status code, the headers and the body. Atlassian's advice is to wait as `Retry-After` says, back off, and "only retry if the API is idempotent" [R8]. Creating a story has no idempotency key, and the documentation does not say a repeated create is safe [R9]. So a create that times out cannot simply be sent again. During an outage, requests fail or get a 5xx answer, and the code decides what to do. |
| **One named risk** | **Everything that keeps it safe is code the team writes.** Nothing stands between the agent and Jira except that code. Waiting when limited, not creating a story twice after a timeout, and stopping on a short answer all have to be built, tested and kept. A gap in that code is a gap in Jira. |

Against the purpose: it runs unattended, and with a service account the agent has its own name, a credential
that can be revoked without touching any person's work [S2], and scopes that leave out delete. The cost is that
the team owns the code.

## 3. MCP

A server that offers Jira to the agent as a list of named tools, such as "search", "create a story" and "edit a
story". The agent's model reads the list and decides, while it runs, which tool to call and with what. The one
compared here is Atlassian's own, which Atlassian hosts. Its documentation calls it both the "Atlassian MCP
server" and the "Atlassian Rovo MCP Server" [M1].

| | |
|---|---|
| **How it authenticates** | Three documented ways. (a) OAuth 2.1 through a browser, which is the default [M2]. (b) An API token, a person's or a service account's, only if the organization's admin has switched that on. Atlassian recommends it "only for non-interactive or machine-to-machine use cases" [M3]. (c) A service account with an OAuth 2.0 credential and no browser, announced on 2026-11-12 and found only in the changelog so far [M4]. An unattended agent needs (b) or (c). |
| **Whom actions are attributed to** | The account that signed in or owns the token. With a shared token the log shows "that account, rather than individual end users" [M5]. With a service account that is the agent's own name. |
| **Scope of access** | The server "never grants access beyond what the user already has" [M6], so the account's Jira permissions are the outer limit, and they are again the only way to hold it to one project. Inside that, tools come in groups: read, write, search, delete and manage. Delete and manage are off until an admin turns them on [M7]. An admin can block read, write or search for the whole organization [M8], and a token's scopes limit which groups work. One thing is wider than the other methods: the same server also reaches Confluence, Bitbucket and other Atlassian products [M1], so what the account can see there matters too. One protection is weaker with a token: data security policies "are enforced only for OAuth authentication methods" [M9]. |
| **What is logged, and where** | The best of the four on Atlassian's side. "Every time a tool is used through the Atlassian MCP server, an event is recorded" in the organization's audit log, with "the tool name, action, and user", on every plan [M5]. Whether the content sent with the call is logged is not stated. The story's own history records the change as in method 2. |
| **Rate limits** | No figure for the MCP server was found in Atlassian's current documentation. Some calls, the "enriched" searches across products, use up the organization's Rovo credits [M10]. |
| **Maintenance** | Atlassian runs the server, so there is no Jira code for the team to keep. In exchange the tools can change without the team doing anything: on 2027-03-01 use of version 1 "will automatically start to expose and utilize v2 tools" [M11]. The credential still has to be replaced before it expires. |
| **Failure behavior** | A failed tool call comes back to the model as an error message, and the model decides what to do next. What the server does when Jira limits it, or during an outage, was not found in the documentation. Whether to try again is the model's choice unless the agent's runner takes that choice away. |
| **One named risk** | **The model chooses the action, from what it has just read.** The stories the agent reads are written by other people. Text in a story can be worded as an instruction, and Atlassian's own account of the risk is that an agent "can be tricked into treating it as a legitimate user command" [M12]. Atlassian's advice is to "review high-impact changes before confirming" [M1]. An unattended agent has nobody to do that. |

Against the purpose: it can run unattended, with the agent's own name, and it gives the best record of what
the agent did. But the way it is meant to be made safe is a person approving changes, and this purpose has no
person present. The no-browser route with a service account is also two weeks old at the time of writing.

## 4. Managed connector

A ready-made Jira connection that the maker of the AI product hosts and runs. The team switches it on in the
product's settings and signs in. There is no tool to install and no code to write. The example read for this
comparison is the Atlassian connector in Anthropic's Claude products. Anthropic is also the maker of the
assistant that wrote this file. Other vendors' connectors were not read and may differ.

Two different things carry this name in that documentation, and they answer the questions differently:

- **A per-person connector.** Each person signs in to Atlassian themselves. Underneath, it is Atlassian's MCP
  server from method 3, reached from the vendor's cloud [C1].
- **A shared-account connector**, offered for a chat product. An admin makes a dedicated Atlassian account,
  and types its email address and an API token into the vendor's settings [C2].

| | |
|---|---|
| **How it authenticates** | Per-person: each person follows a sign-in prompt in a browser and approves access to their own Atlassian account [C3]. Shared-account: an admin gives the vendor a dedicated account's API token to hold, and it is a token without scopes [C2]. Either way the team never handles a secret in its own code. In the shared case the secret is held by the vendor. |
| **Whom actions are attributed to** | Per-person: that person. The product "inherits each person's permissions from the connected service" [C3], and for scheduled runs, anything done through connectors "appears as you" [C4]. Shared-account: the dedicated account [C2]. |
| **Scope of access** | Per-person: whatever that person can do in Atlassian, narrowed by two sets of switches. In the AI product, an owner can set each tool to always allow, needs approval, or blocked, for everyone, and members cannot override it [C3]. On Atlassian's side the MCP settings of method 3 apply as well. No setting that limits it to named Jira projects was found. Shared-account: whatever the dedicated account can do, with a token that has no scopes [C2]. |
| **What is logged, and where** | In two places that do not join up. Atlassian's audit log records each tool call under the acting account, as in method 3 [C1]. The AI product's own audit log is for Enterprise plans only, and the events found in it are administrative: a connector connected or disconnected, a permission setting changed. No event for a single tool call was found there [C5]. |
| **Rate limits** | Not found in the pages read. Two sets of limits would apply, the AI product's own usage limits and Atlassian's, and neither is the team's to tune. |
| **Maintenance** | The least of the four. The vendor and Atlassian run both ends. What is left for the team is the settings, and keeping the sign-in alive: in the shared case the token lasts a year at most and an admin has to replace it [C2]. |
| **Failure behavior** | The least visible of the four. In a scheduled run, a tool set to need approval "may wait for your answer or finish without the tool" [C6]. What a scheduled run does when the Atlassian sign-in has expired was not found for the vendor's own cloud. For one deployment type the documentation says the run "continues without the connector" [C7]. So a run can end without having done its Jira work, and how it reports that is not documented. |
| **One named risk** | **Unattended, it runs as a person.** The documented way to run with nobody present is a scheduled task, and a scheduled task belongs to one person's account and acts through that person's connectors, so every change "appears as you" [C4]. That is the quest's scenario, built in: the agent has a colleague's name, and it stops when that colleague's access does. |

Against the purpose: the per-person connector fits worst of the four. It is made for a person working with an
assistant, and when it runs unattended it borrows that person. The shared-account connector does give the
agent its own name, but with a token that has no scopes, held by a third party, in a product made for chat and
not for a scheduled agent.

## Sources

Atlassian's public documentation, and for method 4 Anthropic's, read on 2026-11-18 by research agents that
fetched each page and reported back. The pages were read through a tool that summarizes, so a quoted phrase should be checked against the
page before it is relied on. No Jira site was contacted.

- [A1] `developer.atlassian.com/cloud/acli/reference/commands/jira-auth-login/`
- [A2] `developer.atlassian.com/cloud/acli/guides/use-acli-on-ci/`
- [A3] `developer.atlassian.com/cloud/acli/reference/commands/jira-workitem-delete/`
- [A4] `developer.atlassian.com/cloud/acli/guides/troubleshooting-guide/`
- [T1] `support.atlassian.com/atlassian-account/docs/manage-api-tokens-for-your-atlassian-account/`
- [T2] `developer.atlassian.com/cloud/jira/platform/security-overview/`
- [S1] `support.atlassian.com/user-management/docs/understand-service-accounts/`
- [S2] `support.atlassian.com/user-management/docs/manage-api-tokens-for-service-accounts/`
- [S3] `support.atlassian.com/user-management/docs/create-oauth-2-0-credential-for-service-accounts/`
- [S4] `support.atlassian.com/atlassian-cloud/kb/401-unauthorized-error-when-service-account-accesses-jira-or-confluence-api/`
- [R1] `developer.atlassian.com/cloud/jira/platform/basic-auth-for-rest-apis/`
- [R2] `developer.atlassian.com/cloud/jira/platform/oauth-2-3lo-apps/`
- [R3] `developer.atlassian.com/cloud/jira/platform/scopes-for-oauth-2-3LO-and-forge-apps/`
- [R4] `developer.atlassian.com/cloud/jira/platform/swagger-v3.v3.json` (the changelog's `author` field)
- [R5] `support.atlassian.com/jira-cloud-administration/docs/audit-activities-in-jira-applications/`
- [R6] `support.atlassian.com/security-and-access-policies/docs/audit-log-activities-database/`
- [R7] `support.atlassian.com/organization-administration/docs/understand-user-api-tokens/`
- [R8] `developer.atlassian.com/cloud/jira/platform/rate-limiting/`
- [R9] `developer.atlassian.com/cloud/jira/platform/swagger-v3.v3.json` (create issue: no idempotency key is described)
- [M1] `support.atlassian.com/atlassian-rovo-mcp-server/docs/getting-started-with-the-atlassian-remote-mcp-server/`
- [M2] `support.atlassian.com/atlassian-rovo-mcp-server/docs/authentication-and-authorization/`
- [M3] `support.atlassian.com/atlassian-rovo-mcp-server/docs/configuring-authentication-via-api-token/`
- [M4] `developer.atlassian.com/cloud/rovo-mcp/changelog/`
- [M5] `support.atlassian.com/security-and-access-policies/docs/monitor-atlassian-mcp-server-activity/`
- [M6] `developer.atlassian.com/cloud/rovo-mcp/`
- [M7] `support.atlassian.com/atlassian-rovo-mcp-server/docs/supported-tools/`
- [M8] `support.atlassian.com/security-and-access-policies/docs/Configure-Atlassian-Rovo-MCP-server-permission/`
- [M9] `support.atlassian.com/security-and-access-policies/docs/prevent-atlassian-mcp-server-access/`
- [M10] `support.atlassian.com/rovo/docs/rovo-usage-limits/`
- [M11] `support.atlassian.com/atlassian-ai-gateway/docs/how-to-upgrade-from-atlassian-mcp-v1-to-atlassian-mcp-v2/`
- [M12] `www.atlassian.com/blog/artificial-intelligence/mcp-risk-awareness` (a blog post of 2025-06-26, about MCP in general)
- [C1] `claude.com/marketplace/connectors/atlassian`
- [C2] `claude.com/docs/claude-tag/admins/connections/atlassian`
- [C3] `support.claude.com/en/articles/10168395-set-up-claude-integrations`
- [C4] `code.claude.com/docs/en/routines`
- [C5] `support.claude.com/en/articles/9970975-access-audit-logs` and `platform.claude.com/docs/en/api/compliance/activities/list` (the second was read only in part)
- [C6] `support.claude.com/en/articles/13854387-schedule-recurring-tasks-in-claude-cowork`
- [C7] `claude.com/docs/third-party/claude-desktop/scheduled-tasks`
