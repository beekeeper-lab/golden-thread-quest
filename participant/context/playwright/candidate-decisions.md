# Automation decisions: Tixly checkout test ideas

Fifteen test ideas for the checkout of Tixly, an invented ticket app, each decided with the
criteria and rule in `participant/context/playwright/automation-criteria.md`. The ideas come from
the layered test strategy in `participant/context/playwright/strategy.md` (risk numbers such as
R-15 refer to it). Decisions by Tom Carter, 11-02-2026, recorded before any second person's
answers were seen; wording drafted with Claude (Claude Code).

Each idea gives the facts someone needs to apply the criteria, my answer to each criterion the
rule needed, the decision with the rule step that gave it, and the reason. A manual idea also says
how it will be checked instead. Criteria after the deciding step aren't answered, because the
rule stops there.

## Decisions

### I-01
- **Idea:** The service fee is $2.50 per ticket for every seat count from 1 to 8.
- **Facts:** Checks requirement CHK-09 through the function that works out the fee (R-15). Runs against the test environment with no outside system. The fee rule isn't changing. Would run every release.
- **Criteria:** C1 yes; C2 yes; C3 yes; C4 yes; C5 3; C6 low
- **Decision:** automate
- **Rule step:** D4
- **Reason:** A wrong fee charges every buyer the wrong amount, and it has to be rechecked on every release; with no outside system it is cheap to keep working.

### I-02
- **Idea:** Two buyers try to hold the same seat at the same moment, and only one of them gets it.
- **Facts:** Checks requirement CHK-12 by sending both requests to the server at once, many times over (R-20). Runs against the test environment with no outside system. The seat-hold rule isn't changing. Would run every release.
- **Criteria:** C1 yes; C2 yes; C3 yes; C4 yes; C5 3; C6 low
- **Decision:** automate
- **Rule step:** D4
- **Reason:** A seat sold to two buyers is the worst outcome in the strategy, a person can't time two requests closely enough to check it by hand, and it must be rechecked on every release.

### I-03
- **Idea:** A seat hold with no payment in progress is released exactly 10 minutes after it starts.
- **Facts:** Checks requirement CHK-03 with a pretend clock, at 9:59, 10:00 and 10:01 (R-04); a hold whose payment is still being processed doesn't expire, which I-08 covers. Runs against the test environment with no outside system. The 10-minute rule isn't changing. Would run every release.
- **Criteria:** C1 yes; C2 yes; C3 yes; C4 yes; C5 3; C6 low
- **Decision:** automate
- **Rule step:** D4
- **Reason:** Releasing a seat early gives a paying buyer's seat to someone else; the pretend clock makes it a quick, repeatable regression check instead of a 10-minute wait.

### I-04
- **Idea:** After the venue doors open, the refund page shows the message that refunds have closed.
- **Facts:** Checks requirement CHK-05 on the refund page in a browser (R-26). Runs against the test environment with no outside system. The refund page isn't changing. Would run every release.
- **Criteria:** C1 yes; C2 yes; C3 yes; C4 yes; C5 2; C6 low
- **Decision:** automate
- **Rule step:** D4
- **Reason:** A buyer who isn't told why a refund was refused is misled, the message is fixed text, and it must be rechecked on every release.

### I-05
- **Idea:** The checkout page feels trustworthy to someone buying from Tixly for the first time.
- **Facts:** Checks the intent behind requirement CHK-07 (my quest 7 reflection on R-13). Whether a page feels trustworthy is a person's judgment.
- **Criteria:** C1 yes; C2 no
- **Decision:** manual
- **Rule step:** D2
- **Reason:** No test can decide whether a page feels trustworthy; a test can only confirm what is on it, which other ideas already do.
- **Checked instead:** Once per release, a tester who hasn't used Tixly goes through checkout as a first-time buyer and notes anything that would make them hesitate to pay.

### I-06
- **Idea:** The seat map is usable within 5 seconds on a real mid-range phone over a slow mobile connection, at the largest venue.
- **Facts:** Checks requirement CHK-02 on a real phone (my quest 7 reflection on R-03), not a simulated one. Would run every release.
- **Criteria:** C1 yes; C2 yes; C3 yes; C4 yes; C5 2; C6 high
- **Decision:** manual
- **Rule step:** D6
- **Reason:** A slow seat map blocks the buyer but loses no money, and a test that needs a real phone on a real slow connection costs more to keep working than checking it by hand. The simulated-phone timing is already a separate automated test in the strategy (R-03).
- **Checked instead:** Once per release, a tester opens the largest venue's seat map on a real mid-range phone on a slow mobile connection and times how long it takes to become usable.

### I-07
- **Idea:** The confirmation email actually arrives in a real inbox within 5 minutes of paying.
- **Facts:** Checks requirement CHK-06 end to end through the real email service (R-11). Would run every release.
- **Criteria:** C1 yes; C2 yes; C3 yes; C4 yes; C5 2; C6 high
- **Decision:** manual
- **Rule step:** D6
- **Reason:** A late email misleads the buyer but loses no money, and a test that waits on a real inbox needs a real account and fails whenever delivery is slow.
- **Checked instead:** Once per release, a tester buys one ticket in the test environment and notes when the email arrives and whether it holds every required detail.

### I-08
- **Idea:** A seat hold reaching 10 minutes while its payment is still being processed, tried against the payment provider's own test environment.
- **Facts:** Checks requirement CHK-03 through the real payment service's test environment, not a stand-in (my quest 7 reflection on R-28). Would run every release.
- **Criteria:** C1 yes; C2 yes; C3 yes; C4 yes; C5 3; C6 high
- **Decision:** automate
- **Rule step:** D5
- **Reason:** A seat given to two buyers is the worst outcome in the strategy, and the payment service's real timing can't be seen with a stand-in, so it is worth automating against its test environment despite the cost.

### I-09
- **Idea:** The confirmation email looks right in the most common email apps.
- **Facts:** Checks how the email in requirement CHK-06 is laid out in different email apps (R-12). Whether it "looks right" is a person's judgment.
- **Criteria:** C1 yes; C2 no
- **Decision:** manual
- **Rule step:** D2
- **Reason:** "Looks right" is a judgment, not a result a test can decide; the email's content is checked separately.
- **Checked instead:** Once per release, a tester opens the confirmation email in the three most common email apps and notes anything cut off or hard to read.

### I-10
- **Idea:** A gift card worth more than the order covers the whole order and keeps the leftover balance.
- **Facts:** Checks requirement CHK-04 through the server: place an order with the card, then read the card's balance back (R-06, R-07). Runs against the test environment with no outside system. The gift card rules aren't changing. Would run every release.
- **Criteria:** C1 yes; C2 yes; C3 yes; C4 yes; C5 3; C6 low
- **Decision:** automate
- **Rule step:** D4
- **Reason:** A wrong balance takes or loses the buyer's money, and it must be rechecked on every release.

### I-11
- **Idea:** The 8-seat limit, checked by clicking 9 seats on the seat map in a browser.
- **Facts:** Checks requirement CHK-01 through the page. I-12 checks the same limit directly on the server.
- **Criteria:** C1 no
- **Decision:** drop
- **Rule step:** D1
- **Reason:** The limit itself is already checked by I-12, faster and more reliably; clicking nine seats would check the same thing again.

### I-12
- **Idea:** The server refuses a 9th seat in one order, even when asked directly without the seat map.
- **Facts:** Checks requirement CHK-01 on the server (R-27). Runs against the test environment with no outside system. The limit isn't changing. Would run every release.
- **Criteria:** C1 yes; C2 yes; C3 yes; C4 yes; C5 2; C6 low
- **Decision:** automate
- **Rule step:** D4
- **Reason:** A buyer holding more than 8 seats blocks other buyers from them, and the server's refusal is a definite result to recheck on every release.

### I-13
- **Idea:** On Tixly's first public on-sale day, a person buys one ticket from start to finish.
- **Facts:** A one-time launch-day check of the whole checkout (requirements CHK-01 to CHK-12 together), done once and not repeated.
- **Criteria:** C1 yes; C2 yes; C3 yes; C4 no; C5 3; C6 high
- **Decision:** manual
- **Rule step:** D6
- **Reason:** It happens once, so an automated test would be built for a single run; the regression checks above cover the same rules on every release.
- **Checked instead:** On launch day, a named person buys one ticket and records each step and the confirmation email.

### I-14
- **Idea:** Before paying, the payment page shows the refund policy and the full total, fees included.
- **Facts:** Checks requirement CHK-07 on the payment page (R-13). Assume the payment page's order summary panel, where the refund policy and the total appear, is being redesigned over the next two sprints; the rest of the page isn't changing.
- **Criteria:** C1 yes; C2 yes; C3 no
- **Decision:** manual
- **Rule step:** D3
- **Reason:** A test written against a panel that is being redesigned would need rewriting every sprint; that is the mistake in the quest's scenario.
- **Checked instead:** Each sprint until the redesign is finished, a tester checks the payment page shows the refund policy and the full total before paying; once the page settles, the idea is decided again.

### I-15
- **Idea:** After a declined payment, the payment page shows the decline message and lets the buyer try again.
- **Facts:** Checks requirement CHK-10 on the payment page with a stand-in payment service that declines the first attempt (R-18). The decline message and the card form aren't part of the redesign in I-14 and aren't changing. Would run every release.
- **Criteria:** C1 yes; C2 yes; C3 yes; C4 yes; C5 2; C6 low
- **Decision:** automate
- **Rule step:** D4
- **Reason:** A buyer who can't retry is blocked from paying, and the message and form are definite results to recheck on every release.
