# Notes on the GitHub connection check

The check is `participant/tools/verify-github-connection.py`. It reads the GitHub CLI's existing
sign-in for the account Hoosiertom50, using read operations only, and compares what it finds with
`participant/context/github/expected-access.yaml`. These notes cover what it does not prove, which
scopes are broader than needed, and how a changed permission would be noticed. Written 11-05-2026,
updated 11-06-2026.

## What the check does not prove

- **That the connection can't change anything.** It proves the check itself only read: every
  request is listed, and every one is a GET. The connection could still write; its scopes allow
  it, and the safe read shows it has admin and push rights on my fork.
- **Why a repository is out of reach.** GitHub answers 404 both for a repository that doesn't
  exist and for a private one the connection may not see, on purpose, so the check can only say
  "inaccessible", not which of the two it is.
- **Anything about the organization's repositories by name.** They are counted, never named,
  because most are private and this repository is public. A lost organization repository would
  change the count, but the check doesn't compare counts, so it wouldn't fail.
- **What each repository's own rules allow.** Scopes are what the token may ask for; branch
  protection, organization policies and single sign-on rules can still refuse an action. The
  check reads repository details, not files, so it doesn't show whether those rules would block a
  file read.
- **Anything after the moment it ran.** It is a snapshot. A permission removed a minute later is
  only noticed on the next run.
- **How the token is stored or when it expires.** The check never touches the token. The CLI keeps
  it in the macOS keychain; this kind of token has no expiry date to report.

## Scopes broader than needed

The connection reports four scopes: `gist`, `read:org`, `repo` and `workflow`. The check itself
only reads one account's details, a list of repositories and one repository's details.

| Scope | What it allows | Needed by the check? |
|---|---|---|
| `repo` | Read and write every repository the account can reach, private ones included: 97 today, 77 of them private and owned by an organization | Only to see private repositories at all; write access isn't needed |
| `workflow` | Change GitHub Actions workflow files | No |
| `gist` | Create and change gists | No |
| `read:org` | Read organization membership and teams | No |

The broadest is `repo`: it gives write access to every private repository the account can reach,
when the check needs to read three public ones. A connection made only for this check would be a
fine-grained token, read-only, limited to those three repositories. I didn't make one: the CLI
sign-in is the one I use every day to push and open pull requests, which needs `repo`, and
checking the connection I actually use was the point.

## How a changed permission would be noticed

- **A lost repository fails the check.** Every repository listed in `expected-access.yaml` must
  appear among the reachable ones; a missing one is reported as `LOST ACCESS: <name>` and the check
  ends with exit code 1.
- **A changed scope fails the check.** The reported scopes must match the expected list exactly; a
  scope added or removed is named in the FAIL line.
- **Inaccessible never looks like empty.** Asked about a repository it can't reach, the check says
  `INACCESSIBLE`, with GitHub's answer; a list it can read but that has nothing in it says
  `REACHABLE, EMPTY`. The quest's scenario, a sync returning nothing for a week, is the second
  answer being mistaken for the first.
- **Tested.** On 11-06-2026, with the final version, I pointed the check at a copy of the
  expected-access file with one repository it can't reach and one extra scope: it reported
  `LOST ACCESS` and `removed: admin:org` and ended with exit code 1.
- **Not yet on a schedule.** Someone has to run it. Run before each sync, or daily, a failure
  would show up the same day instead of after a week.
