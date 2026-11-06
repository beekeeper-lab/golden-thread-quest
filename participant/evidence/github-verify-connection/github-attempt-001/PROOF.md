# Proof · github-verify-connection

Attempt: `github-attempt-001`

Decisions by Tom Carter; the check, its tests and these notes drafted with Claude (Claude Code),
11-05-2026 and 11-06-2026. Everything here only reads from GitHub; nothing on GitHub was changed.

## What was built

A read-only check of the GitHub connection I use every day (the GitHub CLI's sign-in for the
account Hoosiertom50), and notes on what it shows:

- **The check** (`participant/tools/verify-github-connection.py`) reads who the connection acts
  as, the scopes GitHub reports for it, the repositories it can reach and one repository's details,
  then compares them with what I expect. It has a second mode that tries to read a repository out
  of reach and shows it next to a list that is reachable but empty.
- **What I expect** (`participant/context/github/expected-access.yaml`): the account, its four
  scopes and my three repositories. Every run is compared with this, which is how a lost
  permission shows up.
- **The notes** (`participant/context/github/verify-notes.md`): what the check doesn't prove,
  which scopes are broader than needed, and how a changed permission would be noticed.

My decisions:

- **Check the connection I really use,** not a new token made for the quest, so the result says
  something true about my everyday setup, including that it is broader than it needs to be.
- **Name only my own repositories.** The connection also reaches 94 repositories in one
  organization, 77 of them private. This repository is public, so the check counts those and never
  names them, or the organization.
- **Do the safe read on my fork of this repository,** which I own.

## Where the important artifacts are

| What | Path |
|---|---|
| Verification run | `participant/evidence/github-verify-connection/github-attempt-001/logs/verify-run.txt` |
| Out-of-reach run | `participant/evidence/github-verify-connection/github-attempt-001/logs/denied-run.txt` |
| Notes | `participant/context/github/verify-notes.md` |
| The check | `participant/tools/verify-github-connection.py` |
| What I expect | `participant/context/github/expected-access.yaml` |

## How to reproduce the behavior

With the GitHub CLI signed in, from the repository's top folder:

```
.venv/bin/python participant/tools/verify-github-connection.py
.venv/bin/python participant/tools/verify-github-connection.py --denied octocat/not-a-repository-for-this-check
```

The first prints what `logs/verify-run.txt` shows and the second what `logs/denied-run.txt` shows,
apart from the time they ran and any change in what the connection reaches. Signed in as another
account, the first reports FAIL for the identity and the repositories, which is the point: it
checks against what I expect. Exit code 0 means every check passed, 1 that one failed, and 2 that
the check couldn't run (for example, gh missing or signed out).

## How the work meets the criteria

1. **The identity is read from the connection, not typed in:** the first request asks GitHub who
   the connection is (`GET user`), and the log prints the answer, `Hoosiertom50`, as "read from the
   connection". The expected-access file holds the same name only to compare against.
2. **The scopes or permissions are reported:** the log lists the four scopes GitHub returned with
   that answer (`gist`, `read:org`, `repo`, `workflow`), what each allows, and which allow changes.
   The safe read adds this connection's rights on my fork: admin, maintain, push, triage and pull.
3. **The reachable repositories are listed by full name:** my three are listed by full name
   (`Hoosiertom50/clean-house`, `Hoosiertom50/golden-thread-quest`, `Hoosiertom50/seatwise`). The
   other 94 are reachable too, all in one organization; they are counted (77 private, 17 public)
   and deliberately not named, because this repository is public.
4. **A repository outside scope is reported as inaccessible, not as empty:** `logs/denied-run.txt`
   reports `INACCESSIBLE: GitHub answered 404` for the out-of-reach repository, and right after it
   reports `REACHABLE, EMPTY: GitHub answered 200 with 0 items` for my fork's releases. GitHub
   gives the same 404 for a repository that doesn't exist and for a private one I can't see, so the
   check says it can't tell which, but either way calls it inaccessible.
5. **No write operation is attempted:** every request goes through one function that always sends
   GET. Both logs end by listing every request made (3 and 2) and stating that only reads were
   issued; an offline test also records the exact commands and confirms each is a GET.
6. **The credential appears in no output:** the check never asks for the token, turns off the
   CLI's debug output and blanks anything shaped like a GitHub token. Nothing is printed until the
   whole output has been scanned with the quest app's own credential patterns; if the scan finds
   anything, the whole output is withheld, and an error message is checked the same way. Both
   logs end `PASS no credential in this output ... 0 finding(s)`, and the repository's secret
   scanner finds nothing in either log.
7. **The notes say what the check does not prove and which scope is broader than needed:**
   `verify-notes.md` lists six things it doesn't prove and a table of the four scopes; `repo` is
   the broadest, giving write access to every private repository the account reaches, when the
   check needs to read three public ones.

## How the check would reveal a permission lost next week

If one of my repositories became unreachable, it would be missing from the reachable list, and the
check would print `FAIL every expected repository is reachable (LOST ACCESS: <name>)` and end with
exit code 1 (criteria 3 and 4). If a scope were removed or added, the scope line would fail and name
it (criterion 2). Asked about a repository it can't reach, the check says `INACCESSIBLE`, never
"empty" (criterion 4), so the week-long silent sync in the quest's scenario can't happen while the
check runs before it. I tested this with the final version on 11-06-2026 by pointing the check at a
copy of the expected file with one repository it can't reach and one extra scope: it reported
`LOST ACCESS` and `removed: admin:org` and ended with exit code 1. What it won't catch: a lost
organization repository (those are only counted), and anything between runs, since it isn't on a
schedule yet.

## Reflection

**Which scope would you remove first, and what would break?**

**Workflow.** It lets the connection change GitHub Actions files, and nothing in this quest, or in
my day-to-day pushes and pull requests, needs that; those use `repo`. What would break: I couldn't
push a change to a workflow file, such as Seatwise's CI checks in `.github/workflows/`, from this
sign-in. When I need to, I'd add the scope back for that change (`gh auth refresh -s workflow`) and
remove it again after.

## What was tested or validated

- **The real check:** both runs on my account passed, as recorded in the two logs.
- **A lost repository and a changed scope:** reported as FAIL with exit code 1, as described above.
- **Offline tests (kept locally, not handed in):** 46 runs of the check against a stand-in for the
  GitHub CLI, so nothing reached GitHub. They cover two pages of repositories; other owners counted
  but never named; a lost repository; a token-shaped value in GitHub's answer (blanked, even when
  run together with other text); another kind of credential, including one spread over several
  lines (the whole output withheld); a credential given on the command line or in a broken
  expected-access file; the CLI missing, signed out or refused; a readable repository given as out
  of reach (FAIL); names that try to leave the repository path, and an empty one (refused); every
  request being a GET; the CLI's debug setting switched on; GitHub answering badly (an unreadable
  answer, a list that fails part-way, bad credentials, a used-up or secondary rate limit, an
  "empty" list that isn't a list); an expected-access file with a missing, empty or wrongly typed
  entry; an unknown option; a safe-read repository that has moved to another owner (its new name
  withheld); and running with the wrong Python. In each case the check now stops with "couldn't
  run" (exit 2), fails, or withholds the output, instead of passing, printing a credential or
  crashing.
- **What my own tests and reviews found:** eight real problems, all fixed. On 11-05-2026 the tests
  found two: a credential that wasn't shaped like a GitHub token was printed before the scan
  caught it (the check said FAIL, but the value was already in the output), and an out-of-reach
  name of `../user` reached my own profile instead and came back as readable. Reading the whole
  script before the first Copilot round found four kinds of bad answer from GitHub that could
  crash the check or give a wrong result. Reading it again between rounds found two more: one of my
  fixes would have hidden the script's own helpful error messages, and running it with the Mac's
  built-in Python crashed instead of saying which Python to use.
- **Copilot review:** 5 rounds on a practice pull request in my own fork, on 11-06-2026. I
  reproduced every item before changing anything, and kept going until a round came back with
  nothing I would fix. Round 1 found 3 High and 1 Medium, round 2 found 2 High, round 3 found 3
  more in code it hadn't flagged before, and round 4 hinted at 2 gaps in its summary; all were
  real and all are fixed. Most were about keeping a credential out of the output on unusual paths
  (a credential spread over several lines, an error message, a command-line mistake, a token run
  together with other text), and the rest about never reporting success when the check didn't
  really run (a broken expected-access file, throttling read as "inaccessible", an empty
  out-of-reach name). Round 5 recommended approval with no open issues.

## Stretch goals

Not attempted: running the check on a schedule, and listing what a fine-grained token could
restrict (the notes say what one for this check would be limited to).

## Remaining limitations

- **One connection, one account.** It checks the CLI's sign-in on this computer only.
- **Organization repositories are counted, not checked by name,** so losing one wouldn't fail the
  check.
- **Inaccessible can't be split into "doesn't exist" and "not allowed",** because GitHub answers
  both the same way.
- **Not on a schedule:** a permission lost between runs is noticed at the next run.
- **It needs the repository's Python environment** (`.venv`) for the expected-access file and the
  credential patterns; without them it stops and says so rather than passing.

## Sensitive values

No token, password, session cookie or private repository name is in this hand-in. The check never
reads the token, the organization's repositories are only counted, and both logs passed the
check's own credential scan and the repository's secret scanner with no findings.
