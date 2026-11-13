# Four ways an agent can reach Jira: a comparison

How four access methods would let an AI agent reach the Tixly team's Jira project. Tixly, its team
and its Jira project are invented; the four methods are real products, described from their
vendors' public documentation as of 11-02-2026. No connection was made. Decisions by Tom Carter;
research and wording drafted with Claude (Claude Code), 11-02-2026.

The methods compared:

- **CLI:** Atlassian CLI (`acli`), Atlassian's own command-line tool, signed in on one computer.
- **REST API:** a program calling the Jira Cloud REST API directly, with an API token or an
  OAuth 2.0 app.
- **MCP:** the Atlassian Rovo MCP Server, which an AI assistant uses as a set of tools.
- **Managed connector:** Claude's Atlassian connector, a hosted connection an organization adds once
  and each member signs in to. It is built on the Rovo MCP Server, so where it behaves the same, it
  says "as MCP"; it adds the controls listed in its column.

All four reach the same Jira, so Jira's own permissions limit every one of them: no method can do
more than the account it acts as. A number in brackets is a source, listed at the end. **Not
verified** marks a statement no primary source confirmed.

## The comparison

| | CLI (Atlassian CLI) | REST API | MCP (Rovo MCP Server) | Managed connector (Claude's Atlassian connector) |
|---|---|---|---|---|
| **How it signs in** | A person's API token, or signing in through the browser [3]. An open public suggestion reports it doesn't accept service-account tokens [4]. | An API token (scoped tokens recommended) or an OAuth 2.0 app [1][6][7]. A service account can have its own scoped token or OAuth client credentials [2][8]. | OAuth sign-in by a person, mainly [10]. An API token (personal or service-account) only if an organization admin enables it [10]. | An organization owner adds it; then each member signs in with their own Atlassian account [14]. |
| **Whose name is on the actions** | The person whose token or sign-in it uses (inferred; **not verified**). | The token's owner, the person who approved the OAuth app, or the service account (inferred from [6][7][8]; **not verified**). | Signed in: that person, who is the user the audit log records for each tool use [12]. With a token: the token's account, "rather than individual end users" [12]. How Jira's issue history displays either is **not verified**. | The member who signed in, as MCP [14][12]; how Jira's issue history displays it is **not verified**. |
| **What it can reach** | With a person's unscoped token, it can do everything that person can do [6]. With browser sign-in, its exact reach is **not verified**. The reported lack of service-account support means no account of its own for automation [4]. | With a personal unscoped token, everything the person can do; with a scoped token, only its chosen scopes; with an OAuth app, its scopes, limited to what the person may do [1][7]. | The person's permissions (and the token's scopes, with a token) [11]. Delete and manage tools stay off until an admin turns them on [11]; admins can limit read, write and search [19]. | As MCP, and each tool can be set to always allowed, needing approval, or blocked [14]. |
| **What is logged, and where** | The issue's history in Jira; the organization's audit log, on plans that include it [9]. Local logs aren't documented (**not verified**). | The issue's history; the audit log's API-token and app activity, on the top plans [9]; anything else only if your own program logs it. | The issue's history; every tool use, recorded in the organization's audit log with the tool, the action and the user [12]. Atlassian's pages disagree on which plans include this (**not verified**). | As MCP on Atlassian's side. The connector's own logs aren't documented (**not verified**). |
| **Rate limits** | Those of the API underneath (inferred; **not verified**). | API tokens: bursts of up to 100 requests a second per endpoint on a site (50 for updates and deletions) and 20 changes to one issue in 2 seconds; OAuth apps also share an hourly points budget. Over a limit: error 429 with a wait time [5]. | No published request limit; some tools use the organization's Rovo usage credits [15] (**not verified** whether Jira's limits also apply). | As MCP. |
| **Upkeep** | Upgraded by hand; each version supported for 6 months [16]. Tokens expire within a year [1]. A scope change needed every site admin to re-approve it [17]. | You own the code. Tokens expire within a year [1]; an OAuth app must store each new refresh token [7]. | Run by Atlassian. Admins keep the allowed sites, the token switch and the tool groups up to date [13]. | Run by its vendor. A member reconnects when access is lost [14]. |
| **How it fails** | An expired token is refused (inferred from [1]; **not verified** for the CLI); after a scope change, it failed until an admin re-approved it [17]. | 401 for a bad or expired token, 403 for missing permission, 429 when over a limit; repeated failed sign-ins bring up a CAPTCHA [5][6]. | A plain refusal if token sign-in is off or the network isn't allowed [12][13]; some tools use usage credits: by default, extra usage keeps them working and is billed (from 12-03-2026), and they pause only if an admin turns extra usage off or a spending cap is reached [15]. | The connector shows "Reconnect" [14]. |
| **How to switch it off without breaking anyone else** | With a token: revoke it [1]; that breaks only what uses the same token, but until then the agent holds a person's credential. With browser sign-in: `acli jira auth logout` signs out of Jira on that computer [21]; what it revokes, and any other way to withdraw that sign-in, is **not verified**. | Revoke the one token: a service account's affects no one else [1][2]. A person can withdraw an OAuth app; an admin can only uninstall it for everyone [7]. | Revoke the agent's own token: no one else is affected [12]. Wider switches also stop other people's tools: turning off token sign-in for the organization, or blocking apps [12][13]; uninstalling removes it for everyone [20]. | Disconnecting signs Claude out of that member's own account; an owner can remove it for the whole organization [14]. |
| **One named risk** | Without service-account support, automation has to run on a person's token, with all of that person's permissions [4]. | A personal unscoped token is a long-lived key to everything the person can do, and keeps working after the person leaves for as long as their account still has access to the site [18]. | With one shared token, many people's AI assistants act as one account, so the audit log can't tell who did what [12]. | A write tool set to "always allowed" lets the AI change Jira without asking anyone [14]. |

## Facts behind the comparison

- **API tokens expire.** A token created now lasts from 1 to 365 days, a year by default; tokens
  created before 12-15-2024 were set to expire between 03-14-2026 and 05-12-2026 [1].
- **Service accounts** are accounts "not associated with a person", for integrations. They need
  scoped tokens, can't sign in to Jira's web pages, and are limited in number by plan (5 per
  organization on the free allowance) [2][8].
- **When someone leaves:** if their account is deleted, their tokens stop working; as long as the
  account "still has access to your Jira or Confluence site, their user API tokens remain usable"
  [18].

## Sources

All checked on 11-02-2026.

1. Atlassian, Manage API tokens for your Atlassian account: https://support.atlassian.com/atlassian-account/docs/manage-api-tokens-for-your-atlassian-account/
2. Atlassian, Understand service accounts: https://support.atlassian.com/user-management/docs/understand-service-accounts/
3. Atlassian CLI, jira auth login: https://developer.atlassian.com/cloud/acli/reference/commands/jira-auth-login/
4. Atlassian public suggestion CLOUD-12991, service-account tokens with the Atlassian CLI: https://jira.atlassian.com/browse/CLOUD-12991
5. Jira Cloud platform, Rate limiting: https://developer.atlassian.com/cloud/jira/platform/rate-limiting/
6. Jira Cloud platform, Basic auth for REST APIs: https://developer.atlassian.com/cloud/jira/platform/basic-auth-for-rest-apis/
7. Jira Cloud platform, OAuth 2.0 (3LO) apps: https://developer.atlassian.com/cloud/jira/platform/oauth-2-3lo-apps/
8. Atlassian, Manage API tokens for service accounts: https://support.atlassian.com/user-management/docs/manage-api-tokens-for-service-accounts/
9. Atlassian, Accessing audit log activities: https://support.atlassian.com/security-and-access-policies/docs/accessing-audit-log-activities/
10. Atlassian, Rovo MCP Server authentication and authorization: https://support.atlassian.com/atlassian-rovo-mcp-server/docs/authentication-and-authorization/
11. Atlassian developer guide, Rovo MCP authentication and authorization: https://developer.atlassian.com/cloud/rovo-mcp/guides/authentication-and-authorization/
12. Atlassian, Monitor Atlassian MCP server activity: https://support.atlassian.com/security-and-access-policies/docs/monitor-atlassian-mcp-server-activity/
13. Atlassian, Control Atlassian MCP server settings: https://support.atlassian.com/security-and-access-policies/docs/control-atlassian-mcp-server-settings/
14. Claude, Getting started with connectors: https://claude.com/docs/connectors/getting-started
15. Atlassian, Rovo usage limits: https://support.atlassian.com/rovo/docs/rovo-usage-limits/
16. Atlassian CLI, Install: https://developer.atlassian.com/cloud/acli/guides/install-acli/
17. Atlassian CLI, Changelog: https://developer.atlassian.com/cloud/acli/changelog/
18. Atlassian knowledge base, API tokens when the user who created them has left: https://support.atlassian.com/jira/kb/atlassian-api-token-key-status-of-api-tokens-keys-when-a-user-who-generated-the-token-key-has-left-the-organization/
19. Atlassian, Configure Atlassian Rovo MCP server permissions: https://support.atlassian.com/security-and-access-policies/docs/Configure-Atlassian-Rovo-MCP-server-permission/
20. Atlassian, Managing an installed app: https://support.atlassian.com/organization-administration/docs/managing-an-installed-app/
21. Atlassian CLI, jira auth logout: https://developer.atlassian.com/cloud/acli/reference/commands/jira-auth-logout/
