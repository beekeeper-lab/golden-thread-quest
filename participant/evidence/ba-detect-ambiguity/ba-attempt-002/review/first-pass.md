# First pass

Written by the reviewer after one read of `participant/context/ambiguity/requirements.md`, before any second
look and before the author's answer key was opened. The definitions and their order had been agreed with the
participant before the requirements were seen. This file is kept as it was written, so that what changed
afterwards can be seen.

Eleven findings were raised.

| # | Requirement | Type | Words | Why, in a line |
|---|---|---|---|---|
| F-01 | REQ-04 and REQ-12 | contradictory | "at any time before the booking's start time" against "shall not accept a cancellation from a member less than two hours before" | One lets a member cancel up to the start. The other forbids it in the last two hours. |
| F-02 | REQ-14 and NFR-04 | contradictory | "complete booking history for the previous 24 months" against "permanently deleted 12 months after the date of the booking" | A history cannot be complete for 24 months if its records are gone after 12. |
| F-03 | REQ-11 | untestable | "genuinely intend to use them" | No observation shows what a member intends. |
| F-04 | NFR-05 | untestable | "No fault in the system shall ever" | A test can show a loss. None can show that no fault ever causes one. |
| F-05 | REQ-06 | vague | "shortly before" | Five minutes and a day are both "shortly". The glossary defines "promptly" and not this. |
| F-06 | NFR-03 | vague | "recent versions of popular desktop and mobile browsers", "work correctly" | Which browsers, how recent, and what counts as working. |
| F-07 | REQ-08 | incomplete | "accumulates three no-shows" | Over what period, and for how long is the member prevented. |
| F-08 | REQ-13 | incomplete | "shall refuse new bookings for them" | Nothing is said about bookings that already exist on those dates. |
| F-09 | REQ-13 | vague | "as unavailable" | REQ-02 allows two markings, "available" and "booked". Is "unavailable" a third, or does it mean shown as booked. |
| F-10 | REQ-05 | incomplete | "from the current day" | It speaks of dates only. Can a slot earlier today, already past, be booked. |
| F-11 | NFR-01 | incomplete | "making requests at the same time" | How often each of the 50 makes a request is not stated, and the result depends on it. |

Requirements left alone on this pass: REQ-01, REQ-02, REQ-03, REQ-07, REQ-09, REQ-10, NFR-02, NFR-06.

Doubts noted at the time:

- F-09. Read strictly, REQ-02 and REQ-13 contradict each other. Read loosely, a system could show an
  out-of-service slot as "booked" and satisfy both. The agreed definition of a contradiction is that no system
  could satisfy both, so it was raised as vague, with the contradiction noted.
- F-10 and F-11. Both felt close to the line when raised.
- NFR-04 beside NFR-06. Backups could hold records that NFR-04 says are not retrievable. Not raised: no
  requirement says how long a backup is kept, so nothing in the text conflicts.
