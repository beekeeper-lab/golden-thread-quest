# Findings: Tixly checkout requirements

Review of `participant/context/ambiguity/requirements.md` (12 requirements, CHK-01 to CHK-12).
Reviewed 10-26-2026 by Tom Carter, as a blind review: the requirements were drafted for the
exercise with an answer key sealed before the review, and compared only afterwards. Revised the
same day after the reviewer's questions: two findings dropped (CHK-06, CHK-09) and two split so each
finding holds one gap (F-04 into F-04, F-12, F-13; F-09 into F-09, F-14). Finding numbers were kept,
so earlier references still point to the same finding.

## The four defect types

Each finding names exactly one type and one gap. A requirement with two problems has two findings,
even when the same words cause both.

| Type | Meaning | Quick test |
|---|---|---|
| Vague | It names something measurable but gives no measure. | Adding a number or limit would fix it; two testers would pick different numbers. |
| Incomplete | It leaves out a case or behaviour a tester needs. | The happy path is testable, but a "what if…?" has no expected result. |
| Contradictory | Two requirements can't both be true. | Passing one means failing the other. Always cites both. |
| Untestable | No test could ever pass or fail it. | No expected result can be written, and no number would fix that. |

Tie-breaker when the same words seem to fit two types: if a number would fix it, vague; if no
number could, untestable; if a whole situation is missing, incomplete.

Findings ask the question that would resolve them. They never rewrite the requirement; deciding
the answer is the author's call.

## Findings

### F-01
- **Requirement:** CHK-02
- **Type:** Vague
- **Words in CHK-02:** "quickly"
- **A tester couldn't decide:** how many seconds counts as a pass, so two testers would pass and fail different load times.
- **Question:** How many seconds may the seat map take to load?

### F-02
- **Requirement:** CHK-02
- **Type:** Incomplete
- **Words in CHK-02:** "must load"
- **A tester couldn't decide:** the conditions to test under, or where the timing starts and stops.
- **Question:** Under what conditions is the load time measured (connection, device, size of the venue), and from what moment to what moment?

### F-03
- **Requirement:** CHK-04
- **Type:** Incomplete
- **Words in CHK-04:** "The gift card balance is deducted from the order total."
- **A tester couldn't decide:** whether using part of a card is allowed, or what the card should show after an order smaller than its balance.
- **Question:** Can the buyer use only part of the gift card balance, and if so, how?
- **Question:** When the gift card is worth more than the order, what happens to the remaining balance?

### F-04
- **Requirement:** CHK-05
- **Type:** Incomplete
- **Words in CHK-05:** "Refunds are available"
- **A tester couldn't decide:** where the money should go, so a refund back to the card and a refund as Tixly credit would both look right.
- **Question:** How is the refund given: back to the original payment, as Tixly credit, or another way?

### F-12
- **Requirement:** CHK-05
- **Type:** Incomplete
- **Words in CHK-05:** "Refunds are available"
- **A tester couldn't decide:** whether a refund request with no reason given should be accepted or blocked.
- **Question:** Does the buyer have to give a reason for the refund?

### F-13
- **Requirement:** CHK-05
- **Type:** Incomplete
- **Words in CHK-05:** "Refunds are available"
- **A tester couldn't decide:** whether any refund requested in time may still be refused, so there is no expected result for a denial.
- **Question:** Are there reasons a refund requested in time would be denied?

### F-06
- **Requirement:** CHK-07
- **Type:** Untestable
- **Words in CHK-07:** "feel trustworthy"
- **A tester couldn't decide:** anything to check: a feeling has no expected result, and no number could decide it.
- **Question:** What would a tester check to decide whether checkout is trustworthy for a first-time buyer?

### F-07
- **Requirement:** CHK-05, CHK-08
- **Type:** Contradictory
- **Words in CHK-05:** "up to 48 hours before the event starts"
- **Words in CHK-08:** "at any time until the venue doors open"
- **A tester couldn't decide:** the expected result for a cancellation 24 hours before the event, while the venue doors are not yet open: CHK-08 gives a full refund, CHK-05 gives none.
- **Question:** Which refund deadline applies: 48 hours before the event starts, or until the venue doors open?

### F-09
- **Requirement:** CHK-10
- **Type:** Incomplete
- **Words in CHK-10:** "the buyer sees an error message"
- **A tester couldn't decide:** whether the message shown is the right one, since any wording would pass.
- **Question:** What does the message say when a payment is declined?

### F-14
- **Requirement:** CHK-10
- **Type:** Incomplete
- **Words in CHK-10:** "If a payment is declined, the buyer sees an error message."
- **A tester couldn't decide:** what the buyer should be able to do after the message, because the requirement stops there.
- **Question:** After the message, what can the buyer do next: try the payment again, or cancel back to the cart?

### F-10
- **Requirement:** CHK-12
- **Type:** Vague
- **Words in CHK-12:** "any number of buyers"
- **A tester couldn't decide:** how many buyers to test with: "any number" sets no maximum, so two testers would pick different numbers, and a number would fix it.
- **Question:** What is the largest number of buyers checking out at the same time that the system must support?

### F-11
- **Requirement:** CHK-12
- **Type:** Untestable
- **Words in CHK-12:** "handle"
- **A tester couldn't decide:** what result to check: "handle" names no expected outcome, and no number would supply one.
- **Question:** What counts as handling them: no errors, a response time, no seat sold twice?

## Unflagged requirements

- **CHK-01:** States the limit (8 seats), the exact message for a 9th seat, and that the 9th seat isn't held, so a tester knows what to try and what to expect.
- **CHK-03:** States the trigger (payment not completed), the timing (10 minutes after the hold starts) and the visible result (the seats show as available on the seat map).
- **CHK-06:** States the trigger (payment succeeds), the time limit (5 minutes) and every item the email contains. Removed after review: I had asked what happens when the buyer has no email address, but whether checkout requires an email belongs to a buyer-details requirement, not this one. It's the same reasoning that removed CHK-11.
- **CHK-09:** States the amount ($2.50 per ticket), where it appears (its own line on the payment page) and when (before the buyer pays). Removed after review: whether the fee is taxed is a tax rule that belongs in its own requirement, and CHK-09 is precise about the fee line it describes. It's the same reasoning that removed CHK-11.
- **CHK-11:** States a precise rule (the total shown equals the amount charged, to the cent) that a tester can check directly. Removed on a second look: I first asked what happens when the two don't match, but a mismatch is simply the test failing and a bug being logged; asking Tixly to detect it and stop the charge would be a new feature, not a gap in this requirement.
