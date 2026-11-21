# Second look

Written by the reviewer after going through the eleven first-pass findings again, one at a time, and before the
author's answer key was opened. Each finding was held to three tests:

1. Do the quoted words cause the problem, or are they only near it?
2. Would two testers write different tests for this requirement as it stands?
3. What goes wrong if the question is never answered?

## One finding withdrawn: F-10, on REQ-05

Raised as: incomplete, quoting "from the current day", because the text speaks of dates and does not say
whether a slot earlier today, already past, can be booked.

Why it does not survive:

- **The quoted words do not cause it.** "From the current day" is exact. It says which dates are accepted, and
  it is right. The finding blamed words that are fine.
- **Two testers would write the same test for REQ-05.** Today is accepted. Fourteen days ahead is accepted.
  Fifteen is rejected, with the message given. That is the whole of what REQ-05 claims, and all of it can be
  tested.
- **What is missing is another requirement, not part of this one.** Whether a past slot can be booked is a rule
  the set does not have. That is a gap in the set. A finding, as the quest defines it, is a defect in a
  requirement's words.

So F-10 is withdrawn, and REQ-05 is listed as unflagged. The gap is real and is kept, as a note at the end of
the findings file under "Gaps in the set", where it is not counted as a finding.

## One finding kept after doubt: F-11, on NFR-01

It was close. NFR-01 is far better than most performance requirements: it gives the number of members, where
the time is measured, the limit, the share of requests and the length of the run. Against that, "making
requests at the same time" does not say how often. Fifty members who each ask once a minute and fifty who ask
without pause are very different loads, and the same system could pass one and fail the other. Two testers
would not build the same test, and the pass or fail would depend on which of them ran it. Kept, as the finding
most likely to be called nitpicking.

## One finding kept as it was: F-09, on REQ-13

Considered again as a contradiction with REQ-02. Left as vague. A system that shows an out-of-service slot as
"booked" satisfies REQ-02 to the letter and satisfies REQ-13 on one reading of "unavailable". By the agreed
definition a contradiction needs that no system could satisfy both.

## Nothing added

No new finding was raised on the second look. The eight requirements left alone on the first pass were read
again against the question "would two testers write the same test?" and all eight stayed unflagged.

Ten findings remain, on eleven requirements. Nine requirements are unflagged.
