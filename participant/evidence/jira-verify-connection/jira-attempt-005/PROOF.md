# Proof · jira-verify-connection

Attempt: `jira-attempt-005`

## How this was made

An AI assistant (Claude) wrote the check, a fake Jira to test it against, the tests, the notes and this file,
at the participant's direction. The work was done in small steps, each shown to the participant before the
next.

What the participant did themself:

- Chose to verify a real Jira sandbox, with a fake for testing, over a local fixture alone.
- Made the API token, and put the token, the account's email address and the site's address into their own
  terminal. The assistant was never shown any of the three.
- Ran the three recorded runs against the real sandbox.

The approach: have Jira's published API specification read first, to learn what Jira answers for a project
that cannot be seen; build a fake Jira with a visible project, an empty one and a hidden one; write the check
so that "inaccessible" is decided by asking for the project and never by a search; test it, and plant bugs to
test the tests; then run it against the real sandbox.

One thing went wrong, and it is recorded and not hidden. The assistant told the participant that the sandbox
held a project with the key `GTQ`, and the first real run was told to expect it. There is no such project:
the key comes from a local test fixture. The check reported it as inaccessible, which is how the error was
found. That run is kept as `logs/expected-project-missing.txt`.

Statements below are marked **observed** (a recorded run against the real sandbox shows it), **tested** (a
passing test against the fake shows it, with the output in `logs/tests.txt`) or **not assessed**.

## How the check would reveal a permission lost next week

By being told what the connection should see, and saying so loudly when it does not.

The check is run with a list of the projects the connection is expected to see:

    verify.py check --source live --expect SCRUM

That list is the record of what was intended. Each run compares what Jira returns with it. A run with no
expectation could only describe today, and a loss is a difference from before.

If, next week, the connection can no longer see `SCRUM`, the same command would:

1. list no `SCRUM` among the visible projects (criterion 2);
2. ask Jira for the project `SCRUM` itself, get 404, and report `SCRUM: INACCESSIBLE`, with the line `This is
   NOT an empty project` (criterion 4);
3. read nothing from it, and say `NO ITEM WAS READ` (criterion 3 is not met, and the check says so);
4. end `RESULT: ACCESS PROBLEM. 1 of 1 expected project(s) INACCESSIBLE: SCRUM.` with exit code 2.

This is not only predicted. It was **observed**, for a different reason. `logs/expected-project-missing.txt`
is a real run that expected a project the connection could not see, and its output is those four things.

Why it does not depend on a search. **Observed** in `logs/denied-run.txt`: asked to search a project it could
not see, the real sandbox answered status 200 with 0 issues, which is what an empty project answers. Asked for
the project itself, it answered 404. The check decides from the second and shows the first only for
comparison. A check that searched would have reported nothing wrong.

If the token itself is lost, by expiring or being revoked, the first request is refused and the run stops with
`Jira rejected the credentials (401)` and exit code 1. This is **tested**, not observed.

What it would not reveal by itself is set out in `participant/context/jira/verify-notes.md`: a single
permission lost inside a project that stays visible changes one line from `yes` to `no` and nothing else, and
the check is not run on a schedule.

## Reflection: what to check each day to notice a silent loss of access

Not whether the sync worked. The sync in the scenario worked every day for a week.

A silent loss makes no error, so nothing that waits for an error will see it. What changes is the answer to a
question that had a known answer yesterday. So the daily check is a short list of questions whose answers are
written down in advance, and it fails when one of them comes back different.

Four, in the order they would be asked:

1. **Is the connection still the same account, and is it active?** One request. If the token has expired, this
   is where it shows, as a refusal and not as an empty result.
2. **Can it still be handed each project the sync depends on?** Ask for each project by key. This is the
   question that catches the scenario. It cannot be replaced by counting stories: on the real sandbox, a search
   of a project the connection could not see came back as a success with nothing in it.
3. **Can it still read one known item in each of those projects?** A project can stay visible while its
   contents stop being readable.
4. **Are its permissions what they were?** Compared with a saved copy, line by line. This is the only one of
   the four that catches a permission lost inside a project that is still visible, and the only one that
   catches a permission gained.

The fourth is the one the check here cannot do. It prints the permissions and keeps nothing, so a `yes` that
became a `no` is one changed word in a report nobody has a reason to read. That is the same failure as the
scenario, moved down one level: an answer that looks like an answer.

Two things about how it is checked matter as much as what is checked.

- **It has to fail closed.** The check should stop the sync, or mark its output as unverified, when a question
  comes back different. A warning in a log that the sync runs past is not a check.
- **Someone has to notice when the check itself stops running.** A daily check that quietly stopped a week ago
  looks the same as a week with nothing to report.

The count of stories is not on the list, though it is the first thing most people would watch. It is the one
signal the scenario already had. The number went down, and a smaller number is not alarming.

## What was built

- **The check**, `scripts/verify.py`, with two commands. `check` shows who the connection is, which projects it
  can see, whether each expected project is reachable, what it may do there, and that one item can be read.
  `denied` asks for one project the connection should not see and reports what Jira answers. It sends GET
  requests only and lists every one. Before printing, it searches its whole output for the credential.
- **A fake Jira**, `scripts/fake_jira.py`: a made-up site with a visible project, an empty one and a hidden
  one. It can answer a search of a hidden project either with an error or with nothing, because the
  specification does not say which Jira does.
- **28 tests**, `tests/test_verify.py`, against the fake, and a script that plants 13 bugs to see whether the
  tests notice, `scripts/planted_bugs.py`.
- **The notes**, `participant/context/jira/verify-notes.md`.

Neither stretch goal was built. The check is not run on a schedule. It reports five permissions as Jira gives
them, and does not hold a list of permissions the connection should not have.

## Where the important artifacts are

`.../` stands for `participant/evidence/jira-verify-connection/jira-attempt-005/`.

| What | Path |
|---|---|
| The verification run, against the real sandbox | `participant/evidence/jira-verify-connection/jira-attempt-005/logs/verify-run.txt` |
| The denied run, against the real sandbox | `participant/evidence/jira-verify-connection/jira-attempt-005/logs/denied-run.txt` |
| Copies of those two logs, at the path the quest names | `participant/evidence/jira-verify-connection/attempt-001/logs/` |
| What the check does not prove, and how a change would be noticed | `participant/context/jira/verify-notes.md` |
| A real run that expected a project it could not see | `.../logs/expected-project-missing.txt` |
| The output of all 28 tests | `.../logs/tests.txt` |
| Thirteen planted bugs, each caught by a test | `.../logs/planted-bugs.txt` |
| The check | `.../scripts/verify.py` |
| The fake Jira, the tests, the bug-planting script | `.../scripts/fake_jira.py`, `.../tests/test_verify.py`, `.../scripts/planted_bugs.py` |

## How to reproduce the behavior

Needs Python 3.9 or later and nothing else.

**The tests and the planted bugs**, with no network and no credentials:

    cd participant/evidence/jira-verify-connection/jira-attempt-005
    python3 -m unittest discover -s tests -v
    python3 scripts/planted_bugs.py

**The check against the fake**:

    python3 scripts/verify.py check --source fake --expect ALPHA,EMPTY
    python3 scripts/verify.py denied --source fake --fake-search empty --project HIDDEN

**The check against a real Jira** needs a sandbox site and an API token. Set them in the shell, without putting
them in a file or in the shell's history:

    read -s JIRA_BASE_URL && export JIRA_BASE_URL
    read -s JIRA_EMAIL && export JIRA_EMAIL
    read -s JIRA_API_TOKEN && export JIRA_API_TOKEN
    python3 scripts/verify.py check --source live --expect <a project key the connection should see>
    python3 scripts/verify.py denied --source live --project <a project key it should not see>

The recorded runs read the participant's sandbox, so a reviewer's own run will show a different account and
different project keys.

## What was tested or validated

**Observed** means against the real sandbox. **Tested** means against the fake, with the output in
`logs/tests.txt`.

| # | Criterion | Observed | Tested |
|---|---|---|---|
| 1 | The identity is read from the connection, not typed in. | `logs/verify-run.txt`, section 1: an account id, and the first request listed is `GET /rest/api/3/myself -> 200`. No account is given on the command line. | `Identity`: the id printed is whatever the fake says the connection is, and no account id is in `verify.py`. |
| 2 | The visible projects are listed by stable key. | `logs/verify-run.txt`, section 2: `1 visible: SCRUM`. Names are not printed. | `VisibleProjects`: keys and not names, and 122 projects across three pages are all listed. On the sandbox one page was enough. |
| 3 | A read of one item succeeds. | `logs/verify-run.txt`, section 4: `Read one item from SCRUM: SCRUM-1, status 'To Do' ... The read succeeded.` | `test_a_read_of_one_item_succeeds_and_its_text_is_not_printed`. |
| 4 | A project outside scope is reported as inaccessible, not as empty. | `logs/denied-run.txt`: Jira answered 404 for the project and 200 with 0 issues for a search of it, and the report says `It is reported as INACCESSIBLE. It is not reported as empty.` `logs/expected-project-missing.txt`: the same for a project the run was told to expect, ending `ACCESS PROBLEM`. Both are for keys that belong to no project. A project that exists and is forbidden was **not assessed**. | `EmptyIsNotInaccessible` and `Denied`: a project that exists and is hidden, beside one that is visible and empty, under both ways a search might answer. An inaccessible project is never searched to decide. |
| 5 | No write operation is attempted. | Both real runs end with the list of requests: 9 in one and 5 in the other, every one a GET. | `test_the_check_can_only_send_get_requests`: `verify.py` builds one kind of request. `test_a_request_jira_refused_is_listed_too`: the list leaves nothing out. |
| 6 | The credential appears in no output. | Both real runs: `searched for the API token, the account's email address and the encoded pair that is sent to Jira: 0 found.` The project's own secret scan finds nothing in any file of the attempt. | `test_if_jira_echoes_the_token_back_the_output_is_withheld`: when the token does turn up in what would be printed, nothing is printed but a refusal. |
| 7 | The notes say what the check does not prove. | `participant/context/jira/verify-notes.md`, the section "What the check does not prove": twelve points, in three groups. | |

Six of the seven were seen against real Jira. Criterion 7 is a document.

The checks were themselves checked. `logs/planted-bugs.txt`: 13 bugs were put into `verify.py` one at a time,
among them reporting a refused project as empty, letting a search decide, not searching the output for the
credential, and leaving a lost project out of the exit code. The first time, one bug was caught by no test:
requests that Jira refused could be left out of the list of requests. A test was added for it. All 13 are now
caught, 9 of them by exactly one test.

The safety constraints:

- **A sandbox, and only reads.** The participant's Jira sandbox, which holds one sample project. Fourteen GET
  requests were sent to it in the two logged runs and three more in the first run. Nothing else was sent.
- **Authenticate through an environment variable.** Three environment variables, set by the participant with
  `read -s`, so that nothing was typed into the shell's history. The check holds no credential and no site
  address.
- **Untrusted text, and redacted records.** The check read one item and printed its key, its status and the
  length of its summary. The summary itself was not printed. **Tested**: a summary worded as an instruction to
  the tool is not printed and changes nothing. The logs hold one account id and two project keys, `SCRUM`,
  which is the key of Jira's sample project, and keys that belong to nothing. They hold no name, no email
  address and no site address.

## Remaining limitations

Known so far. There may be others. `participant/context/jira/verify-notes.md` gives the full list of what the
check does not prove. The ones that bear most on this evidence:

What could not be done:

- **A project that exists and is forbidden was not tried.** The sandbox has one project, and the account can
  see it. Every refusal recorded is for a key that belongs to no project. Jira's specification says the answer
  is the same for both. That was not confirmed.
- **The connection that was checked is not a limited one.** Jira reports that it may browse, create, edit,
  delete and administer. It is a personal API token on the account that owns the site, expiring a day after it
  was made. The mission is to prove a connection "is limited the way you intended". What this evidence proves
  is that the check reports the limits honestly. The connection itself is not limited.
- **A token with scopes was not used.** It would have been the narrower credential. It needs a different
  address and an extra id for the site, and was set aside to keep the steps short.
- **Losing a token was not seen.** Expiry and revoking are tested against the fake only.

About the check:

- **It does not save a run or compare one run with the last.** A lost permission inside a visible project
  changes one line and is easy to miss.
- **It is not run on a schedule.**
- **It asks about five permissions**, and reads one item.
- **Its list of requests is its own account.** Jira's records were not consulted.
- **The exit code of the first real run was not captured.** The output was piped to a file, which hides it.

About the checking:

- **The fake was written by the same assistant as the check**, from Jira's specification. It was wrong in
  neither direction on what the real runs touched, and it could not have been right about search without the
  switch: the specification does not say what a search of an unseen project returns.
- **Nine of the thirteen planted bugs are caught by exactly one test.**
- **No independent review has been run on this attempt.**

What would be done next: save each run's visible projects and permissions, compare the next run with them and
report any difference; then run it before each sync.

## Sensitive values

No token, password or cookie is in any file. The assistant was never shown the API token, the account's email
address or the site's address: the participant entered all three in their own terminal. The check searched its
own output for the token, the email address and their encoded form before printing, and found none in either
real run. The project's secret scan finds nothing in the attempt folder or the notes.

What the files do contain, on purpose:

- **One Atlassian account id**, the participant's own. It is an id, not a name or an email address.
- **Project keys**: `SCRUM`, the key of Jira's sample project, and `GTQ` and `ZZNONE`, which belong to nothing
  on the site.
- **One issue key**, `SCRUM-1`, with its status. Its summary was read and not printed.

They contain no person's name, no email address, no site address, no organization name and no ticket text. The
participant is called "the participant" throughout.

The token used was made to expire a day after it was made. It can do everything the account can, so it should
not be kept: it can be revoked now on the Atlassian account's API tokens page.
