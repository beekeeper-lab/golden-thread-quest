# Proof · base-camp-repository-safety

Attempt: `base-attempt-001`

## What was built

- **An ownership document** that splits the repository into three zones (program-owned, participant-owned, generated or private) and has a table of what each actor may change: me, the application, the AI agent, `gtq hand-in`, the reviewer, and the program maintainers.
- **An audit log** with one row per action: time, kind (read, local write or external write), action, target, who started it, whether a write was confirmed, and the outcome. It includes reads, confirmed local writes, a push to GitHub that was previewed and not approved, and the three runs of the workflow below.
- **A small demonstrated workflow**, `create-fake-ticket.py`. It pretends to create a ticket in an outside system. The "outside system" is a local file in `local-data/`, which Git ignores, so no real service is touched. The script:
  - reads the fake system and looks for the ticket by its key (`GTQ-DEMO-1`) before doing anything
  - if the ticket already exists, creates nothing
  - if not, shows a preview of the exact write and only creates it if I type `yes`
  - writes to a temporary file and swaps it in, so stopping part way cannot leave a half-written file
  - adds a row to the audit log on every run, whatever the outcome

Claude (the AI agent) drafted these files at my request. I reviewed them and ran the workflow myself.

## Where the important artifacts are

- Ownership document: `participant/context/repository-ownership.md`
- Audit log: `participant/context/audit-log.md`
- Workflow script: `participant/tools/create-fake-ticket.py`
- First run output: `participant/evidence/base-camp-repository-safety/base-attempt-001/logs/first-run.txt`
- Second run output: `participant/evidence/base-camp-repository-safety/base-attempt-001/logs/second-run.txt`
- The fake outside system: `local-data/fake-tracker.json` (ignored by Git, so it is not in the hand-in)

## How to reproduce the behavior

From the repository folder, with no `local-data/fake-tracker.json` yet:

1. `python3 participant/tools/create-fake-ticket.py`, then press Ctrl-C at the prompt. Expected: "Stopped before confirming. Nothing created." The fake tracker file is not created.
2. `python3 participant/tools/create-fake-ticket.py`, then type `yes`. Expected: "Created GTQ-DEMO-1."
3. `python3 participant/tools/create-fake-ticket.py` again. Expected: no prompt, and "GTQ-DEMO-1 already exists (matched by key). Nothing created."

To start over, delete only `local-data/fake-tracker.json` by its full name. Do not delete the whole folder.

## What was tested or validated

**Interruption test (2026-10-14, 17:42:15 UTC).** I ran the workflow and pressed Ctrl-C at the confirmation prompt, after the preview but before anything was written. The script said nothing was created. Afterwards `local-data/fake-tracker.json` did not exist, and the audit log recorded the run as "Interrupted at the prompt. Nothing created." with Confirmed: No.

**Resume and rerun test.** I then ran it twice in a row:
- First run (17:42:43 UTC): the fake system had 0 items. It showed the preview, I typed `yes`, and it created `GTQ-DEMO-1`. Saved in `logs/first-run.txt`.
- Second run (17:43:14 UTC): the fake system had 1 item with that key. It did not prompt and created nothing. Saved in `logs/second-run.txt`.
- Afterwards the fake tracker held exactly one item, `GTQ-DEMO-1`, so the rerun made no duplicate. The audit log has a row for each run.

**Before my runs,** Claude tested the script in a throwaway copy of the folders: answering "no", closed input, a Ctrl-C signal, "yes", and a rerun. Each did what it should, and the real repository was not touched.

**Ownership document check.** Every path in it was checked against Git: every top-level item is listed, every program-owned folder is tracked, and every item listed as ignored is ignored. A separate reviewer agent also read the first draft against the quest's criteria. It found real gaps (no actors, wrong advice about committing, missing paths), and I had them fixed.

**Registered validator.** `validate-repository-foundation` is run from the evidence page after this file is written. It checks the ignore rules, this file, and the evidence for secrets. It does not read the ownership document or the audit log, so a reviewer has to judge those.

## Remaining limitations

- The outside system is a local file, not a real service. A real one could fail or time out partway through, which this does not test.
- It handles one fixed ticket. Matching by key only prevents duplicates when the key is fixed and known in advance.
- Two runs at the same moment could both see "no ticket" and both create one. There is no lock. A real integration would need one, or a system that rejects a duplicate key.
- If the script stopped after creating the ticket but before writing the audit row, the ticket would exist with no row. The next run would still find it and create nothing, but that run's row would be the only record.
- The audit log is append-only by habit, not enforced. Anyone could edit an old row.
- The "actor" in the script's audit rows is the computer's user name, not a checked identity.
- The quest file names the log folder `attempt-001`, but my attempt folder, created by the application, is `base-attempt-001`. I used the folder the application created.
- Stretch goals (pre-commit secret scan, a test that cleanup cannot delete participant files, a dry-run transcript) were not done.

## Reflection

- **Enforced by code:** the script will not create the ticket without a typed `yes`, will not create it twice (the key check), and cannot leave a half-written file. The validator also checks that `.gitignore` covers generated output, local data, environment files and credentials.
- **Enforced by repository structure:** `.gitignore` keeps `local-data/`, generated output and credential files out of Git. `gtq hand-in` stages only `participant/`, so nothing outside my folder goes into my pull request.
- **Still depends on human judgment:** what the AI agent is allowed to change (my rule, not enforced by anything), whether I type `yes`, not hand-editing the files the application owns, keeping the audit log honest, and making sure nothing private ends up in `participant/`.

## Live demonstration (optional evidence)

The optional item "Demonstrate stopping and safely resuming an agent workflow without duplicate output" can only be recorded by a reviewer watching. I am glad to show it live. It takes about two minutes, from the repository folder:

1. `rm local-data/fake-tracker.json` to reset the fake system. This deletes that one file by its full name, nothing else.
2. `python3 participant/tools/create-fake-ticket.py`, then press Ctrl-C at the prompt. It stops and creates nothing.
3. Run it again and type `yes`. It resumes and creates `GTQ-DEMO-1` once.
4. Run it a third time. It finds `GTQ-DEMO-1` by its key and creates nothing.
5. `cat local-data/fake-tracker.json` shows exactly one ticket, and the bottom of `participant/context/audit-log.md` shows one row per run.

## Credentials (criterion 2)

Added after submission, so the reviewer does not have to infer it.

- The only credential this quest used is my GitHub sign-in, used by `gtq hand-in` to push and open the pull request. It comes from the GitHub command-line tool: `gh auth status` shows I am signed in, with the token stored in the macOS keychain. Git gets it through `gh auth git-credential`, which is set up as Git's credential helper for github.com.
- No token, password or `.env` file is in this repository. The only `.env` file is `.env.example`, which holds no real values. `.gitignore` blocks `.env`, `.env.*`, key, token and credential files, and the repository-foundation check confirmed those rules.
- The fake-ticket workflow needs no credentials, because it never talks to a real service.

## Sensitive values

There are no secrets, tokens, cookies, customer names or private ticket content in this evidence. The only "ticket" is a fake one I made up for this test. Nothing here connected to a real service, and the fake system's data stays in `local-data/`, which Git ignores.
