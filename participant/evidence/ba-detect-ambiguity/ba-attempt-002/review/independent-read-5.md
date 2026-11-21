# The fifth independent read

After the fourth read, the rule the reviewer had suggested was taken out of the definitions again and F-11 was
withdrawn. A fifth assistant, starting fresh, was given the requirements and the findings file as it now
stands, nine findings, with each finding's Type, Also considered and Effort lines taken out
(`blinded-findings-5.md` in this folder), with the same instruction to apply the definitions strictly and
assume nothing. The definitions it was given are word for word those the third reader had. Its table and
remarks are copied here unchanged below the line.

---

I read only the two named files and edited nothing. Six of the nine findings are settled by the written definitions alone; three (F-02, F-06, F-07) needed an assumption, which I name.

| Finding | Requirement(s) | Type | Deciding sentence | Settled or assumed |
| --- | --- | --- | --- | --- |
| F-01 | REQ-04, REQ-12 | contradictory | Q1 was the first yes: "Is there another requirement such that no system could satisfy both?" A member cancellation 90 minutes before start must be both accepted and refused. | Settled |
| F-02 | REQ-14, NFR-04 | contradictory | Q1 was the first yes, decided by "The clash must hold on every reasonable reading of both." A booking 18 months old must be listed and must not be retrievable. | Assumed: that reading "complete booking history" as "whatever records still exist" is not a reasonable reading. If it is reasonable, Q1 is no and the finding falls to vague (Q3 is no because "12 months" speaks of the retention period). |
| F-03 | REQ-11 | untestable | Q2 was the first yes: "Is there no observation at all that could show the requirement is met, however its words are read?" Intent cannot be observed on any reading. | Settled |
| F-04 | NFR-05 | untestable | Q2 was the first yes, decided by "A requirement that could be shown to be broken and could never be shown to be met counts as untestable." | Settled |
| F-05 | REQ-06 | vague | Q4 was the first yes; Q3 was ruled out by "If a word does speak of it, however loosely, the answer is no." "Shortly" speaks of the lead time. | Settled |
| F-06 | NFR-03 | vague | Q4 was the first yes; Q3 was ruled out by the same "however loosely" sentence. "Recent", "popular" and "work correctly" speak of each fact asked for. | Assumed (minor): that "the website shall work correctly" counts as speaking of "which of its functions must work in each". If it does not, that point is absent and the finding is incomplete. |
| F-07 | REQ-08 | incomplete | Q3 was the first yes, decided by "Absent means that no word in the requirement speaks of it at all", applied to the second point (how a member becomes able to book again), then "it takes the type of the first question that either point answers yes." | Assumed: that neither "prevented" nor the message word "suspended" speaks of reinstatement. The first point alone (counting period) is not settled between incomplete and vague, because it is unclear whether "accumulates" speaks of a period. |
| F-08 | REQ-13 | incomplete | Q3 was the first yes: "Absent means that no word in the requirement speaks of it at all." The text speaks of slots and new bookings, never of existing bookings or their holders. | Settled |
| F-09 | REQ-13 (with REQ-02) | vague | Q4 was the first yes; Q1 was ruled out by "If one reasonable reading lets a system satisfy both, the answer is no" (the finding itself gives one: "unavailable" shown as "booked"), and Q3 by "however loosely". | Settled |

Still unclear in the definitions:

1. "Reasonable reading" in Q1 is not defined, and it alone decides whether F-02 is contradictory or vague.
2. "Speaks of it, however loosely" in Q3 does not say whether a word that only implies a fact speaks of it ("accumulates" for a period, "suspended" for reinstatement, "work correctly" for which functions), which is the whole of the doubt in F-06 and F-07.
3. The two-point rule gives F-07 its type from its second point only, so the type says nothing true about the first point; splitting such findings would classify more reproducibly than the rule does.
4. Q3 says "no word in the requirement", so it is unwritten whether a word in another requirement or the glossary can make a fact present (F-07's own text points to NFR-04 for the period).
