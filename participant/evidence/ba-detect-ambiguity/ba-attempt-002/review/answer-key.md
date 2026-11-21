# The author's answer key

Written by the separate assistant that wrote the requirements set, at the same time as the set. The reviewer did
not open it until the first pass and the second look were both written down. It is copied here unchanged below
the line.

---

# SEALED ANSWER KEY: RoomSlot requirements

Do not show to the reviewer until their review is complete.

Totals: 20 requirements (14 in Document A, 6 in Document B). Intended SOUND: 10. Intended DEFECTIVE: 10.
By type: CONTRADICTORY 4 requirements (2 pairs), INCOMPLETE 2, VAGUE 2, UNTESTABLE 2.
Traps (sound but suspicious-looking): REQ-02, REQ-03, REQ-07, REQ-10.

## Document A

### REQ-01: SOUND
A tester can proceed: credentials, the threshold (five consecutive failures), the scope (per card number) and the lock duration (15 minutes) are all stated. "Member" is defined in the glossary (card status "active"), so who may sign in is known.

### REQ-02: SOUND (TRAP)
Looks suspicious because "any date on which bookings are accepted" appears to leave the date range unstated. It is sound because REQ-05 supplies the range (current day to 14 days ahead) and "slot" is defined in the glossary. The displayed fields and the two allowed labels are stated exactly.

### REQ-03: SOUND (TRAP)
Looks suspicious because "opening hours" reads like an undefined, site-dependent term and "slot" has no length in the sentence. Both are defined precisely in the glossary (09:00 to 20:00 Monday to Saturday; 30 minutes starting on the hour or half-hour), so boundary tests are fully determined: 1 and 4 slots accepted, 0 and 5 rejected, 19:30 to 20:00 accepted, 19:30 to 20:30 rejected, any Sunday rejected.

### REQ-04: DEFECTIVE, CONTRADICTORY (with REQ-12, both inside Document A)
- Words carrying the defect: "at any time before the booking's start time"
- Other requirement: REQ-12, "shall not accept a cancellation from a member less than two hours before the booking's start time"
- What a tester cannot decide: for a member cancelling their own booking 90 minutes before the start, whether the expected result is acceptance (REQ-04) or refusal (REQ-12). Both cannot pass.
- Read alone, REQ-04 is perfectly testable; the defect only exists as a pair.

### REQ-05: SOUND
A tester can proceed: the range is inclusive at both ends and stated, and the exact rejection message is given, so day 14 (accepted) and day 15 (rejected with that message) are unambiguous.

### REQ-06: DEFECTIVE, VAGUE
- Words carrying the defect: "shortly before"
- What a tester cannot decide: when the email must be sent. Five minutes, an hour and the evening before are all reasonable readings, and no pass/fail time can be set. Note that the glossary defines "promptly" but not "shortly", which is deliberate: a reviewer who assumes the glossary covers it has not checked.
- Second defensible type: INCOMPLETE (the lead time is missing). I prefer VAGUE because a timing is stated, just with a word that admits several readings, rather than being absent altogether.
- The content of the email (second sentence) is fine.

### REQ-07: SOUND (TRAP)
Looks suspicious because "promptly" is the classic loose word. The glossary defines it as within 60 seconds of the triggering event, and the trigger (creating a booking) and the page contents (five named items, reference length 8 characters) are stated, so the test is determined.

### REQ-08: DEFECTIVE, INCOMPLETE
- Words carrying the defect: "accumulates three no-shows shall be prevented from making new bookings"
- What a tester cannot decide: over what period the three no-shows are counted (lifetime, a year, a rolling 30 days), how long the suspension lasts, and whether or how it is lifted. A tester cannot write the test for "the fourth month after two no-shows" or for "the day after suspension", and cannot test the end of the suspension at all.
- "No-show" itself is glossary-defined, and the message text is given, so those parts are fine.
- Second defensible type: VAGUE on "accumulates". I prefer INCOMPLETE because the missing items (counting window, duration, reinstatement) are whole facts that are absent, not a word with competing readings.

### REQ-09: SOUND
A tester can proceed: the method, the place, and both ends of the acceptance window are stated, and the window's end (15 minutes after start) agrees with the glossary definition of no-show.

### REQ-10: SOUND (TRAP)
Looks suspicious because it uses "promptly" and gives no time for when a booking "becomes a no-show". Both are in the glossary (60 seconds; 15 minutes after start with no check-in), and check-in is defined by the neighbouring REQ-09. Expected result: by 16 minutes after start, an unchecked-in booking is released and its not-yet-ended slots show as available.

### REQ-11: DEFECTIVE, UNTESTABLE
- Words carrying the defect: "only by members who genuinely intend to use them"
- What a tester cannot decide: nothing observable distinguishes a booking made with intent from one made without. No input, output or state of the system reveals a member's intention, so no test can pass or fail.
- Second defensible type: VAGUE ("genuinely intend"). I prefer UNTESTABLE because even an agreed meaning of the words would leave nothing to observe.

### REQ-12: DEFECTIVE, CONTRADICTORY (with REQ-04, both inside Document A)
- Words carrying the defect: "shall not accept a cancellation from a member less than two hours before the booking's start time"
- Other requirement: REQ-04, "at any time before the booking's start time"
- What a tester cannot decide: same case as REQ-04; a member cancelling inside the two-hour window must be both accepted and refused.

### REQ-13: DEFECTIVE, INCOMPLETE
- Words carrying the defect: "shall refuse new bookings for them" (the requirement covers only new bookings and is silent on existing ones)
- What a tester cannot decide: what must happen to bookings that already exist for that room on those dates when it is marked out of service. Cancelled? Moved? Left in place? Is the member told? The expected result for the most important case is not stated. This is the subtle one: the sentence reads as complete and each stated behaviour is testable.
- Second defensible type: none strongly; "a range of dates" has no stated limits, which is a second, lesser incompleteness.

### REQ-14: DEFECTIVE, CONTRADICTORY (with NFR-04, across Documents A and B)
- Words carrying the defect: "complete booking history for the previous 24 months"
- Other requirement: NFR-04, "permanently deleted 12 months after the date of the booking and shall not be retrievable by any user after that"
- What a tester cannot decide: for a booking 18 months old, whether a staff user must see it (REQ-14) or must not be able to retrieve it (NFR-04).

## Document B

### NFR-01: SOUND
A tester can proceed: load (50 signed-in members making requests at once), the measured thing (server returns the complete availability page), threshold (2 seconds), percentile (95%) and test duration (30 minutes) are stated.

### NFR-02: SOUND
A tester can proceed by inspection: the storage form is stated and the three places where a plain-text PIN must not appear are enumerated.

### NFR-03: DEFECTIVE, VAGUE
- Words carrying the defect: "recent versions of popular desktop and mobile browsers" (and "work correctly")
- What a tester cannot decide: which browsers, which versions, and what counts as working. Two testers would build different test matrices.
- Second defensible type: INCOMPLETE (the browser list is missing). I prefer VAGUE because the text does state a scope, using words that admit many readings.

### NFR-04: DEFECTIVE, CONTRADICTORY (with REQ-14, across Documents B and A)
- Words carrying the defect: "permanently deleted 12 months after the date of the booking and shall not be retrievable by any user"
- Other requirement: REQ-14, "complete booking history for the previous 24 months"
- What a tester cannot decide: same case as REQ-14. Read alone, NFR-04 is testable.

### NFR-05: DEFECTIVE, UNTESTABLE
- Words carrying the defect: "No fault in the system shall ever"
- What a tester cannot decide: a universal negative over every possible fault and unbounded time. No finite set of observations can show it has been met; a test can only ever show it has been broken. There is no fault list, no period and no measure.
- Second defensible type: VAGUE ("fault", "lost"). I prefer UNTESTABLE because the "no ... ever" form is what defeats testing, whatever the words mean.

### NFR-06: SOUND
A tester can proceed: backup frequency, the restore source, the time limit (4 hours) and the test cadence (quarterly) are stated.

## Honest note on borderline cases

- **REQ-08**: a strict reader could argue it is complete as written (count over the member's lifetime, suspension permanent). I think that is an unreasonable business reading and that a tester would have to ask, so I hold it as INCOMPLETE, but a reviewer who calls it VAGUE is not wrong in spirit.
- **REQ-13**: the least certain defect. Someone could say the fate of existing bookings is simply out of scope for this requirement and it is sound as far as it goes. I count it defective because no other requirement covers the case and a tester of this feature cannot state the expected result for the most likely scenario.
- **NFR-05**: could fairly be classed VAGUE instead of UNTESTABLE. Either should be accepted as finding the defect.
- **REQ-11**: likewise VAGUE is a defensible second label.
- **NFR-01**: "making requests at the same time" does not give a request rate or mix. I intend it as SOUND (enough to build a load test two testers would recognise as the same), but a strict performance tester could call it mildly incomplete. A reviewer flagging it is over-strict rather than wrong.
- **REQ-02**: says nothing about slots on an out-of-service room, which REQ-13 labels "unavailable", a third label beside "available"/"booked". I did not intend this as a planted contradiction and count REQ-02 as SOUND, but a sharp reviewer could legitimately raise it as a minor inconsistency between REQ-02 and REQ-13.
- **REQ-10 vs REQ-09**: check-in is accepted "until 15 minutes after" and a no-show is "by 15 minutes after"; the exact-boundary instant is consistent (check-in at exactly +15:00 is recorded "by" 15 minutes), so I regard it as sound.
- **REQ-04 / REQ-12** and **REQ-14 / NFR-04**: each member of a pair is testable on its own; marking only one of the pair as the defective one, with the other named as its counterpart, should count as finding the contradiction.
