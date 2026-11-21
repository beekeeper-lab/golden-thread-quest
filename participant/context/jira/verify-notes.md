# Notes on the Jira connection check

What the check in `participant/evidence/jira-verify-connection/jira-attempt-005/scripts/verify.py` does not
prove, and how a changed permission would be noticed. Written by an AI assistant (Claude) at the participant's
direction.

## What the check does

It reads, and only reads. In one run it asks Jira who the connection is, lists the projects the connection can
see, asks for each project it was told to expect, asks what the connection may do there, and reads one item.
A second command asks for one project the connection should not see, and reports the refusal.

A project is called inaccessible when Jira refuses to return the project itself. It is never called empty on
the strength of a search that found nothing.

## What it found on the sandbox

Three things worth keeping, from the real runs recorded in the attempt's `logs/` folder.

- **A search of a project the connection cannot see answers as an empty project does.** Jira returned status 200
  with no issues for a project key that belongs to nothing. Asked for the same project directly, it answered
  404. A sync that only searches cannot tell a lost project from a quiet one.
- **The connection that was checked is not limited.** Jira reports that it may browse, create, edit, delete
  and administer in the one project it can see. It is a personal API token on the account that owns the site,
  so it can do whatever that account can. The check did not make it so, and did not use any of it.
- **The first real run was told to expect a project that does not exist.** The assistant had assumed the
  sandbox held a project with the key `GTQ`. It does not. The check reported `GTQ` as inaccessible and ended
  with an access problem, which is how the mistake was found.

## What the check does not prove

**About the connection:**

- **It does not prove the connection is limited the way anyone intended.** It reports what Jira says the
  connection may do. Whether that is too much is for a person to judge. On the sandbox it is plainly more than
  a read-only check needs.
- **It does not prove a write would be refused.** It never tries one, by design. All it can say about writing
  is what Jira reports: yes or no for each permission it asks about.
- **It asks about five permissions only**: browse projects, create issues, edit issues, delete issues,
  administer projects. Jira has many more. A permission it does not ask about is not in the report.
- **It reports the account's permissions, not a token's limits.** A token made with scopes can be narrower than
  its account. Whether Jira's answer about permissions reflects those scopes was not tried.

**About what it can see:**

- **It cannot say why a project is inaccessible.** Jira gives one answer, 404, for a project that does not
  exist and for one the connection may not see. The check reports both possibilities and does not choose.
- **A project that exists and is forbidden was never tried.** The sandbox has one project and the account can
  see it. The refusal recorded is for a key that belongs to no project. Jira's specification says the answer
  is the same, and that was not confirmed.
- **Reading one item does not show that every item can be read.** Jira can hide single issues inside a visible
  project. The check reads the first item in a project and stops.
- **A project it was not told to expect is not checked.** The list of visible projects is printed, but nothing
  compares it with anything unless the project is named in `--expect`.

**About the check itself:**

- **"Only read operations were issued" is the check's own account.** The list of requests is kept by the check.
  Jira's records were not consulted. What stands behind it is that the check has no code that sends anything
  but a GET, and a test that fails if such code is added.
- **The credential scan covers what the check prints, and nothing else.** It searches that output for the
  token, the email address and their encoded form, exactly as they are. It does not look at the shell's
  history, at other files, or for a credential that has been altered.
- **It shows one moment.** A run that says OK says nothing about an hour later.
- **Most of its tests run against a fake Jira** built from Jira's published specification by the same assistant
  that wrote the check. Three real runs agreed with it, on a site with one project.

## How a changed permission would be noticed

Only by comparing a run with what was expected. A single run with no expectation describes today and cannot
report a loss.

**What the check compares with: the `--expect` list.** The person running it names the projects the connection
should see. That list is the record of what was intended.

| What changes | What the next run shows |
|---|---|
| The connection loses a project it was expected to see. | That project is reported as `INACCESSIBLE`, in those words, and not as empty. The run ends `ACCESS PROBLEM`, naming the project, with exit code 2. The count of visible projects is one lower. |
| The token expires or is revoked. | The first request is refused, and the run stops with `Jira rejected the credentials (401)` and exit code 1. |
| The connection can still see a project but can no longer read from it. | The run stops and says reading from that project failed, with the status Jira gave. |
| The connection loses a permission inside a project, for example editing. | That permission's line reads `no` where it read `yes`. Nothing else changes, and the exit code is still 0. |
| The connection gains a project it should not see. | Nothing, unless the `denied` command is run for that project. Then it ends `NOT AS INTENDED` with exit code 3. |
| The connection becomes a different account. | A different account id in the first section. Nothing flags it. |

The first three rows are noticed by the check itself: it stops, or exits with a code that is not 0, and
something running it on a schedule can act on that without reading the report.

The last three are not. They change a line in the output, and a person, or a comparison with an earlier run,
has to notice. **Nothing here saves a run to compare the next one with, and nothing runs the check on a
schedule.** Both would be needed before the check could be relied on to notice a change by itself.

## What this means for the existing sync

`participant/skills/jira-read-assigned/` finds stories by searching. Given what the sandbox showed, a search
after a project is lost would return fewer stories and no error. That sync lists a story that stops coming
back as removed, which would show that something changed. It could not tell "removed" from "the connection can
no longer see that project". Running this check before a sync, with the projects the sync depends on in
`--expect`, would.
