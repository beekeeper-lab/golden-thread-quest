# Jira create-story

Written by an AI assistant (Claude) at the participant's direction.

## 1. Purpose

This skill creates one Jira story from a local draft, and ties the local record to the story it made. It
previews first, creates only after a person confirms that exact preview, reads the new story back to compare
it with what was sent, and writes the story's key and id into a local link file. Once a draft is linked it is
never created again.

**It writes to Jira.** The one write it can make is the creation of one story, and only in a project on the
sandbox allowlist.

Run it from the repository root:

    python3 participant/skills/jira-create-story/create.py preview --source live --draft DRAFT.md --link LINK.md \
        --allowlist participant/context/jira/update/sandbox-allowlist.json --catalog FOLDER --state FOLDER

`--source fake` runs against the made-up Jira in `fake_jira.py`, with no network and no credentials.

## 2. Configuration

A live run reads three environment variables, set in the local shell and never stored in a file:
`JIRA_BASE_URL`, `JIRA_EMAIL` and `JIRA_API_TOKEN`. The output is searched for the token, the email address and
their encoded form before it is shown. The site's address is shown on screen, so the person confirming can see
where the write would go, and is replaced by a marker in anything saved.

| Option | What it is |
|---|---|
| `--draft FILE` | The story draft, in the format of the `jira-create-story-preview` skill, with its citations. |
| `--link FILE` | The link file: the local record of the story. One draft has one link file. |
| `--allowlist FILE` | The sandbox allowlist: projects by project id, each with a fingerprint of its site's address. |
| `--catalog FOLDER` | The local catalog to search for duplicates. |
| `--state FOLDER` | Where previews are kept between the preview and the confirmation. |
| `--log FILE` | Also save the output, with the site's address removed. |
| `--result FILE` | Save the result record of a create, as Markdown. |

## 3. The four commands

| Command | What it does | Writes to Jira |
|---|---|---|
| `preview` | Shows the site, the project, every field, the exact payload, the permission check, the duplicate checks and a fingerprint. | No. It has no way to. |
| `confirm` | Creates the story of one preview, named by its fingerprint, then records and compares it. | One create |
| `verify` | Reads the linked story from Jira by its issue id and compares it again with the payload that was sent. | No |
| `reconcile` | After a create whose result was never recorded: finds the story by its marker and links it. | No |

Exit codes: 0 done. 1 refused, nothing written to Jira. 2 a create was sent and a person needs to look.

## 4. The preview

The payload is built by the `jira-create-story-preview` skill's own function, `build_payload`, from the same
draft, so a preview here and a preview there cannot mean different things. Everything that skill checks is
checked: the citations, the required fields, the values Jira allows.

This workflow adds three things.

- **A marker.** One label, `gtq-` and eight random characters, new for each preview. It is part of the payload
  and is shown as such. See section 7.
- **A same-title check asked of Jira.** How many stories in the project have exactly this title, and how many
  more Jira's text search returns for its words. This does not depend on the local catalog.
- **A check of the link file.** A draft that is already linked is refused.

The duplicate search of the local catalog is shown as before, with how much of the project the catalog covers.

## 5. The confirmation

`confirm` needs `--fingerprint` and `--confirmed-by`. There is no option that creates without them. It
refuses, creating nothing, unless all of this holds at that moment:

- the saved preview is unaltered, has not been used, and is at most 15 minutes old;
- the draft file is byte for byte the one that was previewed;
- the payload, worked out again from the draft and from Jira as it is now, has the SHA-256 of the previewed one;
- the project is on the sandbox allowlist, for this Jira site;
- Jira says this identity may create stories there;
- the draft has no link file, and no story in Jira carries this preview's marker.

Then, in this order:

1. It writes the link file, saying a create is being sent and its result is not yet recorded.
2. It sends the create, once. The bytes sent are the bytes whose SHA-256 the preview showed.
3. It writes the key and the issue id that came back into the link file.
4. It reads the story back from Jira by its issue id.
5. It compares the story with the payload, field for field, and writes the comparison and the result record.

The order matters. If anything fails after step 2, the link file already says that a create went out.

## 6. Read back and compare

Each field the payload sent is compared with the story read back.

| Field | The same when |
|---|---|
| Project, issue type, priority, a custom choice | the id read back is the id sent |
| Summary, due date | the value read back equals the value sent |
| Labels | the same labels, in any order |
| Components | the same component ids |
| Parent | the same parent key |
| Description | the same structure and text. The verdict says whether it came back identical, or the same with Jira's own block identifiers added. |

Fields Jira set that the payload did not send are listed as Jira's. A few are shown with their values: the
status, the priority, the creation time. A person is shown only as "a person". A project is shown by its key
and id.

If any field differs, the command says so, records it in the link file, and exits with code 2. The story exists
by then, so a person needs to look.

## 7. Not creating the same story twice

Jira has no documented way to refuse a second create of the same story, and none to try a create without
making one. The protection is this workflow's own, in three layers.

1. **The link file.** A draft that is linked to a Jira story is refused by `preview` and by `confirm`.
2. **The intent is written before the create is sent.** A link file that says a create was sent and never
   recorded also stops `preview` and `confirm`. They say to run `reconcile`.
3. **The marker.** `reconcile` asks Jira for stories in the project carrying the preview's marker label. Exactly
   one: it is linked, read back and compared. None: it says so, and that Jira's search can lag a few seconds
   behind a create, and it creates nothing. More than one: nothing is linked and a person needs to look.

A create is sent once in a run and never retried. When no answer comes back, the workflow says it is not known
whether the story was created.

When Jira answers a create with a refusal, the workflow looks for the marker before believing it. Only if no
story carries the marker does it remove the link file and report that nothing was created.

What this does not stop: the same story being created some other way, by a person or another tool. The
same-title check in the next preview would report it.

## 8. The link file

The local story. It holds the story's title, description and sources; the Jira key and issue id; which preview
it came from; who confirmed and when; the payload that was sent; and the read-back comparison.

The story is identified by its issue id. `verify` fetches the story by that id. If the key has changed in
Jira, it reports the change, matches all the same, and updates the key in the link file, keeping the earlier
one.

## 9. Tests

    cd participant/skills/jira-create-story && python3 -m unittest discover -s tests -v

## 10. What it does not do

- It does not delete or edit a story. Removing one it created is done by hand in Jira.
- It does not stop a duplicate made outside this workflow.
- `reconcile` cannot prove a story does not exist: a search that finds nothing may be a search that lags.
- Its protection against a second create is local. A second machine without the link file would rely on the
  same-title check and on a person reading the preview.
- It creates stories with the fields the preview skill supports: no assignee, no sprint, and single-choice
  custom fields only.
