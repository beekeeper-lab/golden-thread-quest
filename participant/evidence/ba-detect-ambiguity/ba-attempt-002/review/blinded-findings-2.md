# The findings as the second independent reader was given them

A copy of findings.md, with the clarified definitions, and with the Type, Also considered and Effort lines
taken out of each finding.

---

# Findings with their types removed

## How a requirement is judged

One question decides whether there is a defect at all:

> Would two competent testers, reading only this text, write the same test?

If they would, the requirement is sound and has no finding. A word that the glossary or another requirement
defines is read with that definition.

If they would not, four questions are asked **in this order**, and the first that is answered yes gives the
type. A finding has exactly one type.

1. **Contradictory.** Is there another requirement such that no system could satisfy both? The clash must hold
   on every reasonable reading of both. If one reasonable reading lets a system satisfy both, the answer is no.
2. **Untestable.** Is there no observation at all that could show the requirement is met, however its words
   are read? A requirement that could be shown to be broken and could never be shown to be met counts as
   untestable.
3. **Incomplete.** Is a fact that a tester needs simply absent from the text? Absent means that no word in the
   requirement speaks of it at all. If a word does speak of it, however loosely, the answer is no.
4. **Vague.** Are the facts all present, with a word or phrase that has more than one reasonable reading? This
   is where a point belongs when the text does speak of it, in words that leave the answer open.

The order runs from the most serious to the least. A contradiction cannot be mended by making one requirement
clearer. An untestable requirement cannot be tested on any reading. An incomplete one needs a fact added. A
vague one needs a word pinned down.


## F-01
- Requirement: REQ-04 and REQ-12
- Words in REQ-04: "at any time before the booking's start time"
- Words in REQ-12: "shall not accept a cancellation from a member less than two hours before the booking's start time"
- A tester could not decide: whether a member's cancellation 90 minutes before the start is to be accepted or refused. REQ-04 says accepted and REQ-12 says refused.
- If unanswered: whichever is built, one of the two requirements fails its test, and members are either let out of a rule that was meant to hold or held to one that was not.
- Question: In the two hours before a booking starts, may the member cancel it or not?

## F-02
- Requirement: REQ-14 and NFR-04
- Words in REQ-14: "complete booking history for the previous 24 months"
- Words in NFR-04: "permanently deleted 12 months after the date of the booking"
- A tester could not decide: what a staff user should see for a booking made 18 months ago. REQ-14 says it is listed. NFR-04 says it no longer exists.
- If unanswered: either records are kept a year longer than the constraint allows, or staff are shown a history that is called complete and is missing its older half.
- Question: For how long are booking records kept, and is that the period a staff user's history must cover?

## F-03
- Requirement: REQ-11
- Words: "genuinely intend to use them"
- A tester could not decide: what to observe. A system can see what a member does. No test can observe what a member intends at the moment of booking.
- If unanswered: the requirement can never be shown to be met or not met, so nothing is built for it, or something is built that nobody can check.
- Question: What that the system can observe would count as a member not intending to use a room, and what is the system to do when it sees it?

## F-04
- Requirement: NFR-05
- Words: "No fault in the system shall ever"
- A tester could not decide: when to stop. A test can show that one fault loses a booking. No set of tests can show that no fault ever does.
- If unanswered: the requirement is passed on the strength of the faults somebody thought to try, and reads as a promise about all of them.
- Question: Which faults must a confirmed booking survive, and how is its survival to be checked after each?

## F-05
- Requirement: REQ-06
- Words: "shortly before"
- A tester could not decide: when to look for the email. Ten minutes before the start and the evening before are both shortly before.
- If unanswered: the reminder arrives too late to act on, or so early that it is forgotten, and either passes.
- Question: How long before a booking's start time is the reminder email to be sent?

## F-06
- Requirement: NFR-03
- Words: "recent versions of popular desktop and mobile browsers"
- Words: "work correctly"
- A tester could not decide: which browsers and which versions to test in, and what would count as working in each.
- If unanswered: the site is tested in whatever browsers the tester has, and a member with another one finds it broken after release.
- Question: Which browsers and which versions must the website support, and which of its functions must work in each?

## F-07
- Requirement: REQ-08
- Words: "accumulates three no-shows"
- A tester could not decide: over what period the three are counted, and whether or when the member can book again. Three in a month and three in ten years both accumulate.
- If unanswered: a member is barred for good by three missed bookings years apart, or the count quietly drops as old records are deleted under NFR-04, and nobody chose either.
- Question: Over what period are no-shows counted, and how does a member who has been prevented from booking become able to book again?

## F-08
- Requirement: REQ-13
- Words: "shall refuse new bookings for them"
- A tester could not decide: what should happen to a booking that already exists on a date when the room is marked out of service. The text covers new bookings only.
- If unanswered: a member arrives for a booking in a room that is closed, or their booking disappears and nobody tells them.
- Question: When a room is marked out of service for dates on which it already has bookings, what is to happen to those bookings and to the members who hold them?

## F-09
- Requirement: REQ-13
- Words: "as unavailable"
- A tester could not decide: what marking to expect on an out-of-service slot. REQ-02 marks every slot as either "available" or "booked". Here "unavailable" could be a third marking, or could mean shown as booked.
- If unanswered: a third marking is built and the test of REQ-02 fails, or closed rooms are shown as booked and look as if they were in demand.
- Question: Is an out-of-service slot shown with a marking of its own, or as "booked", and if it has its own, is that a third marking beside the two in REQ-02?

## F-11
- Requirement: NFR-01
- Words: "making requests at the same time"
- A tester could not decide: how often each of the 50 members makes a request. Fifty who ask once a minute and fifty who ask without pause are very different loads.
- If unanswered: the same system passes for one tester and fails for another, and the result says more about the test than about the system.
- Question: How often does each of the 50 signed-in members request the availability page during the 30-minute run?

