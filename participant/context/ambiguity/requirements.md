# RoomSlot: study-room booking requirements

This is a made-up requirements set for an invented product. RoomSlot is an imaginary website and in-library kiosk through which members of a small public library book the library's study rooms. The library, the product and every detail below are fictional.

## Glossary

| Term | Meaning |
| --- | --- |
| Member | A person who holds a library card whose status is "active". |
| Staff user | A person signed in with an account that carries the staff role. |
| Slot | A 30-minute period that begins on the hour or on the half-hour. |
| Opening hours | 09:00 to 20:00, Monday to Saturday. The library is closed on Sunday. |
| Promptly | Within 60 seconds of the triggering event. |
| No-show | A booking for which no check-in has been recorded by 15 minutes after its start time. |

## Document A: Functional requirements

**REQ-01** The system shall allow a member to sign in with their library card number and 6-digit PIN. After five consecutive failed sign-in attempts for a card number, the system shall reject all further sign-in attempts for that card number for 15 minutes.

**REQ-02** For any date on which bookings are accepted, the system shall display each study room with its seating capacity and shall mark each slot of that room as either "available" or "booked".

**REQ-03** A booking shall consist of between one and four consecutive slots in a single room on a single day. Every slot in a booking shall fall wholly within opening hours.

**REQ-04** A member shall be able to cancel any of their own bookings at any time before the booking's start time. On cancellation the system shall show the booking's slots as available.

**REQ-05** The system shall accept bookings for dates from the current day up to and including 14 days ahead. It shall reject a booking for any later date with the message "Bookings open 14 days in advance".

**REQ-06** The system shall send a reminder email to the member shortly before each of their bookings begins. The email shall state the room, the date, the start time and the booking reference.

**REQ-07** On creating a booking, the system shall promptly display a confirmation page showing the room, the date, the start time, the end time and an 8-character booking reference.

**REQ-08** A member who accumulates three no-shows shall be prevented from making new bookings. The system shall display the message "Booking suspended" when such a member attempts to book.

**REQ-09** A member shall check in by entering the booking reference at the library kiosk. The kiosk shall accept a check-in from 10 minutes before the booking's start time until 15 minutes after it, and shall reject a check-in outside that period.

**REQ-10** When a booking becomes a no-show, the system shall promptly release it and show any of its slots that have not yet ended as available.

**REQ-11** The system shall ensure that study rooms are booked only by members who genuinely intend to use them.

**REQ-12** The system shall not accept a cancellation from a member less than two hours before the booking's start time. Within that period a booking shall be cancelled only by a staff user.

**REQ-13** A staff user shall be able to mark a room as out of service for a range of dates. The system shall show that room's slots on those dates as unavailable and shall refuse new bookings for them.

**REQ-14** A staff user shall be able to view any member's complete booking history for the previous 24 months, listing for each booking the room, the date, the start time and whether it was attended, cancelled or a no-show.

## Document B: Service levels and constraints

**NFR-01** With 50 members signed in and making requests at the same time, the server shall return the complete availability page within 2 seconds for at least 95% of requests over a 30-minute test run.

**NFR-02** The system shall store each PIN only as a salted hash. No PIN shall appear in plain text in the database, in log files or in any email.

**NFR-03** The website shall work correctly in recent versions of popular desktop and mobile browsers.

**NFR-04** Booking records shall be permanently deleted 12 months after the date of the booking and shall not be retrievable by any user after that.

**NFR-05** No fault in the system shall ever cause a confirmed booking to be lost.

**NFR-06** The booking database shall be backed up once every 24 hours. In a quarterly test, a restore from the most recent backup shall be completed within 4 hours.
