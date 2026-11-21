# GitHub: read my assigned issues

Written by an AI assistant (Claude) at the participant's direction.

## 1. Purpose

This skill finds every GitHub issue assigned to the signed-in user, across repositories, and keeps a local
Markdown copy of each one: its fields, its comments, the material entries of its timeline, and the pull
requests, commits and issues that point to it. A later sync updates the copy in place and never deletes from it.

It only reads GitHub. Every request is a GET. There is no code in it that creates, comments on, labels, closes
or reopens anything.

    python3 participant/skills/github-read-assigned/sync.py --source fake [--fake-step 1]
    python3 participant/skills/github-read-assigned/sync.py --source live --out FOLDER [--only-repos owner/name,...]

`--source fake` reads the made-up GitHub in `fake_github.py`, beside this file. `--source live` reads GitHub.
The sync uses the Python standard library only.

## 2. Credentials and token scope

A live run needs one environment variable, `GITHUB_TOKEN`. Set it in your own terminal, for example with
`read -s`, and export it. It is sent in a request header. It is never put in an address, printed, or written to
a file. A fake run needs none.

Use the narrowest token that can read the issues:

- a fine-grained token on the repositories you choose, with **Issues: read-only**, **Pull requests: read-only**
  and **Metadata: read-only**. Pull requests are needed so that GitHub shows the pull requests that mention an
  issue. The sync still records no pull request as assigned work.
- for public repositories only, a fine-grained token with public read-only access.

Do not add a write permission. The sync prints the scopes GitHub reports for the token, when GitHub reports
them, so a wider token than intended is visible.

## 3. Identity

The sync asks GitHub "who am I?" (`GET /user`) and uses the login and user id it answers with. No login is
written in the skill, given on the command line, or put in a query: the count check uses `assignee:@me`.
The output, the index and `assigned.json` all say which identity produced the data. One folder holds one
user's issues, matched on the user id, and a folder that holds another user's refuses the run.

## 4. Scope

The scope is every repository in which GitHub lists an issue assigned to the user: owned repositories, member
repositories and organization repositories. `--only-repos` restricts a run to named repositories, and the
output and the index then say RESTRICTED.

A repository whose comments or timelines GitHub refuses (status 403, 404, 410 or 451) is reported as **could
not be read**, in the output and in the index, with how many assigned issues that leaves unrecorded. Its issues
are left exactly as the last successful sync left them, and its last successful sync time does not move.
The other repositories are still synchronized.

## 5. The query, and pull requests

1. `GET /issues?filter=assigned&state=all`, 100 to a page. GitHub returns issues and pull requests together.
2. **An item is a pull request when it carries a `pull_request` key, and only then.** Those are left out and
   counted. What the key holds does not matter. The key being there does.
3. `GET /search/issues?q=is:issue assignee:@me`, for its declared total only.

## 6. Paging and the count

The sync asks for the next page for as long as GitHub's answer carries a `Link` header with `rel="next"`. A
page that holds nothing new while GitHub says there is more stops the run.

The number of issues retrieved is then compared with the total GitHub's search declares. The output gives both.
If they disagree, or the search calls its own result incomplete, the run stops and writes nothing. Comments and
timelines are paged the same way.

## 7. What is kept of an issue

Repository full name, number, node ID, title, state, state reason, author, assignees, labels, milestone, body,
created, updated and closed times. Only these fields are asked for from the answer and kept. The whole answer
is never stored.

**Local identity is the node ID.** Each record is the file `issues/<node ID>.md`, and shows the repository full
name and number as well. Two issues with the same number in different repositories have different node IDs and
different files. A renamed repository keeps its issues' records, and each record lists its earlier identity.

Comments are kept with their id, author and times, and matched on the comment id, so a second sync adds none
twice. An edited comment replaces the held one. A comment GitHub no longer returns is kept and marked.

Timeline entries kept as material: closed, reopened, assigned, unassigned, transferred, renamed,
cross-referenced, referenced, connected, disconnected. Each has who and when. They are matched on the entry's
id, or for a cross-reference, which has none, on its source and time.

## 8. Links from request to delivery

From the timeline, each record lists the pull requests and issues that mention it, with repository, number and
node ID, and the commits that reference or closed it, with SHA and repository. `delivery-links.md` gathers them
and says for each issue whether delivery evidence **exists** (closed as completed, and a merged pull request
mentions it or a commit closed it), is **partial**, or is **missing**. A link is a claim that work answers the
issue. It is not proof that the work is right.

## 9. Your notes

Write notes on an issue in `notes/<node ID>.md`. The index and the record show which issues have one. The sync
opens notes files for reading only, to take their SHA-256, and prints each checksum before and after every run.
Its one function that writes files refuses any path in the notes folder. Note text is never copied anywhere.

## 10. Closed, transferred, unreadable

Nothing is ever removed locally.

- **Closed.** A closed issue that is still assigned is still returned. The output says CLOSED and what state it
  was in, and the record keeps every state the sync has seen, with the sync that saw it.
- **No longer returned.** The sync looks the issue up at its last known address and flags it with why:
  transferred (with where to), reassigned, unassigned, deleted, not found, or not reachable. The record keeps
  the fields it last had, says they are the last known state, and the index lists it in its own section.
- **Transferred.** GitHub redirects the old address. The sync follows a redirect only to GitHub's own API. If
  the issue kept its node ID the record is updated in place. If it has a new one, the old record is flagged and
  the new record points back to it.

## 11. Times

`assigned.json`, the index and each record hold the time of the last successful sync: for the whole run, for
each repository, and for each issue. A flagged issue keeps the time it was last actually synchronized.

## 12. All or nothing

Everything is read before anything is written. If a request fails, or GitHub rate-limits the run beyond three
waits of 15 seconds, nothing is written and every file is as the last successful sync left it.

Exit codes: 0 synchronized. 1 stopped, nothing written. 2 incomplete because of a rate limit, nothing written.

## 13. Bodies and comments are other people's writing

Nothing in a title, body or comment is acted on. Bodies and comments are written into a record inside a code
fence longer than any run of backticks they contain, so they stay text. Titles and names are written on one
line with the characters that could break a table or start a link replaced. The screen output shows ids, counts
and times, never a title, body or comment.

## 14. What is written, and where

| File | What it is |
|---|---|
| `index.md` | The assigned issues grouped by repository, the repositories, and the issues no longer assigned. Generated. |
| `issues/<node ID>.md` | One record for each issue. Generated. |
| `delivery-links.md` | The links from issues to pull requests, commits and issues. Generated. |
| `assigned.json` | The sync's memory. Generated. |
| `notes/<node ID>.md` | **Yours.** The sync never writes here. |

A fake run writes to `participant/context/github/assigned/` by default. A live run must be given `--out`, and
it should be a folder outside this repository, because real issues can hold private detail. Do not commit a
live run's folder.

## 15. Tests

    python3 -m unittest discover -s participant/skills/github-read-assigned/tests -v

Every test runs against `fake_github.py`. None contacts GitHub.

## 16. What it does not do

- It does not change anything in GitHub.
- It does not read issues in repositories GitHub's list leaves out, such as a public repository the user does
  not belong to. The count check then disagrees and the run stops. `--only-repos` gets past that.
- It does not record checks or workflow runs, or the commits inside a pull request.
- It does not know which pull request a "connected" entry refers to. GitHub's timeline does not say.
- It reads every issue's comments and timeline at every sync. It has no delta by update time.
- It stops if two node IDs differ only in upper and lower case, because each record is a file named by node ID.
