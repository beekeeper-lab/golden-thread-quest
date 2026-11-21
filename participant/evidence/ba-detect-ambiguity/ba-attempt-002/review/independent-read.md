# The independent read

A third assistant, starting fresh, was given two files only: the requirements, and the findings with each
finding's type, its "also considered" line and its effort line taken out (`blinded-findings.md` in this folder).
It was asked to give each finding a type from the written definitions, to say how close the choice was, and to
say candidly whether it would have raised the finding at all. It could not see the reviewer's types or the
author's answer key. Its table and its remarks are copied here unchanged below the line.

---

| Finding | Requirement(s) | My type | First question answered yes, and why | Clear or close (other type weighed) | Real defect? |
| --- | --- | --- | --- | --- | --- |
| F-01 | REQ-04, REQ-12 | contradictory | Q1: a member cancellation 90 minutes before start must be both accepted and refused, so no system satisfies both. | Clear | Yes. Two testers would write opposite expected results. |
| F-02 | REQ-14, NFR-04 | contradictory | Q1: a "complete" 24-month history cannot be shown if records are permanently deleted at 12 months. | Mostly clear (vague: "complete" could mean "all that still exists", which would dissolve the conflict) | Yes. An 18-month-old booking has two opposite expected results. |
| F-03 | REQ-11 | untestable | Q2: intent is not observable on any reading, and no other requirement makes Q1 apply. | Clear (briefly vague, but no reading gives an observation) | Yes. |
| F-04 | NFR-05 | untestable | Q2: "no fault ... ever" is a universal negative, so no finite set of observations can show it is met. | Close (incomplete: the list of faults to survive is a missing fact) | Yes, though one fault can show it is not met, so it is only untestable on the pass side. |
| F-05 | REQ-06 | vague | Q4: "shortly" is present and covers the timing but has many reasonable readings; I did not count the lead time as "simply absent". | Close (incomplete: the lead time is a missing number) | Yes. The glossary pins down "promptly" but not "shortly". |
| F-06 | NFR-03 | vague | Q4: "recent", "popular" and "work correctly" each have several reasonable readings, and it is testable once a reading is picked. | Close (incomplete: the browser and version list is absent; untestable weighed briefly) | Yes. |
| F-07 | REQ-08 | incomplete | Q3: the counting period and any way back to booking are not addressed by any word in the text. | Fairly clear (vague: "accumulates" could be read as lifetime or rolling) | Yes, but modest. Most testers would default to a lifetime count and write the same basic test. The defect bites mainly through NFR-04 deletion and the missing reinstatement rule, which is closer to a missing requirement than an ambiguous one. |
| F-08 | REQ-13 | incomplete | Q3: the fate of existing bookings on out-of-service dates is not stated anywhere. | Clear | Yes as a gap. For the behaviour actually written (new bookings refused) two testers would write the same test, so it is a missing case, not a disputed one. |
| F-09 | REQ-13 (with REQ-02) | vague | Q4: "unavailable" reads either as a third marking or as shown "booked"; Q1 is no because on the second reading both requirements can be met. | Close (contradictory: on the third-marking reading REQ-02's "either available or booked" is breached) | Yes. Testers would expect different labels. |
| F-11 | NFR-01 | incomplete | Q3: the request rate per member during the 30-minute run is not given at all. | Close (vague: "at the same time" could mean 50 simultaneous requests or 50 concurrent sessions) | Yes. The load is not reproducible between testers. |

**What was hard to apply in the definitions**

- **Incomplete versus vague.** This boundary is the weakest. Almost any vague phrase ("shortly before", "recent versions") can be restated as an absent fact. Because incomplete is asked before vague, a strict reader would type F-05 and F-06 as incomplete. I avoided that only by reading "simply absent" as "no word in the text addresses it at all", which the definitions do not say.
- **Contradictory.** "No system could satisfy both" does not say under which reading. F-09 is contradictory on one reading and merely vague on another. I took Q1 as yes only if the conflict holds on every reasonable reading; the opposite convention would flip F-09.
- **Untestable.** "No observation could show the requirement is met" fits F-04 only if one-sided testability (it can be falsified but never confirmed) counts. The definition should say so.
- **Gaps versus the gate question.** The two-testers question does not fit pure gaps such as F-08 and the second half of F-07. Testers would agree on the test for what is written, and the defect is the case nobody wrote.
