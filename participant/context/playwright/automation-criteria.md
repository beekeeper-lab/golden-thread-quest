# Automation criteria

The criteria for deciding whether a test idea is worth automating, kept manual or dropped. They
are written so that someone else can apply them without asking me anything: each criterion has
one question and fixed answers, and one rule turns the answers into a decision. Decisions by Tom
Carter; wording drafted with Claude (Claude Code), 11-02-2026. The test ideas they are applied to
are for Tixly, an invented ticket app; nothing here describes a real product.

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

## Why the rule is in this order

- **A check nobody needs is dropped first,** however easy it would be to automate.
- **A judgment can't be automated,** so a person checks it, whatever its value.
- **A changing part of a screen is checked by hand until it settles,** even when it matters: a test
  written now would need rewriting every sprint. This is the mistake in the quest's scenario.
- **Automation pays off for checks that run again and again,** so only regression checks are
  automated, and only when they matter (value 3 or 2).
- **Cost comes last.** It can only decide between automate and manual for a regression check
  that is needed, objective, stable and valuable, and even then a value-3 check is automated at
  high cost. How easy a test is to automate never decides on its own.
