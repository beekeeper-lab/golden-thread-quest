# The fourth independent read

The first hand-in was sent back by the reviewer because F-11's type could not be reproduced. The reviewer
suggested a rule for when a nearby phrase counts as speaking of a fact: that the fact is present only if a word
names the quantity the finding's question asks for. That rule was written into the definition of incomplete,
and a fourth assistant, starting fresh, was given the requirements and the findings with those definitions and
with each finding's Type, Also considered and Effort lines taken out (`blinded-findings-4.md` in this folder),
with the same instruction to apply the definitions strictly and assume nothing. Its table and remarks are copied
here unchanged below the line.

What came of it: F-11 was given the review's type, by an assumption. F-06, which every earlier reader had typed
as the review did, was left unsettled. The rule moved the difficulty from one finding to another. It was taken
out again, and F-11 was withdrawn, as had been agreed with the participant beforehand.

---

Eight of the ten findings get a type from the written definitions; F-06 is not settled, and F-02 and F-11 needed an assumption from me. I read only the two files named and edited nothing.

| Finding | Requirement(s) | Type | Deciding sentence | Settled or assumed |
| --- | --- | --- | --- | --- |
| F-01 | REQ-04, REQ-12 | contradictory | Q1 was the first yes, decided by "Is there another requirement such that no system could satisfy both? The clash must hold on every reasonable reading of both." "At any time before the booking's start time" and "shall not accept ... less than two hours before" clash at 90 minutes on every reading. | Settled |
| F-02 | REQ-14, NFR-04 | contradictory | Q1 was the first yes, decided by the same sentence. A booking 18 months old must be listed under REQ-14 and "shall not be retrievable by any user" under NFR-04. | Assumed: that reading "complete booking history" as "complete as far as records still exist" is not a reasonable reading. The definitions do not say what makes a reading reasonable. If that reading is allowed, Q1 is no and the finding falls to vague. |
| F-03 | REQ-11 | untestable | Q2 was the first yes, decided by "Is there no observation at all that could show the requirement is met, however its words are read?" Intention cannot be observed. | Settled |
| F-04 | NFR-05 | untestable | Q2 was the first yes, decided by "A requirement that could be shown to be broken and could never be shown to be met counts as untestable." | Settled |
| F-05 | REQ-06 | vague | Q4 was the first yes. Q3 was no under "It counts as present only if a word in the requirement names the quantity or thing that the question asks for, however loosely", because "shortly before" names the lead time loosely. | Settled |
| F-06 | NFR-03 | not settled: incomplete or vague (leaning vague) | The first point (which browsers and versions) is named loosely by "recent versions of popular desktop and mobile browsers", so it reaches Q4. The second point (which functions must work in each) depends on whether "the website shall work correctly" names the functions or only "something near it". Under "Where one finding raises two points, it takes the type of the first question that either point answers yes", an absent second point makes the whole finding incomplete. | Not settled. The written words do not say whether a word naming the whole (the website) names its parts (its functions). |
| F-07 | REQ-08 | incomplete | Q3 was the first yes, decided by "If no word names it, it is absent and the answer is yes." No word names how a barred member becomes able to book again, and the two-point rule then gives incomplete whatever is decided about the counting period. | Settled. The counting-period point alone would be less clear, since "accumulates" could be the thing named loosely or something near it, but the second point decides the finding. |
| F-08 | REQ-13 | incomplete | Q3 was the first yes, decided by "A word that names something near it, and not the thing itself, does not make it present." "New bookings" is near existing bookings but does not name them. | Settled |
| F-09 | REQ-13 (with REQ-02) | vague | Q4 was the first yes. Q1 was no under "If one reasonable reading lets a system satisfy both, the answer is no", because the finding itself gives such a reading ("unavailable" shown as "booked"). Q3 was no because "unavailable" names the marking asked for. | Settled, taking the finding's own statement that "shown as booked" is a possible reading. |
| F-11 | NFR-01 | incomplete | Q3 was the first yes, decided by "A word that names something near it, and not the thing itself, does not make it present." The question asks how often each member requests; "at the same time" names simultaneity, not frequency. | Assumed: that "making requests at the same time" names something near the request rate, not the rate itself "however loosely". If it counts as a loose naming of the load pattern, the type is vague. |

Remaining problems in the definitions:

1. "However loosely" and "names something near it, and not the thing itself" pull against each other with no written test for telling them apart. F-11, the second point of F-06 and the period point of F-07 all sit on that line.
2. Q1 depends on "reasonable reading", which is not defined. F-02 turns on whether "complete" may be read as "complete as far as records are retained".
3. The definitions do not say whether a word that names a whole (the website) names its parts (its functions).
4. The two-point rule lets a small absent sub-point outrank the main vague point, so a finding's type can depend on how its question happens to be worded (F-06, F-07). That may not be intended.
5. Q2's "however its words are read" is very strict. F-03 passes only because every reading of "genuinely intend" is a mental state; a reviewer who accepts a behavioural proxy as a reading would answer no and land on vague.
