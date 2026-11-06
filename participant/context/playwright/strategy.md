# Tixly checkout: layered test strategy

The test strategy for the twelve requirements in `participant/context/playwright/requirements.md`.
It decides what to test and where before any test is written: each risk goes to the cheapest test
layer that would fail if that risk happened, and the strategy says plainly what it leaves untested.
Tixly and everything about it are synthetic. Decisions by Tom Carter; wording drafted with Claude
(Claude Code), 10-30-2026.

## How risks are scored

Each risk is scored on two scales, from 1 to 3. The levels are defined by what can be seen in the
requirement, so another person scoring the same risk should get the same numbers.

**Likelihood** (how likely the risk is to happen), from the kind of logic involved:

- **3:** it involves arithmetic, a time limit, more than one person at once, or another system (the
  payment provider or the email service).
- **2:** it is a rule with a few cases.
- **1:** it shows a fixed value or a fixed message.

If a risk fits more than one level, it takes the highest. A risk is scored for what its own step
does, not for an earlier step it depends on: the seat map drawing a seat that the hold timer has
released is a rule with a few cases (2), while the hold timer itself is a time limit (3).

**Impact** (what happens if it does):

- **3:** money is wrong, or a seat goes to the wrong buyer (or to two buyers).
- **2:** the buyer is blocked or misled, but no money is lost and no seat goes to the wrong buyer.
- **1:** it is cosmetic or annoying.

**Score** = likelihood × impact, from 1 to 9. Risks are ranked by score, highest first. Ties go to
the risk whose requirement has the higher importance (High, then Medium, then Low, as defined in
`requirements.md`; for a risk with several requirements, the highest of them). Remaining ties go
in risk number order.

## The test layers

From cheapest to most expensive. A risk goes to the cheapest layer where a test would fail if the
risk happened.

- **unit:** one function tested alone, with no server, database or browser. Runs in milliseconds,
  and can try many values (every seat count from 1 to 8, every minute around a deadline).
- **API:** calls Tixly's server directly, with a test database, a fake payment provider and a fake
  mailbox. Runs in seconds. Catches what only shows when parts work together: what is saved, what
  is charged, what is sent.
- **UI:** a Playwright test in a real browser. The slowest and the most likely to break when a page
  changes, so it is used only for risks that live in the browser: what the buyer sees, and whether
  the pages connect.
- **manual:** a person checks it, once per release. Used only where an automated test can't see the
  risk.
- **untested:** no test. Each one is listed with the reason and who accepted it.

## Ranking

| Rank | Risk | Requirement | Likelihood | Impact | Score | Layer |
|---|---|---|---|---|---|---|
| 1 | R-04 | CHK-03 | 3 | 3 | 9 | unit |
| 2 | R-06 | CHK-04 | 3 | 3 | 9 | unit |
| 3 | R-07 | CHK-04 | 3 | 3 | 9 | API |
| 4 | R-08 | CHK-05, CHK-08 | 3 | 3 | 9 | unit |
| 5 | R-09 | CHK-05 | 3 | 3 | 9 | API |
| 6 | R-14 | CHK-08 | 3 | 3 | 9 | API |
| 7 | R-15 | CHK-09 | 3 | 3 | 9 | unit |
| 8 | R-19 | CHK-11 | 3 | 3 | 9 | API |
| 9 | R-20 | CHK-12 | 3 | 3 | 9 | API |
| 10 | R-28 | CHK-03 | 3 | 3 | 9 | API |
| 11 | R-21 | CHK-12 | 3 | 2 | 6 | untested |
| 12 | R-24 | CHK-11 | 2 | 3 | 6 | UI |
| 13 | R-03 | CHK-02 | 3 | 2 | 6 | UI |
| 14 | R-10 | CHK-06 | 3 | 2 | 6 | API |
| 15 | R-11 | CHK-06 | 3 | 2 | 6 | manual |
| 16 | R-17 | CHK-10 | 3 | 2 | 6 | API |
| 17 | R-05 | CHK-03 | 2 | 2 | 4 | API |
| 18 | R-22 | CHK-03, CHK-09, CHK-11 | 2 | 2 | 4 | UI |
| 19 | R-23 | CHK-03 | 2 | 2 | 4 | UI |
| 20 | R-26 | CHK-05, CHK-08 | 2 | 2 | 4 | UI |
| 21 | R-01 | CHK-01 | 2 | 2 | 4 | unit |
| 22 | R-18 | CHK-10 | 2 | 2 | 4 | UI |
| 23 | R-27 | CHK-01 | 2 | 2 | 4 | API |
| 24 | R-16 | CHK-09 | 1 | 2 | 2 | UI |
| 25 | R-25 | CHK-04 | 1 | 2 | 2 | UI |
| 26 | R-02 | CHK-01 | 1 | 2 | 2 | UI |
| 27 | R-12 | CHK-06 | 2 | 1 | 2 | untested |
| 28 | R-13 | CHK-07 | 1 | 2 | 2 | UI |

Totals: 5 unit, 10 API, 10 UI, 1 manual, 2 untested. Every requirement from CHK-01 to CHK-12 has at
least one tested risk.

## Risks that need a browser

These are the only risks given a UI test. Each one lives in what the buyer sees or in how the pages
connect, so nothing cheaper would fail if it broke.

### R-02
- **Requirement:** CHK-01
- **Risk:** Choosing a 9th seat doesn't show the message "You can buy up to 8 seats per order.", so the buyer doesn't know why the seat wasn't held.
- **Likelihood:** 1 (a fixed message)
- **Impact:** 2 (the buyer is misled)
- **Layer:** UI
- **Reason:** The limit itself is tested in R-01; what's left is whether the page shows the message, which only a browser can see. It is one extra step in an existing seat-map test, not a test of its own.

### R-03
- **Requirement:** CHK-02
- **Risk:** The seat map takes longer than 5 seconds to become usable on a mid-range phone with a slow connection, at the largest venue.
- **Likelihood:** 3 (a time limit)
- **Impact:** 2 (the buyer is blocked)
- **Layer:** UI
- **Reason:** Load time includes the page, its scripts and drawing the map, which only a browser does. Playwright can slow the network and the processor to match the requirement's phone and connection.

### R-13
- **Requirement:** CHK-07
- **Risk:** The refund policy or the full total, fees included, isn't shown before the buyer starts paying.
- **Likelihood:** 1 (fixed content)
- **Impact:** 2 (the buyer is misled about what they will pay before they start paying)
- **Layer:** UI
- **Reason:** It is about what is on the screen and when, so only a browser can see it. It costs two extra checks in the checkout test in R-22, not a separate test.

### R-16
- **Requirement:** CHK-09
- **Risk:** The service fee isn't shown as its own line on the payment page, or the line shows an amount other than $2.50 for each ticket.
- **Likelihood:** 1 (a fixed line showing the fee the server works out)
- **Impact:** 2 (the buyer is misled about what they're paying for)
- **Layer:** UI
- **Reason:** The fee is worked out and tested in R-15; whether the page shows it as its own line, with the right amount, can only be seen in a browser. It is one extra check in the checkout test in R-22: two seats, so the line must show $5.00.

### R-18
- **Requirement:** CHK-10
- **Risk:** After a declined payment, the payment page doesn't show the decline message or doesn't let the buyer enter a card again.
- **Likelihood:** 2 (a rule with a few cases)
- **Impact:** 2 (the buyer is blocked)
- **Layer:** UI
- **Reason:** The server's side of the retry is tested in R-17; what's left is whether the page shows the message and keeps the card form usable, which only a browser can see.

### R-22
- **Requirement:** CHK-03, CHK-09, CHK-11
- **Risk:** Every part works on its own, but the full checkout in a browser doesn't: choosing seats, the payment page and the confirmation don't connect.
- **Likelihood:** 2 (a few steps that must connect)
- **Impact:** 2 (buyers are blocked; no money is taken and no seat goes to the wrong buyer)
- **Layer:** UI
- **Reason:** Only a browser goes through the real pages in order. This is the one end-to-end checkout test: one buyer, two seats, the fake payment provider accepts, and the confirmation page shows the order. The detailed rules stay in the unit and API tests; this test adds only the page checks in R-13, R-16, R-24 and R-25.

### R-23
- **Requirement:** CHK-03
- **Risk:** After a hold is released, the seat map still draws the seat as taken when it is opened or refreshed, although the server reports it available.
- **Likelihood:** 2 (a rule with a few cases)
- **Impact:** 2 (buyers are blocked from that seat)
- **Layer:** UI
- **Reason:** R-05 proves the server reports the seat as available; only a browser shows whether the map then draws it that way. One seat-map test holds a seat, moves the test server's clock past 10 minutes, refreshes the map and checks the seat is shown as available.

### R-24
- **Requirement:** CHK-11
- **Risk:** The total the payment page shows differs from the amount charged, for example because the page still shows the total from before a gift card was applied. The page only shows the total the server sends; working it out and rounding it are the server's step, covered by R-19.
- **Likelihood:** 2 (a rule with a few cases: show the server's total, and show it again after a gift card)
- **Impact:** 3 (money is wrong: the buyer is charged an amount they were not shown)
- **Layer:** UI
- **Reason:** R-19 proves the server's total matches the charge, but only a browser sees the total the buyer actually reads. The checkout test in R-22 reads the total on the payment page and compares it with the amount the fake payment provider received, once without a gift card and once with one.

### R-25
- **Requirement:** CHK-04
- **Risk:** The payment page offers a field for choosing how much of the gift card to use, although the card should always cover as much of the order as its balance allows.
- **Likelihood:** 1 (a fixed part of the page: the field is there or it isn't)
- **Impact:** 2 (the buyer is misled into thinking they can choose the amount)
- **Layer:** UI
- **Reason:** R-06 proves the amount the server takes from the card; whether the page offers an amount field can only be seen in a browser. It is one extra check in the gift-card run of the checkout test in R-24, not a test of its own.

### R-26
- **Requirement:** CHK-05, CHK-08
- **Risk:** On the refund page, a refund refused after the doors opened doesn't show the message that refunds closed, or a cancellation made in time asks the buyer for a reason.
- **Likelihood:** 2 (a rule with a few cases: the request is refused or accepted)
- **Impact:** 2 (the buyer is misled, or blocked by a question they shouldn't be asked)
- **Layer:** UI
- **Reason:** R-09 proves the server refuses a late refund with the right message, and R-14 proves a cancellation needs nothing but the request; only a browser shows what the refund page then asks and says. One refund-page test cancels an order before the doors open and checks no reason is asked for, then tries one after and checks the message is shown.

## Risks that don't need a browser

### R-01
- **Requirement:** CHK-01
- **Risk:** The 8-seat limit is off by one: a 9th seat is held, or the 8th is refused.
- **Likelihood:** 2 (a rule with a few cases)
- **Impact:** 2 (the buyer is blocked, or holds more seats than allowed)
- **Layer:** unit
- **Reason:** The limit is one rule in one function. A unit test can try every count from 1 to 9 in milliseconds; a browser would have to click nine seats to try one count.

### R-04
- **Requirement:** CHK-03
- **Risk:** A seat hold is released at the wrong time: before 10 minutes, so a paying buyer loses the seat, or not at all, so the seat can't be sold.
- **Likelihood:** 3 (a time limit)
- **Impact:** 3 (a seat goes to the wrong buyer, or can't be sold)
- **Layer:** unit
- **Reason:** A unit test with a fake clock can check 9:59, 10:00 and 10:01 instantly. A browser test would wait 10 real minutes and still only try one moment.

### R-05
- **Requirement:** CHK-03
- **Risk:** After a hold is released, the seat is still reported as taken, so no one else can buy it.
- **Likelihood:** 2 (a rule with a few cases)
- **Impact:** 2 (buyers are blocked from that seat)
- **Layer:** API
- **Reason:** Whether the seat is available is decided by the server, and the seat map only draws what the server reports. An API test can release a hold with a fake clock and read the seat's availability back.

### R-06
- **Requirement:** CHK-04
- **Risk:** The gift card amount is worked out wrongly: when the card is worth more than the order, less, or exactly the same.
- **Likelihood:** 3 (arithmetic)
- **Impact:** 3 (money is wrong)
- **Layer:** unit
- **Reason:** It is arithmetic in one function. A unit test can try every case, including the exact-match and one-cent edges, in milliseconds.

### R-07
- **Requirement:** CHK-04
- **Risk:** The balance left on a gift card isn't saved after the order, or is saved wrongly, so the next order sees the wrong balance.
- **Likelihood:** 3 (arithmetic: the balance left is the old balance minus the amount used)
- **Impact:** 3 (money is wrong)
- **Layer:** API
- **Reason:** The risk is in what is saved, which a unit test can't see. An API test can place one order with a card, then read the card's balance back. No browser is needed to check a saved number.

### R-08
- **Requirement:** CHK-05, CHK-08
- **Risk:** The refund deadline is worked out wrongly: refunds close before the venue doors open, or stay open at or after that moment, for example because of the venue's time zone.
- **Likelihood:** 3 (a time limit)
- **Impact:** 3 (money is wrong)
- **Layer:** unit
- **Reason:** It is a date-and-time rule in one function. A unit test with a fake clock can check one minute before doors open, the exact moment they open and one minute after, in several time zones, instantly.

### R-09
- **Requirement:** CHK-05
- **Risk:** A refund requested at or after the moment the doors opened is accepted by the server, or is refused without the message saying refunds closed when the doors opened.
- **Likelihood:** 3 (a time limit: the event's doors-open time)
- **Impact:** 3 (money is wrong)
- **Layer:** API
- **Reason:** The unit test in R-08 proves the rule; this checks that the server actually uses it with the event's stored doors-open time, and returns the refusal message. Both are in the server's response, so no browser is needed.

### R-10
- **Requirement:** CHK-06
- **Risk:** After payment succeeds, Tixly doesn't send the confirmation email, sends it late, or leaves out the order number, event name, date and start time, or a seat number.
- **Likelihood:** 3 (another system: the email service)
- **Impact:** 2 (the buyer is misled; the order itself is fine)
- **Layer:** API
- **Reason:** An API test can pay with the fake payment provider, then read the fake mailbox: when the email was handed over and what it contains. No browser is involved in sending email.

### R-11
- **Requirement:** CHK-06
- **Risk:** Tixly hands the email over in time, but the real email service delivers it late or not at all.
- **Likelihood:** 3 (another system: the email service)
- **Impact:** 2 (the buyer is misled; the order itself is fine)
- **Layer:** manual
- **Reason:** The fake mailbox in R-10 can't show what the real email service does. An automated test against a real inbox needs a real account and fails whenever delivery is slow. Once per release, a person buys one ticket in the test environment and notes when the email arrives.

### R-14
- **Requirement:** CHK-08
- **Risk:** A cancelled order is refunded the wrong amount, or to something other than the original payment, or an in-time request is not approved.
- **Likelihood:** 3 (another system: the payment provider)
- **Impact:** 3 (money is wrong)
- **Layer:** API
- **Reason:** The risk is in what the server asks the payment provider to do. An API test can cancel an order and check the fake provider received one full refund to the original payment.

### R-15
- **Requirement:** CHK-09
- **Risk:** The service fee is worked out wrongly: not $2.50 for every ticket, or rounded wrongly.
- **Likelihood:** 3 (arithmetic)
- **Impact:** 3 (money is wrong)
- **Layer:** unit
- **Reason:** It is arithmetic in one function, so a unit test can check every seat count from 1 to 8 in milliseconds. A browser test would check one count per run, slowly, and would read the amount off a page that can change.

### R-17
- **Requirement:** CHK-10
- **Risk:** After a declined payment, the server releases the buyer's seats or refuses a second payment attempt.
- **Likelihood:** 3 (another system: the payment provider)
- **Impact:** 2 (the buyer is blocked)
- **Layer:** API
- **Reason:** The fake payment provider can decline the first payment and accept the second. An API test can then check that the seats were still held and the second payment went through. Both are server behaviour.

### R-19
- **Requirement:** CHK-11
- **Risk:** The total the server sends to the payment page differs from the amount it charges, for example because the two are worked out in different places or rounded differently.
- **Likelihood:** 3 (arithmetic)
- **Impact:** 3 (money is wrong)
- **Layer:** API
- **Reason:** Both totals come from the server, so an API test can read the total it sends to the payment page, pay with the fake provider and compare it with the amount charged, to the cent, for orders with fees and gift cards.

### R-20
- **Requirement:** CHK-12
- **Risk:** Two buyers hold the same seat at the same moment, and both are sold it.
- **Likelihood:** 3 (more than one person at once)
- **Impact:** 3 (a seat goes to two buyers)
- **Layer:** API
- **Reason:** The risk is two requests reaching the server at the same moment. An API test can send both at once, many times over, and check only one succeeds. Two browsers could not time their clicks closely enough to find it reliably.

### R-27
- **Requirement:** CHK-01
- **Risk:** The server holds a 9th seat when it is asked directly, without going through the seat map, so a buyer can hold more than 8 seats in one order.
- **Likelihood:** 2 (a rule with a few cases)
- **Impact:** 2 (the buyer holds more seats than allowed, blocking other buyers from them)
- **Layer:** API
- **Reason:** R-01 proves the limit rule on its own and R-02 the message on the page; this checks the server actually applies the limit to every request. An API test asks the server for a 9th seat in one order and checks it is refused and only 8 seats are held.

### R-28
- **Requirement:** CHK-03
- **Risk:** A hold reaches 10 minutes while its payment is still being processed, and the server gets it wrong: the seat is released and held by another buyer although the payment then succeeds, or after the payment is declined the seat is kept past the original 10 minutes (held on, or given a fresh 10 minutes).
- **Likelihood:** 3 (a time limit, another system and two buyers at once)
- **Impact:** 3 (a seat goes to two buyers; a seat kept too long only blocks other buyers, but the highest level applies)
- **Layer:** API
- **Reason:** It needs a fake clock and a fake payment provider that answers slowly, which only the server-level tests have. One API test runs three times. Each run starts a payment at 9:58 and holds the provider's answer. In the first, the clock moves past 10:00, a second buyer tries to hold the seat, the payment succeeds, and the seat must belong only to the first buyer. In the second, the clock moves past 10:00 and the payment is declined, and the seat must be released at once. In the third, the payment is declined at 9:59, and the seat must be released at 10:00, not 10 minutes after the decline.

## Accepted as untested

### R-12
- **Requirement:** CHK-06
- **Risk:** The confirmation email looks wrong in some email apps (for example, the seat list is cut off or badly laid out).
- **Likelihood:** 2 (a few email apps, each showing email its own way)
- **Impact:** 1 (annoying; the content is correct, as R-10 checks)
- **Layer:** untested
- **Reason:** R-10 already checks the email holds every required detail. Checking how it looks in each email app needs a paid preview service or many accounts, which costs more than a score of 2 is worth.
- **Accepted by:** Tom Carter, acting as the Tixly product owner for this exercise, 10-30-2026.

### R-21
- **Requirement:** CHK-12
- **Risk:** With a few hundred buyers checking out at once, checkout slows down or shows errors.
- **Likelihood:** 3 (more than one person at once)
- **Impact:** 2 (buyers are blocked; R-20 covers seats going to two buyers)
- **Layer:** untested
- **Reason:** None of the four layers can run hundreds of buyers at once; that needs a separate load-testing tool and a test environment sized like the real one. A few hundred buyers is a modest load, and the part of CHK-12 where money or seats go wrong is tested in R-20. Revisit before any on-sale expected to draw more buyers.
- **Accepted by:** Tom Carter, acting as the Tixly product owner for this exercise, 10-30-2026.

## Outside this strategy

The strategy covers the twelve requirements and nothing else. Accessibility, security and browser
compatibility are not in the requirements, so they are not scored here; a real team would add
requirements for them first.
