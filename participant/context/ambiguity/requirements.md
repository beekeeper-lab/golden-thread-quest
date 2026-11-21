# Tixly checkout requirements

Tixly is an invented event-ticket app. Every requirement, rule and number below is synthetic,
written for this exercise. No real product, company or person is described.

Scope: the checkout, from choosing seats to the confirmation email. Each requirement has a
stable id, so findings can cite it.

## Requirements

**CHK-01.** A buyer can hold up to 8 seats for one event in a single order. Choosing a 9th seat
shows the message "You can buy up to 8 seats per order." and the 9th seat is not held.

**CHK-02.** The seat map must load quickly.

**CHK-03.** Held seats are released 10 minutes after the hold starts if payment has not
completed. Released seats show as available on the seat map.

**CHK-04.** A buyer can apply a Tixly gift card at checkout. The gift card balance is deducted
from the order total.

**CHK-05.** Refunds are available up to 48 hours before the event starts.

**CHK-06.** After payment succeeds, Tixly sends a confirmation email within 5 minutes. The email
contains the order number, the event name, the event date and start time, and every seat number.

**CHK-07.** Checkout should feel trustworthy to first-time buyers.

**CHK-08.** A buyer can cancel an order and receive a full refund at any time until the venue
doors open.

**CHK-09.** A service fee of $2.50 per ticket is shown as its own line on the payment page,
before the buyer pays.

**CHK-10.** If a payment is declined, the buyer sees an error message.

**CHK-11.** The order total shown on the payment page must equal the amount charged, to the
cent.

**CHK-12.** The system must handle any number of buyers checking out at the same time.
