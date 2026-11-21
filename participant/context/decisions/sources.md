# Decision sources

The written records the decision log cites, for the context-decision-log quest. Everything here is
made up: the demo shop in `participant/tests/playwright/demo-app/`, its invented people (Avery Lane,
product owner; Sam Ortiz, tech lead; Jordan Pike, designer; Riley Chen, support lead) and its
invented meetings, documents and work items. Written by Claude (Claude Code) for Tom Carter,
11-19-2026.

Each source is a `## ID · title, MM-DD-YYYY` section: the date it was recorded. An approval is a
line of the form
`- Approved by <approver> (area: <area>[; promotes: P-nn][; replaces: D-nn]): <what is approved>`,
in the approver's own words. The part in brackets is what the record itself says the approval
covers: its area, and any proposal it promotes or decision it replaces. A log entry quotes the
whole line exactly, and must agree with it; the checker (`participant/tools/decision-check.mjs`)
confirms both. Only plain text, bullets and tables are used here: no comments, code blocks or HTML.

## MTG-01 · Pricing kickoff, 10-05-2026

Attendees: Avery Lane, Sam Ortiz, Jordan Pike.

- Avery proposed a service fee of $2.50 per ticket, on every ticket.
- Approved by Avery Lane (area: fees): the service fee is $2.50 per ticket, charged on every ticket.
- Jordan asked whether one order should be limited to a number of tickets.
- Approved by Avery Lane (area: ticket limits): an order may have at most 6 tickets.
- Sam: amounts will be kept in whole cents so totals never round wrongly.
- Approved by Sam Ortiz (area: calculation): the order total is the quantity times (the ticket price plus the fee), worked out in whole cents.

## MTG-02 · Checkout review, 10-19-2026

Attendees: Avery Lane, Jordan Pike, Riley Chen.

- Riley asked for a way to cancel an order from the orders page; Jordan suggested one-click cancel.
- Riley: should a cancelled order give the fee back? Nobody knew yet.
- Jordan: we could waive the fee for orders of 6 or more tickets. Everyone agreed it was a good idea.
- Avery: "Let me think about the fee waiver; I'm not approving it today."

## MTG-03 · Ticket limit follow-up, 11-02-2026

Attendees: Avery Lane, Riley Chen.

- Riley reported group buyers asking for more than 6 tickets.
- Approved by Avery Lane (area: ticket limits; replaces: D-02): an order may have at most 8 tickets, replacing the limit of 6.
- Riley: is there a limit per buyer across several orders? Left open.

## DOC-01 · Ideas list (shared document), 10-12-2026

- Jordan Pike: let buyers choose their seats on a seating map.
- Riley Chen: do children need their own ticket?

## SHOP-15 · Buyer name on the review page (work item), comment of 10-21-2026

- Approved by Avery Lane (area: pages): the buyer's name is required, at most 60 characters.

## SHOP-17 · Cancel an order (work item), comment of 10-23-2026

- Approved by Avery Lane (area: pages; promotes: P-02): an order can be cancelled from the orders page, one order at a time.

## SUP-04 · Support question about currency, comment of 10-26-2026

- Approved by Avery Lane (area: pages): prices are shown in US dollars, with two decimal places.

## Work items

The made-up work items, and the decision each one rests on. The checker confirms each rests on a
decision in force, never on a proposal or a question.

| Work item | What it is | Rests on |
|---|---|---|
| SHOP-11 | Show the order total on the event card | D-01 D-04 |
| SHOP-12 | Show the service fee on the event card | D-01 |
| SHOP-13 | Limit the ticket quantity on the event card | D-07 |
| SHOP-15 | Buyer name on the review page | D-03 |
| SHOP-16 | Show the order total on the review page | D-04 |
| SHOP-17 | Cancel an order from the orders page | D-05 |
