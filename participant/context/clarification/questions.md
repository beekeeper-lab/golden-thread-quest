# Clarification questions: Tixly checkout

Questions for the Tixly product owner, drawn from the findings in
`participant/context/ambiguity/findings.md` (verified 10-28-2026). Decisions by Tom Carter; wording drafted with Claude (Claude Code), 10-28-2026.
These are drafts for a person to ask; nothing has been sent to anyone.

**How a question made this list:** if the product owner answered one way, then the other, would the
developer build something different? If yes, it's here. If both answers lead to the same work, it's in
`dropped.md` with the reason. A small question that still changes the work is kept and placed last,
not dropped.

**Order:** the questions the most work depends on come first: the whole system, then money flows,
then single screens, then small additions. Within each group, the question with more work riding on
it goes first.

## Questions

### Q-01
- **Finding:** F-10
- **Question:** What is the most buyers that must be able to check out at the same time?
- **Answer:** Up to a few hundred.
- **Work:** A single server and database are enough; standard load testing.
- **Answer:** Tens of thousands, for on-sale moments.
- **Work:** A waiting room or queue, more servers that scale up, and load tests at that size before launch.
- **Why this position:** It shapes the design of the whole system.

### Q-02
- **Finding:** F-11
- **Question:** What counts as handling that many buyers: no errors, a response time, or never selling a seat twice?
- **Answer:** No errors shown to buyers.
- **Work:** Error handling and monitoring; no change to how seats are reserved.
- **Answer:** Never selling the same seat twice.
- **Work:** Seat holds must lock each seat in the database so two buyers can't hold it at once, with tests that race two buyers for one seat.
- **Answer:** A response time, for example each checkout step answers within 3 seconds at that load.
- **Work:** Measure checkout speed under load and tune the slow steps (database queries, payment calls) until it meets the target.
- **Why this position:** Locking has to be built into checkout from the start; adding it later means reworking every seat hold.

### Q-03
- **Finding:** F-07
- **Question:** Which refund deadline applies: 48 hours before the event starts, or until the venue doors open?
- **Answer:** 48 hours before the event starts.
- **Work:** The refund option closes at a fixed time before each event's start time, which Tixly already has; later requests are refused.
- **Answer:** Until the venue doors open.
- **Work:** Tixly must store a doors-open time for every event, collect it from venues, and keep refunds open until that time.
- **Why this position:** The first money question: it's a contradiction, so the refund rules can't be built either way until it's settled, and one answer needs new venue data.

### Q-04
- **Finding:** F-04
- **Question:** Is a refund paid back to the original payment, or given as Tixly credit?
- **Answer:** Back to the original payment.
- **Work:** Call the payment provider's refund service and handle its failures and delays.
- **Answer:** As Tixly credit.
- **Work:** Build a credit balance for each buyer, show it at checkout, and let it be spent like a gift card.
- **Why this position:** It decides which money flow gets built, and both are sizeable.

### Q-05
- **Finding:** F-03
- **Question:** When a gift card is worth more than the order, does the leftover balance stay on the card?
- **Answer:** Yes, it stays on the card for a later order.
- **Work:** Store a remaining balance on each card, update it after every order, and show the buyer what's left.
- **Answer:** No, the card is used up by one order.
- **Work:** Mark the card as used after one order, with no balance to store; checkout warns the buyer before they give up the rest.
- **Why this position:** It changes the gift card records, and it comes before Q-08 because using part of a card only matters if the rest is kept.

### Q-06
- **Finding:** F-13
- **Question:** Can a refund requested in time ever be denied?
- **Answer:** No, every request made in time is approved.
- **Work:** Refunds are approved automatically; no review screen.
- **Answer:** Yes, for stated reasons.
- **Work:** Denial rules in the code, or a screen where staff approve or deny each request, plus a message telling the buyer why.
- **Why this position:** It decides whether refunds need people and a review step.

### Q-07
- **Finding:** F-14
- **Question:** After a declined payment, can the buyer try again, or are they sent back to the cart?
- **Answer:** They can try again with the same or another card.
- **Work:** The payment page stays open and the seats stay held, within CHK-03's 10-minute hold.
- **Answer:** They're sent back to the cart, and their seats are released.
- **Work:** The payment is abandoned, the hold ends at once, and the seats show as available on the seat map; the buyer must choose seats again.
- **Why this position:** It changes the checkout flow and how seat holds behave after a failure.

### Q-08
- **Finding:** F-03
- **Question:** Can a buyer choose to use only part of a gift card's balance on an order?
- **Answer:** No, the card covers as much of the order as it can.
- **Work:** No amount field at checkout; the card is applied automatically.
- **Answer:** Yes, the buyer enters how much of the card to use.
- **Work:** An amount field at checkout, checked against the card's balance and the order total.
- **Why this position:** It changes one field on the checkout screen, so it follows the larger refund and payment flows; it comes after Q-05 because it only matters if the rest of the card is kept.

### Q-09
- **Finding:** F-01
- **Question:** How many seconds may pass from opening an event to its seat map being usable?
- **Answer:** Up to 5 seconds.
- **Work:** Load the whole map in one request; no extra work.
- **Answer:** Under 1 second.
- **Work:** Cache the map and load seat availability in stages; test with the largest venue.
- **Why this position:** It can change how the map is built, but only on one screen.

### Q-10
- **Finding:** F-02
- **Question:** On what device, connection and venue size must the seat map be usable within its load time?
- **Answer:** A desktop on broadband, at a typical venue.
- **Work:** No extra work beyond Q-09's answer; test on one desktop setup.
- **Answer:** A mid-range phone on a slow mobile connection, at the largest venue.
- **Work:** Smaller map data and seats loaded in stages, tested on a slowed-down phone connection with the largest venue.
- **Why this position:** It goes with Q-09: together they set the load-time target, and both change only the seat map screen.

### Q-11
- **Finding:** F-09
- **Question:** Should the decline message say why the payment was declined, or just that it was?
- **Answer:** Just that it was declined.
- **Work:** One fixed message.
- **Answer:** Say why (for example, insufficient funds or an expired card).
- **Work:** Read the decline reason from the payment provider and show a different message for each reason.
- **Why this position:** Real new code, but contained to the decline message.

### Q-12
- **Finding:** F-06
- **Question:** What should a first-time buyer see at checkout that makes it feel trustworthy?
- **Answer:** A security badge and the card brands accepted.
- **Work:** Add the badge and logos to the payment page.
- **Answer:** The refund policy and the total, including fees, before the buyer starts paying.
- **Work:** A refund-policy link and a price summary shown from the first checkout step.
- **Why this position:** Each likely answer is a small visible addition.

### Q-13
- **Finding:** F-12
- **Question:** Does the buyer have to give a reason for a refund?
- **Answer:** No.
- **Work:** Nothing extra.
- **Answer:** Yes.
- **Work:** A required reason field, or a list of reasons to choose from, stored with the refund.
- **Why this position:** The smallest difference: one field. Kept because the answers still change the work.
