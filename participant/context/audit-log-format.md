# Audit log format

This describes the chained audit log in `participant/context/audit-log-all-events.md`: what each row holds, the five kinds of event, and how a change to an earlier row is caught. The older `participant/context/audit-log.md` from the first Base Camp quest is a different, unchained log and is left as it was.

The tool that writes and checks the log is `participant/evidence/base-camp-audit-log/base-attempt-002/scripts/auditlog.py`. It has two commands, `append` and `check`. It has no edit or delete command.

## The fields

Each row is one event. The columns, in order:

| Field | What it holds | Rule the check applies |
|---|---|---|
| **Seq** | The row's number, counting from 1. | Must equal the row's position. |
| **Time (UTC)** | When the row was written, as `YYYY-MM-DD HH:MM:SS`, taken from the computer's clock when the row is added. | Must be present, in that form, and not earlier than the row before. |
| **Kind** | One of the five kinds below. | Must be one of the five. |
| **Action** | What was done or tried, in plain words. | Must not be empty. |
| **Target** | What it was done to, named by identifier (system, ticket key, field). Never the record's content. | Must not be empty. |
| **Actor** | Who started it. The log tool records the text its caller passes. `run_workflow.py` passes the computer account that ran it and its own name. | Must not be empty. |
| **Confirmed** | Whether the action was approved, and how the answer arrived. Reads show `n/a`. The log tool records the text its caller passes. | Must not be empty. |
| **Outcome** | What came of it. For a failure, the reason as a short description and a code. | Must not be empty. |
| **Ref** | The Seq of an earlier row this one belongs to. | If present, must be plain digits naming an earlier row. A confirmed write must name an earlier preview for the same target. A recovery must name an earlier failure. |
| **Chain** | 16 characters that tie this row to the one before it (see "How a changed row is caught"). | Must match what the check recomputes. |

`append` refuses a field that contains a `|`, or any character in four Unicode categories: control (Cc, which includes line breaks and tabs), format (Cf, which includes the zero-width and direction-override characters that were tried), line separator (Zl) and paragraph separator (Zp). It refuses a value that looks like a credential, using a short list of shapes (a bearer token, `password=...` and similar, a few known token prefixes, a private key header, a partly masked value, a long opaque string). `check` applies both rules to rows already in the log. `append` also refuses to add to a log that does not pass `check`.

## The five kinds, with one example of each

Every example below is a row copied from `audit-log-all-events.md`, from the run Beau made on 2026-11-11. The work was simulated: the "pretend tracker" was a temporary file, and `SIM-101`, `user-a` and `user-b` are made up.

### read

Something was looked at and nothing was changed. Confirmed is `n/a`.

| Seq | Time (UTC) | Kind | Action | Target | Actor | Confirmed | Outcome | Ref | Chain |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 2026-11-11 15:36:22 | read | Read the ticket's current assignee | pretend tracker, ticket SIM-101, field assignee | beaubrown (ran run_workflow.py) | n/a | Done. Assignee is user-a. Nothing changed. |  | 57d9f564d0a86882 |

### preview

A write was shown before it happened. Nothing is changed by a preview. Its Confirmed field says the question was asked; the answer is in a later row, because earlier rows are never edited. If the person says no, a second preview row records that and names the first in Ref.

| Seq | Time (UTC) | Kind | Action | Target | Actor | Confirmed | Outcome | Ref | Chain |
|---|---|---|---|---|---|---|---|---|---|
| 2 | 2026-11-11 15:36:22 | preview | Previewed changing the assignee from user-a to user-b | pretend tracker, ticket SIM-101, field assignee | beaubrown (ran run_workflow.py) | Not yet. Asked at the prompt; the answer is in a later row. | Shown on screen. Nothing changed. |  | 14f8e036b03aeaa6 |

### confirmed write

A change that was made, recorded with the approval it had. Ref names the preview it came from, and the check enforces that link. In rows written by `run_workflow.py`, Confirmed says whether the yes arrived through a terminal or was piped in. The check does not judge what Confirmed says.

| Seq | Time (UTC) | Kind | Action | Target | Actor | Confirmed | Outcome | Ref | Chain |
|---|---|---|---|---|---|---|---|---|---|
| 5 | 2026-11-11 15:36:30 | confirmed write | Changed the assignee from user-a to user-b | pretend tracker, ticket SIM-101, field assignee | beaubrown (ran run_workflow.py) | Yes, typed at the prompt | Done. Applied once, on attempt 2. | 2 | 666ee70460346ef4 |

### failure

Something was tried and did not work. The outcome gives the reason as a short description and a code from a fixed list in the tool. The error's own message is never copied into the log, because a real system's error text can quote the record or the request.

| Seq | Time (UTC) | Kind | Action | Target | Actor | Confirmed | Outcome | Ref | Chain |
|---|---|---|---|---|---|---|---|---|---|
| 3 | 2026-11-11 15:36:25 | failure | Tried to change the assignee from user-a to user-b (attempt 1) | pretend tracker, ticket SIM-101, field assignee | beaubrown (ran run_workflow.py) | Yes, typed at the prompt | Failed. Reason: the pretend tracker did not answer in time (code SIM_TIMEOUT). The tool does not yet know whether the change was applied. | 2 | 3b049cd28d79e33f |

### recovery

What was done after a failure to find out what state things were left in. Ref names the failure. Here the tool read the ticket again and found it unchanged, so the same change could be tried again.

| Seq | Time (UTC) | Kind | Action | Target | Actor | Confirmed | Outcome | Ref | Chain |
|---|---|---|---|---|---|---|---|---|---|
| 4 | 2026-11-11 15:36:25 | recovery | Read the ticket again after the failure | pretend tracker, ticket SIM-101, field assignee | beaubrown (ran run_workflow.py) | n/a | Assignee is still user-a. The failed attempt changed nothing. The same change can be tried again. | 3 | f289a2f03a67ed3f |

## Corrections

An earlier row is never edited or removed. If a row turns out to be wrong, the correction is a new row at the bottom that names the earlier row in Ref.

## How a changed row is caught

1. **The shape of the file.** `check` requires the file to be exactly the tool's fixed heading followed by rows written byte for byte as the tool writes them. A second table above the real one, a changed column label, a note under the table, a blank line between rows, changed spacing or changed line endings each fail the check.
2. **The chain.** A row's Chain value is the first 16 hex characters of the SHA-256 of: the previous row's Chain value, a line break, then this row's other nine cells joined with `|`. The first row uses the word `GENESIS` in place of a previous value. If a cell is changed, a row before the last is removed, or rows are moved, a Chain value no longer matches. Removing the last row leaves the chain intact; the anchor catches that.
3. **The anchor file.** `participant/context/audit-log-all-events.anchor` holds the number of rows and the last Chain value. `append` updates it. If rows are cut from the end, or someone recomputes every Chain value after an edit, the log no longer matches the anchor.
4. **The committed anchor.** The anchor file on disk could be rewritten along with the log. A copy of it in a Git commit is not changed by editing files. `check --anchor-git-ref <commit>` compares the log with the anchor as it was at that commit: the log must still have at least that many rows, and the row at that count must still have that Chain value.

To check the log, from the repository folder:

```
python3 participant/evidence/base-camp-audit-log/base-attempt-002/scripts/auditlog.py check participant/context/audit-log-all-events.md
```

## What this does not do

Known so far; there may be others.

- It does not stop someone editing the file. It makes the changes listed above show up when the check is run.
- Rewriting the log and the anchor file together passes the plain check. Comparing with a committed anchor covers that only if the commit is one the editor cannot replace. Here the commit is pushed to the participant's own fork, whose owner could force-push, so it depends on someone else (the reviewer, or the pull request on the program's repository) holding the commit. Nothing in the tool records which commit to trust.
- Actor and Confirmed are text supplied by whatever calls `append`. The check only requires them not to be empty. A caller could write a confirmed write row whose Confirmed says "No".
- "Typed at the prompt" means the answer came through a terminal. A program can drive a terminal too (one of the tests does). So the log cannot prove whether a person or an AI agent running under the same account gave the answer, and Actor is the same account name for both.
- One preview can be named by more than one confirmed write, and a recovery's target is not compared with its failure's target.
- The sample log has no correction row. A correction would be added as a new row of one of the five kinds with the corrected row in Ref; there is no separate kind for it.
- If `append` is interrupted after writing the row and before updating the anchor, the check then fails ("rows were added without the tool") and `append` refuses from then on, until the anchor is repaired by hand. An honest crash looks the same as tampering.
- Time comes from the computer's clock and is not checked against any outside clock. A row with a time in the future passes the check and blocks later appends until that time.
- The credential list is short and matches shapes, not meaning. It misses, for example, a password written without `=` or `:`, a short token, a card number and an email address. It refuses some ordinary values, such as a 40-character commit ID.
- The Chain value is 64 bits of a SHA-256. That is meant to catch edits, not to resist someone searching for a colliding row.
- The anchor's name comes from the log's name without its extension, so `a.md` and `a.txt` in one folder would share an anchor.
- Two programs appending at the same moment are not handled.
- Invisible or blank characters outside those four categories are accepted, for example U+034F, U+FE0F, U+3164 and U+2800. A cell made only of U+3164 counts as not empty and can look empty. Look-alike letters, pipe look-alikes such as U+FF5C, and HTML or Markdown such as `<br>` or `<!--` inside a cell are accepted too. They are covered by the chain once written, but what a Markdown viewer shows for them was not assessed.
- Three inputs make the tool stop with a Python error instead of a clean message, with nothing written: a Ref of more than 4300 digits (in `append`, or already in the file for `check`), and an argument holding bytes that are not valid UTF-8.
- A single field of tens of thousands of letters with no spaces makes `append` and later checks slow (about 10 seconds at 40,000 letters). No length limit is applied.
