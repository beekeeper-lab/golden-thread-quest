# Tixly checkout requirements (clarified)

Tixly is an invented event-ticket app. Every requirement, rule, number and answer below is
synthetic, written for this exercise. No real product, company or person is described, and no real
product owner was asked.

These are the twelve checkout requirements from `participant/context/ambiguity/requirements.md`
(quest 4), rewritten so each one can be tested. Where the original was vague or contradictory, it
now uses **assumed answers** to one or more questions in
`participant/context/clarification/questions.md` (quest 5), one answer per question. The three
answers already used for the follow-up stories in
`participant/context/write-preview/follow-up-stories.yaml` (quest 6) are kept the same. One more
answer, for CHK-03, was added during the strategy review and is marked as such. Decisions by Tom
Carter; wording drafted with Claude (Claude Code), 10-30-2026.

**Importance** says how much the business depends on the requirement:

- **High:** money, or which buyer gets a seat, depends on it.
- **Medium:** the buyer can still get their tickets, but the checkout works less well.
- **Low:** it affects how checkout feels, not what it does.

Importance is not the same as risk. Risk also depends on how likely the requirement is to break;
that is scored in `strategy.md`.

## Requirements

### CHK-01
- **Importance:** Medium
- **Requirement:** A buyer can hold up to 8 seats for one event in a single order. Choosing a 9th seat shows the message "You can buy up to 8 seats per order." and the 9th seat is not held.
- **Assumed answer:** None needed; the original was already clear.

### CHK-02
- **Importance:** Medium
- **Requirement:** The seat map is usable within 5 seconds of opening an event, on a mid-range phone with a slow mobile connection, for the largest venue.
- **Assumed answer:** Q-09 (up to 5 seconds) and Q-10 (a mid-range phone on a slow mobile connection, at the largest venue).

### CHK-03
- **Importance:** High
- **Requirement:** Held seats are released 10 minutes after the hold starts if payment has not completed. A hold does not expire while its payment is being processed: if the payment succeeds, the seats are the buyer's; if it fails, the 10-minute rule applies as usual. Released seats show as available on the seat map.
- **Assumed answer:** Added during the strategy review, not one of the quest 5 questions: the original said nothing about a hold that reaches 10 minutes while its payment is still being processed, so this answer was decided by Tom Carter for this exercise.

### CHK-04
- **Importance:** High
- **Requirement:** A buyer can apply a Tixly gift card at checkout. The card covers as much of the order total as its balance allows; there is no field for choosing a smaller amount. Any balance left after the order stays on the card for a later order.
- **Assumed answer:** Q-05 (the leftover balance stays on the card) and Q-08 (the card covers as much as it can).

### CHK-05
- **Importance:** High
- **Requirement:** A refund requested at or after the moment the venue doors open is refused, and the buyer is told refunds closed when the doors opened.
- **Assumed answer:** Q-03 (refunds are available until the venue doors open), which removes the contradiction with CHK-08. A request at the exact moment the doors open is refused, so the boundary has one expected result.

### CHK-06
- **Importance:** Medium
- **Requirement:** After payment succeeds, Tixly sends a confirmation email within 5 minutes. The email contains the order number, the event name, the event date and start time, and every seat number.
- **Assumed answer:** None needed; the original was already clear.

### CHK-07
- **Importance:** Low
- **Requirement:** Before the buyer starts paying, checkout shows the refund policy and the full order total, fees included.
- **Assumed answer:** Q-12 (the refund policy and the total, including fees, before the buyer starts paying).

### CHK-08
- **Importance:** High
- **Requirement:** Before the venue doors open, a buyer can cancel an order and receive a full refund to the original payment. Every request made in time is approved, and no reason is asked for.
- **Assumed answer:** Q-03 (until the venue doors open), Q-04 (back to the original payment), Q-06 (every request made in time is approved) and Q-13 (no reason needed).

### CHK-09
- **Importance:** High
- **Requirement:** A service fee of $2.50 per ticket is shown as its own line on the payment page, before the buyer pays.
- **Assumed answer:** None needed; the original was already clear.

### CHK-10
- **Importance:** Medium
- **Requirement:** If a payment is declined, the buyer sees a message saying it was declined and can try again with the same or another card. Their seats stay held, within the 10-minute hold in CHK-03.
- **Assumed answer:** Q-07 (the buyer can try again) and Q-11 (the message just says it was declined).

### CHK-11
- **Importance:** High
- **Requirement:** The order total shown on the payment page equals the amount charged, to the cent.
- **Assumed answer:** None needed; the original was already clear.

### CHK-12
- **Importance:** High
- **Requirement:** Up to a few hundred buyers can check out at the same time, and the same seat is never sold to two buyers.
- **Assumed answer:** Q-01 (up to a few hundred) and Q-02 (never selling the same seat twice).
