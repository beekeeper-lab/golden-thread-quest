# Redaction notes for `sample-meeting`

## What was redacted, and why

| Utterance | What was there | Replaced by | Why |
|---|---|---|---|
| `sample-meeting#U038` | An email address | `[REDACTED]` | Personal contact detail |
| `sample-meeting#U038` | A phone number | `[REDACTED]` | Personal contact detail |

Rules applied (from `participant/skills/ba-ingest-transcript/SKILL.md`, rule 5): email
addresses and phone numbers become `[REDACTED]`. Speaker names are kept, because they are the
attribution the later work depends on. In this exercise every name, address and number is
made up.

## Where the unredacted original is

- `local-data/transcripts/raw/sample-meeting.raw.txt`, in this repository's folder but ignored
  by Git (`.gitignore` line 9, `/local-data/`), so it is never committed or handed in.
- Its SHA-256 is recorded in `sample-meeting.provenance.yaml` (`original_sha256`). That lets
  anyone holding the original confirm it is the file this record came from, without the
  original ever being in source control.
- In real use the original would sit in the team's restricted recording store, and the
  provenance file would name that location instead.
