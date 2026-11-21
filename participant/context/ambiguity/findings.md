# Findings: review of the RoomSlot requirements

A review of `requirements.md` in this folder, a made-up requirements set for an invented product. It was
written by an AI assistant (Claude) at the participant's direction. The requirements were written by a separate
assistant, and this review was made without seeing which of them it meant to be defective.

Every finding is about words on the page. None is about whoever wrote them.

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
3. **Incomplete.** Is a fact that a tester needs simply absent from the text? The fact in question is the one
   the finding's own question asks for. Absent means that no word in the requirement speaks of it at all. If a
   word does speak of it, however loosely, the answer is no.
4. **Vague.** Are the facts all present, with a word or phrase that has more than one reasonable reading? This
   is where a point belongs when the text does speak of it, in words that leave the answer open.

The order runs from the most serious to the least. A contradiction cannot be mended by making one requirement
clearer. An untestable requirement cannot be tested on any reading. An incomplete one needs a fact added. A
vague one needs a word pinned down.

These definitions were tested by independent readers who were given the findings with the types taken out.
After the first, a sentence was added under contradictory, untestable, incomplete and vague, writing down
readings that had been applied and not stated. After the second, the sentence "The fact in question is the one
the finding's own question asks for" was added under incomplete, with the rule for a finding that raises two
points. A further rule, tried after the third and fourth, made matters worse and was taken out again. The
definitions above are the ones the third and fifth readers were given.

What the definitions still leave to judgment: what counts as a "reasonable" reading. F-02 is a contradiction
only if "complete booking history" cannot reasonably mean "complete as far as records still exist". F-09 is
vague and not contradictory only if "unavailable" can reasonably mean "shown as booked". A reader who judges
either differently will give that finding another type. The definitions also do not say whether a word that
only implies a fact speaks of it: "work correctly" for which functions must work, in F-06, and "accumulates"
for a counting period, in F-07. Where one finding raises two points, as those two do, it takes the type of the
first question that either point answers yes, so its type can turn on how its question is worded.

The fifth reader, given this file with the types taken out and told to assume nothing, gave all nine findings
the types below: six from the written words alone, and F-02, F-06 and F-07 by the judgments just named.

Each finding gives the words that cause it, quoted exactly; what a tester could not decide; what goes wrong if
the question is never answered; and the question. A finding asks. It does not say what the requirement ought
to say, because that is for whoever owns the requirement to decide. Where a second type was considered, the
finding says which and why the order chose the first.

"Effort to make testable" is small when one number or one name answers the question, medium when a rule has to
be decided, and large when requirements have to be reconciled or the requirement thought out again.

## F-01
- Requirement: REQ-04 and REQ-12
- Type: contradictory
- Words in REQ-04: "at any time before the booking's start time"
- Words in REQ-12: "shall not accept a cancellation from a member less than two hours before the booking's start time"
- A tester could not decide: whether a member's cancellation 90 minutes before the start is to be accepted or refused. REQ-04 says accepted and REQ-12 says refused.
- If unanswered: whichever is built, one of the two requirements fails its test, and members are either let out of a rule that was meant to hold or held to one that was not.
- Question: In the two hours before a booking starts, may the member cancel it or not?
- Effort to make testable: large. Two requirements have to be reconciled, and the answer is a decision about the library's rules.

## F-02
- Requirement: REQ-14 and NFR-04
- Type: contradictory
- Words in REQ-14: "complete booking history for the previous 24 months"
- Words in NFR-04: "permanently deleted 12 months after the date of the booking"
- A tester could not decide: what a staff user should see for a booking made 18 months ago. REQ-14 says it is listed. NFR-04 says it no longer exists.
- If unanswered: either records are kept a year longer than the constraint allows, or staff are shown a history that is called complete and is missing its older half.
- Question: For how long are booking records kept, and is that the period a staff user's history must cover?
- Effort to make testable: large. Two requirements in two documents have to be reconciled.

## F-03
- Requirement: REQ-11
- Type: untestable
- Words: "genuinely intend to use them"
- A tester could not decide: what to observe. A system can see what a member does. No test can observe what a member intends at the moment of booking.
- If unanswered: the requirement can never be shown to be met or not met, so nothing is built for it, or something is built that nobody can check.
- Question: What that the system can observe would count as a member not intending to use a room, and what is the system to do when it sees it?
- Also considered: vague, since "genuinely" is loose. The order puts untestable first: no reading of the words gives something to observe.
- Effort to make testable: large. The requirement states a wish, and the behaviour that would serve it has yet to be chosen.

## F-04
- Requirement: NFR-05
- Type: untestable
- Words: "No fault in the system shall ever"
- A tester could not decide: when to stop. A test can show that one fault loses a booking. No set of tests can show that no fault ever does.
- If unanswered: the requirement is passed on the strength of the faults somebody thought to try, and reads as a promise about all of them.
- Question: Which faults must a confirmed booking survive, and how is its survival to be checked after each?
- Also considered: contradictory with NFR-06, since a restore from a backup up to 24 hours old could lose bookings. Not chosen: nothing stops a system keeping bookings safe by other means as well, so both can be satisfied.
- Effort to make testable: medium. A list of faults and a check have to be decided.

## F-05
- Requirement: REQ-06
- Type: vague
- Words: "shortly before"
- A tester could not decide: when to look for the email. Ten minutes before the start and the evening before are both shortly before.
- If unanswered: the reminder arrives too late to act on, or so early that it is forgotten, and either passes.
- Question: How long before a booking's start time is the reminder email to be sent?
- Also considered: incomplete. Not chosen: the timing is stated, by a phrase with many readings. The glossary defines "promptly" and does not define this.
- Effort to make testable: small. One duration answers it.

## F-06
- Requirement: NFR-03
- Type: vague
- Words: "recent versions of popular desktop and mobile browsers"
- Words: "work correctly"
- A tester could not decide: which browsers and which versions to test in, and what would count as working in each.
- If unanswered: the site is tested in whatever browsers the tester has, and a member with another one finds it broken after release.
- Question: Which browsers and which versions must the website support, and which of its functions must work in each?
- Also considered: incomplete. Not chosen: browsers, versions and correctness are all spoken of, each by a word with more than one reading.
- Effort to make testable: medium. A list of browsers and versions is small. Deciding what "work correctly" covers is a rule.

## F-07
- Requirement: REQ-08
- Type: incomplete
- Words: "accumulates three no-shows"
- A tester could not decide: over what period the three are counted, and whether or when the member can book again. Three in a month and three in ten years both accumulate.
- If unanswered: a member is barred for good by three missed bookings years apart, or the count quietly drops as old records are deleted under NFR-04, and nobody chose either.
- Question: Over what period are no-shows counted, and how does a member who has been prevented from booking become able to book again?
- Effort to make testable: medium. A counting period and a way back have to be decided.

## F-08
- Requirement: REQ-13
- Type: incomplete
- Words: "shall refuse new bookings for them"
- A tester could not decide: what should happen to a booking that already exists on a date when the room is marked out of service. The text covers new bookings only.
- If unanswered: a member arrives for a booking in a room that is closed, or their booking disappears and nobody tells them.
- Question: When a room is marked out of service for dates on which it already has bookings, what is to happen to those bookings and to the members who hold them?
- Effort to make testable: medium. A rule for existing bookings has to be decided.

## F-09
- Requirement: REQ-13
- Type: vague
- Words: "as unavailable"
- A tester could not decide: what marking to expect on an out-of-service slot. REQ-02 marks every slot as either "available" or "booked". Here "unavailable" could be a third marking, or could mean shown as booked.
- If unanswered: a third marking is built and the test of REQ-02 fails, or closed rooms are shown as booked and look as if they were in demand.
- Question: Is an out-of-service slot shown with a marking of its own, or as "booked", and if it has its own, is that a third marking beside the two in REQ-02?
- Also considered: contradictory with REQ-02. Not chosen: a system that shows such a slot as "booked" meets REQ-02 to the letter and meets REQ-13 on one reading, so it is not the case that no system could satisfy both.
- Effort to make testable: small. One answer settles the marking.

## Unflagged

Requirements left alone, each with the reason two testers would write the same test.

- REQ-01: the credentials, the count of five consecutive failures and the 15-minute rejection are all stated, so the sixth attempt and the first after 15 minutes each have one expected result.
- REQ-02: what is shown for each room and the two markings a slot can have are stated, and "any date on which bookings are accepted" is fixed by REQ-05.
- REQ-03: the limits of one to four consecutive slots, one room and one day are stated, and "slot" and "opening hours" are both defined in the glossary.
- REQ-05: the first and last accepted dates and the exact message for a later date are stated, so day 14 and day 15 each have one expected result.
- REQ-07: the five things on the confirmation page are listed, and "promptly" is defined in the glossary as within 60 seconds.
- REQ-09: the way to check in and both ends of the period in which it is accepted are stated in minutes.
- REQ-10: the trigger is the glossary's "no-show", "promptly" is defined, and which slots become available is stated.
- NFR-01: the number of members, where the time is measured, the limit, the share of requests and the length of the run are all stated as numbers. A finding on how often each member makes a request was raised and withdrawn, as set out below.
- NFR-02: how a PIN is stored and the three places it must never appear are stated, and each can be inspected.
- NFR-06: the backup interval, how often the restore is tested and its time limit are all stated as numbers.

## Raised and withdrawn

Not findings. Two findings were raised in the review and later taken out. They are kept here so that a reader
can see what was considered.

- **F-10, against REQ-05, withdrawn on the second look.** It quoted "from the current day" and said the text
  does not say whether a slot earlier today, already past, can be booked. The quoted words are exact and two
  testers would write the same test for them. What is missing is a rule the set does not have, which is noted
  under "Gaps in the set".
- **F-11, against NFR-01, withdrawn after review.** It quoted "making requests at the same time" and asked how
  often each of the 50 members makes a request, since the same system could pass at one rate and fail at
  another. It was typed incomplete. Two independent readers in turn could not settle whether it was incomplete
  or vague, because the definitions do not say whether a phrase about the load in general speaks of how often a
  request is made. A rule added to settle it unsettled another finding. The assistant that wrote the
  requirements had meant NFR-01 as sound. A finding whose type cannot be reproduced does not meet this review's
  own standard, so it is withdrawn. The concern itself is not withdrawn: a person planning a load test from
  NFR-01 would still have to choose a request rate.

## Gaps in the set

Not findings. A finding is a defect in a requirement's words. These are things no requirement says, noted
because a reader of the set would want to know.

- No requirement says whether a slot earlier on the current day, already past, can be booked.
- No requirement says how long a backup is kept. If backups outlive NFR-04's 12 months, deleted booking records
  could be restored from one.
