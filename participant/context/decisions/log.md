# Decision log

Every decision, proposal and question about the made-up demo shop
(`participant/tests/playwright/demo-app/`), from the context-decision-log quest. The rules are in
`rules.md`; the meeting notes, documents and work-item comments each entry cites are in
`sources.md`. Everything here is invented. Decisions by Tom Carter; entries drafted with Claude
(Claude Code), 11-19-2026.

Entries are never rewritten: a change adds a new entry, and the only lines ever added to an old one
are `Became` and `Replaced by`. Check the log with `node participant/tools/decision-check.mjs`.

The **Current decisions** list below shows the decisions in force now (not replaced), each in its
approver's own words. The checker builds it from the entries; don't edit it by hand
(`node participant/tools/decision-check.mjs --write-view` writes `log.md.new` to check and move into
place). Each decision's title is its approver's own words. Work items and the decisions they rest
on are listed in `sources.md`.

## Current decisions

<!-- current-decisions: start -->
| Decision | What was approved (the approver's words) | Area | Approved by | Date | Where |
|---|---|---|---|---|---|
| D-01 | the service fee is $2.50 per ticket, charged on every ticket. | fees | Avery Lane | 10-05-2026 | MTG-01 |
| D-03 | the buyer's name is required, at most 60 characters. | pages | Avery Lane | 10-21-2026 | SHOP-15 |
| D-04 | the order total is the quantity times (the ticket price plus the fee), worked out in whole cents. | calculation | Sam Ortiz | 10-05-2026 | MTG-01 |
| D-05 | an order can be cancelled from the orders page, one order at a time. | pages | Avery Lane | 10-23-2026 | SHOP-17 |
| D-06 | prices are shown in US dollars, with two decimal places. | pages | Avery Lane | 10-26-2026 | SUP-04 |
| D-07 | an order may have at most 8 tickets, replacing the limit of 6. | ticket limits | Avery Lane | 11-02-2026 | MTG-03 |
<!-- current-decisions: end -->

## Entries

### D-01 · The service fee is $2.50 per ticket, charged on every ticket

- Status: decision
- Date: 10-05-2026
- Source: MTG-01
- Area: fees
- Approver: Avery Lane
- Approval: "Approved by Avery Lane (area: fees): the service fee is $2.50 per ticket, charged on every ticket."
- Affects: SHOP-11 SHOP-12

### D-02 · An order may have at most 6 tickets

- Status: decision
- Date: 10-05-2026
- Source: MTG-01
- Area: ticket limits
- Approver: Avery Lane
- Approval: "Approved by Avery Lane (area: ticket limits): an order may have at most 6 tickets."
- Affects: SHOP-13
- Replaced by: D-07

### D-03 · The buyer's name is required, at most 60 characters

- Status: decision
- Date: 10-21-2026
- Source: SHOP-15
- Area: pages
- Approver: Avery Lane
- Approval: "Approved by Avery Lane (area: pages): the buyer's name is required, at most 60 characters."
- Affects: SHOP-15

### D-04 · The order total is the quantity times (the ticket price plus the fee), worked out in whole cents

- Status: decision
- Date: 10-05-2026
- Source: MTG-01
- Area: calculation
- Approver: Sam Ortiz
- Approval: "Approved by Sam Ortiz (area: calculation): the order total is the quantity times (the ticket price plus the fee), worked out in whole cents."
- Affects: SHOP-11 SHOP-16

### P-01 · Let buyers choose their seats on a seating map

- Status: proposal
- Date: 10-12-2026
- Source: DOC-01
- Proposed by: Jordan Pike

### Q-01 · Do children need their own ticket?

- Status: question
- Date: 10-12-2026
- Source: DOC-01
- Asked by: Riley Chen

### P-02 · Let buyers cancel an order from the orders page

- Status: proposal
- Date: 10-19-2026
- Source: MTG-02
- Proposed by: Riley Chen
- Became: D-05
- Note: Jordan Pike's "one-click cancel" was part of the discussion; D-05 approves cancelling one order at a time, not how many clicks it takes.

### P-03 · Waive the service fee for orders of 6 or more tickets

- Status: proposal
- Date: 10-19-2026
- Source: MTG-02
- Proposed by: Jordan Pike
- Note: everyone in MTG-02 agreed it was a good idea, but Avery Lane, who approves fees, said "I'm not approving it today". Agreement is not an approval, so it stays a proposal.

### Q-02 · Does a cancelled order give the service fee back?

- Status: question
- Date: 10-19-2026
- Source: MTG-02
- Asked by: Riley Chen

### D-05 · An order can be cancelled from the orders page, one order at a time

- Status: decision
- Date: 10-23-2026
- Source: SHOP-17
- Area: pages
- Approver: Avery Lane
- Approval: "Approved by Avery Lane (area: pages; promotes: P-02): an order can be cancelled from the orders page, one order at a time."
- From: P-02
- Affects: SHOP-17

### D-06 · Prices are shown in US dollars, with two decimal places

- Status: decision
- Date: 10-26-2026
- Source: SUP-04
- Area: pages
- Approver: Avery Lane
- Approval: "Approved by Avery Lane (area: pages): prices are shown in US dollars, with two decimal places."
- Affects: none

### D-07 · An order may have at most 8 tickets, replacing the limit of 6

- Status: decision
- Date: 11-02-2026
- Source: MTG-03
- Area: ticket limits
- Approver: Avery Lane
- Approval: "Approved by Avery Lane (area: ticket limits; replaces: D-02): an order may have at most 8 tickets, replacing the limit of 6."
- Replaces: D-02
- Affects: SHOP-13

### Q-03 · Is there a ticket limit per buyer across several orders?

- Status: question
- Date: 11-02-2026
- Source: MTG-03
- Asked by: Riley Chen
