# Brief for the second person

What the second person is given: the automation criteria and the rule, copied word for word from
`participant/context/playwright/automation-criteria.md`, and 10 of the 15 test ideas, each with
exactly the idea and facts from `participant/context/playwright/candidate-decisions.md`. My answers,
decisions and reasons are not included. Prepared by Tom Carter, 11-02-2026, with Claude (Claude
Code); instructions revised 11-04-2026 after the first second person's attempt, which used
`second-person-brief-v1.md`. Only the instructions changed: the criteria, rule and facts are the
same. Tixly is an invented ticket app; nothing here describes a real product.

## How to take part

Thank you for helping. This takes about fifteen minutes, and there are no wrong answers: the point
is to see whether someone else reaches the same decisions from the same criteria and facts.

What the three decisions mean. Automate means a test program checks it, automatically, every time
the tests run. Manual means a person checks it by hand. Drop means it isn't tested at all, because
it isn't needed or another idea already checks it.

A few words used below, in plain terms. The regression suite is the set of checks run again before
every release, to make sure nothing that used to work has broken. The test environment is a
practice copy of the app used only for testing. A stand-in is a pretend version of an outside
system, such as a payment service, that a test controls. An outside system is a service someone
else runs, such as a real payment service, a real email inbox or a real phone.

How to decide each idea. Read the idea and its facts. Answer the criteria questions in order, from
C1. Then go down the decision rule yourself, from D1: the first step whose conditions match your
answers gives the decision, and you can stop there. Treat each idea's facts as true, even where
they are assumptions made for this exercise, such as a part of a page being redesigned: the point
is to see whether we reach the same decisions from the same facts, so please don't replace them
with your own view. If a fact seems missing, decide as best you can and say so. Risk numbers such
as R-15 refer to a test strategy you don't need to read.

Please work on your own, without seeing my decisions and without an AI assistant; if you do use
one, please tell me. Send back one line per idea, in the form "idea: decision (rule step)".

## The criteria

### C1 Needed
- **Question:** Does the idea check something a current requirement asks for, and is it not already checked by another test idea? When two ideas check the same thing, the one that checks it more directly (for example on the server rather than through a page) is kept, and the other is already checked.
- **Answers:** yes, no

### C2 Objective
- **Question:** Is the expected result definite enough for a machine to decide pass or fail? A fixed number, message or state is objective; a judgment such as "does it feel trustworthy" or "is it easy to use" is not.
- **Answers:** yes, no

### C3 Stable
- **Question:** Will the behavior and the parts of the screen this idea checks stay the same for the next three months? A part being redesigned, or a rule still being decided, is not stable; other parts of the same screen may still be stable.
- **Answers:** yes, no

### C4 Regression
- **Question:** Will the check be part of the regression suite, run again every release or every code change to confirm existing behavior still works? A one-time check, such as a launch-day check or a data migration, is not regression.
- **Answers:** yes, no

### C5 Value
- **Question:** If what the idea checks broke and nobody noticed, how bad would it be? 3: money is wrong, or a seat goes to the wrong buyer. 2: the buyer is blocked or misled, but no money is lost and no seat goes to the wrong buyer. 1: it is cosmetic or annoying.
- **Answers:** 3, 2, 1

### C6 Cost
- **Question:** How much effort would it take to build the automated test and keep it working, compared with checking it by hand? High: it needs a real outside system (a real payment service, a real inbox, a real phone), waits on real time, or would need fixing often. Low: it runs against the test environment with stand-ins for outside systems, and rarely needs fixing.
- **Answers:** low, high

## The decision rule

Go down the list; the first step that applies gives the decision.

### D1
- **If:** C1 is no
- **Then:** drop

### D2
- **If:** C2 is no
- **Then:** manual

### D3
- **If:** C3 is no
- **Then:** manual

### D4
- **If:** C4 is yes, C5 is 3 or 2, and C6 is low
- **Then:** automate

### D5
- **If:** C4 is yes, C5 is 3, and C6 is high
- **Then:** automate

### D6
- **If:** none of the steps above applies
- **Then:** manual

## The test ideas

### I-01
- **Idea:** The service fee is $2.50 per ticket for every seat count from 1 to 8.
- **Facts:** Checks requirement CHK-09 through the function that works out the fee (R-15). Runs against the test environment with no outside system. The fee rule isn't changing. Would run every release.

### I-02
- **Idea:** Two buyers try to hold the same seat at the same moment, and only one of them gets it.
- **Facts:** Checks requirement CHK-12 by sending both requests to the server at once, many times over (R-20). Runs against the test environment with no outside system. The seat-hold rule isn't changing. Would run every release.

### I-04
- **Idea:** After the venue doors open, the refund page shows the message that refunds have closed.
- **Facts:** Checks requirement CHK-05 on the refund page in a browser (R-26). Runs against the test environment with no outside system. The refund page isn't changing. Would run every release.

### I-05
- **Idea:** The checkout page feels trustworthy to someone buying from Tixly for the first time.
- **Facts:** Checks the intent behind requirement CHK-07 (my quest 7 reflection on R-13). Whether a page feels trustworthy is a person's judgment.

### I-06
- **Idea:** The seat map is usable within 5 seconds on a real mid-range phone over a slow mobile connection, at the largest venue.
- **Facts:** Checks requirement CHK-02 on a real phone (my quest 7 reflection on R-03), not a simulated one. Would run every release.

### I-07
- **Idea:** The confirmation email actually arrives in a real inbox within 5 minutes of paying.
- **Facts:** Checks requirement CHK-06 end to end through the real email service (R-11). Would run every release.

### I-11
- **Idea:** The 8-seat limit, checked by clicking 9 seats on the seat map in a browser.
- **Facts:** Checks requirement CHK-01 through the page. I-12 checks the same limit directly on the server.

### I-12
- **Idea:** The server refuses a 9th seat in one order, even when asked directly without the seat map.
- **Facts:** Checks requirement CHK-01 on the server (R-27). Runs against the test environment with no outside system. The limit isn't changing. Would run every release.

### I-13
- **Idea:** On Tixly's first public on-sale day, a person buys one ticket from start to finish.
- **Facts:** A one-time launch-day check of the whole checkout (requirements CHK-01 to CHK-12 together), done once and not repeated.

### I-14
- **Idea:** Before paying, the payment page shows the refund policy and the full total, fees included.
- **Facts:** Checks requirement CHK-07 on the payment page (R-13). Assume the payment page's order summary panel, where the refund policy and the total appear, is being redesigned over the next two sprints; the rest of the page isn't changing.
