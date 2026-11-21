# The second independent read

After the first independent reader reported that five of its ten types were close calls, three clarifications
were written into the definitions, one as a second sentence under each of three types. A second assistant,
starting fresh, was then given the requirements and the findings with the clarified definitions and with each
finding's Type, Also considered and Effort lines taken out (`blinded-findings-2.md` in this folder), and nothing
else. It was told to apply the definitions strictly as written, to supply no conventions of its own, and to say
"not settled" where the written words did not decide a case. Its table and remarks are copied here unchanged
below the line.

---

| Finding | Requirement(s) | Type | Deciding sentence | Settled or assumed |
| --- | --- | --- | --- | --- |
| F-01 | REQ-04, REQ-12 | contradictory | Q1 was the first yes: "Is there another requirement such that no system could satisfy both?" REQ-04 says "at any time before" and REQ-12 says "shall not accept" inside two hours, which leaves no reading that satisfies both. | settled |
| F-02 | REQ-14, NFR-04 | contradictory | Q1 was the first yes, decided by "The clash must hold on every reasonable reading of both": an 18-month-old booking must be listed and must also be permanently deleted. | assumed: that reading "complete booking history" as "complete as far as records still exist" is not reasonable. If that reading is allowed, Q1 is no and the finding falls through to vague. |
| F-03 | REQ-11 | untestable | Q2 was the first yes (Q1 no, no clashing requirement): "Is there no observation at all that could show the requirement is met, however its words are read?" Intention cannot be observed. | settled (a proxy such as check-in would replace the words, not read them) |
| F-04 | NFR-05 | untestable | Q2 was the first yes: "A requirement that could be shown to be broken and could never be shown to be met counts as untestable." | settled |
| F-05 | REQ-06 | vague | Q4 was the first yes; Q3 was no by "If a word does speak of it, however loosely, the answer is no", since "shortly before" speaks of the lead time. | settled |
| F-06 | NFR-03 | vague | Q4 was the first yes; Q2 was no because once browsers are chosen the site can be observed, and Q3 was no by the "however loosely" sentence ("recent", "popular" and "work correctly" each speak of the missing point). | settled |
| F-07 | REQ-08 | incomplete | Q3 was the first yes: "Absent means that no word in the requirement speaks of it at all." No word speaks of how a prevented member becomes able to book again. | assumed: that a finding raising two points takes the type of the earliest question either point answers yes. The reinstatement point is plainly absent. The counting-period point alone is not settled between incomplete and vague, because it depends on whether "accumulates" speaks of a period. |
| F-08 | REQ-13 | incomplete | Q3 was the first yes: "Is a fact that a tester needs simply absent from the text?" The text speaks only of "new bookings" and no word speaks of existing ones. | settled |
| F-09 | REQ-13 (with REQ-02) | vague | Q4 was the first yes; Q1 was no by "If one reasonable reading lets a system satisfy both, the answer is no" (reading "unavailable" as shown "booked" satisfies REQ-02), and Q3 was no because "as unavailable" does speak of the marking. | assumed: that "unavailable" meaning "shown as booked" is a reasonable reading. If it is not, Q1 is yes and the type is contradictory. |
| F-11 | NFR-01 | not settled: incomplete or vague | Q1 and Q2 are no. Q3 turns on "If a word does speak of it, however loosely, the answer is no", and the text does not settle whether "making requests at the same time" speaks of request frequency or only of concurrency. | not settled. If the phrase counts as speaking loosely of the load, it is vague; if frequency is a separate fact no word mentions, it is incomplete. |

What is still unclear in the definitions:

- **"Speaks of it" (Q3).** The test has no rule for how to name "it": described broadly (the load, the counting) a nearby word nearly always speaks of it, and described narrowly (requests per minute, the counting period) nothing does. That is why F-11 and half of F-07 cannot be settled.
- **"Reasonable reading" (Q1 and Q4).** The word "reasonable" is undefined and carries the whole decision in F-02 and F-09; a reviewer who is generous about readings turns F-02 into vague, and a strict one turns F-09 into contradictory.
- **Findings with more than one point.** The definitions say a finding has exactly one type but not what to do when one finding raises two points that would type differently (F-07, and to a lesser degree F-06).
- **"However its words are read" (Q2).** It does not say whether a proxy reading counts as a reading, for example "intends to use" read as "checks in"; I took it that it does not, but a reviewer who allows it would move F-03 to vague.
