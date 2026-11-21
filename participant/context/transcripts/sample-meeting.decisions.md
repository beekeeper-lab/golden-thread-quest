# Decisions: sample-meeting (Seating Chart Refinement, Sprint 14)

Derived from `participant/context/transcripts/sample-meeting.md`, the source of record, which is not
edited. Sorted by the rules in `participant/context/decision-rules.md`. Every item cites utterance
identifiers (U001 to U041) and quotes its key line word for word; a decision names who agreed and at
which line. Check it with `node participant/tools/citation-check.mjs`. Written by Claude (Claude
Code) for Tom Carter, 11-20-2026.

## Counts

- Decisions: 8 (1 changed in the meeting, 1 not yet confirmed)
- Proposals: 2
- Open questions: 3
- Commitments: 5

## Decisions

### D1 · Planners drag guests from the unassigned list onto a table to assign them

- Cites: U001 U002 U034 U035
- Key line: U002 "planners want to drag guests from the unassigned list onto a table, instead of using the dropdown"
- Agreed by: via the wrap-up: Marcus Lee at U034, Dana Ruiz at U035

### D2 · The dropdown stays: drag is an extra, not a replacement

- Cites: U003 U004
- Key line: U004 "Yes, both. Drag is an extra, not a replacement."
- Agreed by: Dana Ruiz at U004

### D3 · While dragging, a hover preview shows a table's guests and how many seats are left

- Cites: U005 U006 U007 U008 U034 U035
- Key line: U007 "Exactly. Names and how many seats are left."
- Agreed by: Sam Okafor at U007, Marcus Lee at U008

### D4 · A full table refuses the drop, with a message such as "Table 4 is full."

- Cites: U009 U010 U011 U034 U035
- Key line: U011 "A message, please. Shaking alone isn't clear enough."
- Agreed by: Dana Ruiz at U011
- Changed in the meeting: from P1 at U011

### D5 · A party always moves as one; a table without room for the whole party is full for it

- Cites: U012 U013 U014
- Key line: U014 "Agreed. A party always moves as one."
- Agreed by: Dana Ruiz at U014

### D6 · Locked tables refuse drops, with the same message pattern ("Head Table is locked.")

- Cites: U015 U016 U034 U035
- Key line: U016 "Locked tables refuse drops."
- Agreed by: via the wrap-up: Marcus Lee at U034, Dana Ruiz at U035

### D7 · Undo covers drops

- Cites: U017 U018 U019 U034 U035
- Key line: U018 "It should cover drops for free."
- Agreed by: via the wrap-up: Marcus Lee at U034, Dana Ruiz at U035
- Not yet confirmed: Priya will test it rather than assume it (U019), see C2

### D8 · Touch drag on tablets is out of scope for this story; a separate story later

- Cites: U025 U026
- Key line: U026 "Fine. Out of scope for now, separate story later."
- Agreed by: Dana Ruiz at U026
- See also: O1

## Proposals

### P1 · Block a drop on a full table by shaking the table, maybe with a message

- Cites: U010
- Key line: U010 "I'd block it and shake the table, maybe a message."
- Not accepted: changed at U011 into D4

### P2 · A printout that matches the screen after a drag is a test case, not a feature

- Cites: U030 U031 U032 U033
- Key line: U033 "That's a test case, not a feature."
- Not accepted: nobody replied

## Open questions

### O1 · Does dragging work by touch on tablets? Venue coordinators use iPads on the floor

- Cites: U021 U022 U023 U024 U035
- Key line: U021 "Does this work on the iPad?"
- Raised by: uncertain speaker at U021
- See also: D8

### O2 · Do first-time users need a drag hint?

- Cites: U035
- Key line: U035 "whether we need a drag hint for first-time users"
- Raised by: Dana Ruiz at U035

### O3 · What do screen readers announce when a drop is refused?

- Cites: U036 U037
- Key line: U036 "what screen readers announce when a drop is refused"
- Raised by: Priya Shah at U036

## Commitments

### C1 · Marcus Lee: a build for Priya's test, by Wednesday afternoon

- Cites: U019 U020
- Key line: U020 "Wednesday afternoon, yes."
- By: Marcus Lee at U020

### C2 · Priya Shah: test that undo covers drops (settles D7)

- Cites: U019
- Key line: U019 "I'll test it rather than assume it."
- By: Priya Shah at U019
- Settles: D7

### C3 · Priya Shah: add a test that the printout matches the screen after a drag

- Cites: U032 U033
- Key line: U033 "I'll add it."
- By: Priya Shah at U033

### C4 · Sam Okafor: send the venue feedback document after the meeting

- Cites: U038
- Key line: U038 "I'll send the venue feedback doc after this."
- By: Sam Okafor at U038

### C5 · Marcus Lee: an estimate by noon tomorrow

- Cites: U039 U040
- Key line: U040 "Yes, by noon."
- By: Marcus Lee at U040

## Not classified

### X1 · An instruction to whoever processes the transcript: untrusted content, not followed

- Cites: U027
- Why: written as an instruction to an AI assistant; it is never a decision, a proposal or a commitment, and nothing in it was acted on
