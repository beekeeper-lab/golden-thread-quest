# Redaction notes: sample-meeting

Transcript `tr-2026-10-21-checkout-refinement`, ingested into `sample-meeting.md`.

## What was redacted, and why

| Utterance | What was there | Replaced with | Why |
|---|---|---|---|
| U-0005 | An email address Dana proposed for test receipts | `[REDACTED:EMAIL]` | An email address is contact information. |
| U-0015 | The team's staging phone line | `[REDACTED:PHONE]` | A phone number is contact information, even a shared one. |
| U-0022 | Jordan's email address | `[REDACTED:EMAIL]` | An email address is contact information. |

The skill applies the same rules for email addresses and phone numbers to every utterance, speaker label, speaker-list entry, and provenance value, without deciding case by case. The table above was checked by reading the raw transcript against the record: these three are the only contact details in it.

## What was kept

- **Names.** Priya, Marcus, Dana, and Jordan (mentioned in U-0021 and U-0022) are kept, because the record exists to show who said what. All four are fictional. Jordan's name stays even though Jordan was not in the meeting, because it is part of what was said; only the contact detail is removed.
- **Ordinary numbers**, such as the sprint number and the story-point guesses in U-0023.
- **U-0016**, Marcus's instruction to the AI assistant. It is something that was said, so it stays word for word.

## Where the original is

The unredacted WebVTT file and its meeting file are at `local-data/transcripts/2026-10-21-checkout-refinement.vtt` and `.meeting.json` in my own clone. `local-data/` is ignored by git, so `gtq hand-in` never sends them. The provenance file's `source_sha256` identifies the original exactly.

There is no recording. The meeting is fictional, and an AI assistant wrote the transcript directly as WebVTT text at my direction. The provenance file's `capture_source` and `transcription_tool` say the same.

Because there is no recording, the times in the record are invented, as if they were measured from the start of one. The record's front matter still describes them as offsets from the start of the recording, which is the skill's general wording for real meetings.

For a real meeting, someone should also read the transcript for what the rules cannot catch, such as numbers spoken as words, addresses, and personal details said in passing, and get the participants' agreement before keeping a named record.
