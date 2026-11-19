# HomeBites demonstration scenarios

## Start and prepare

After initial setup (`migrate`, `seed_demo`, a classroom buyer password and a staff account), run:

```powershell
& .\scripts\start-demo.ps1
```

Visit `http://127.0.0.1:8000/`. Newly rotated standard windows start 30 minutes after preparation, last two hours and stop bookings 30 minutes before ending. Pre-orders use 18:00–20:00 Bangkok time two calendar days ahead and close the preceding day at 18:00. Existing eligible windows are retained, so their displayed dates may differ.

If the server remains running beyond its windows, sign in as staff and open `/demo/readiness/`, then use **Refresh expired demo windows**. Current sold-out and paused windows stay unchanged. This is distinct from a destructive database reset; history is retained.

## Scenario 1: Explain discovery

Browse the five cuisine groups, search for a dish, then enable **Accepting orders** under **Refine results**. Open a dish and show the seller's ingredient list, illustrative-photo label, exact fulfillment dates, cutoff and portions per window. Explain why a published recipe can remain visible when sold out, paused or closed.

Expected: the filtered list and detail agree on availability. Closed food has an explanation and an **Explore other food** link rather than an unusable ordering control.

## Scenario 2: Prepare a seller

Create a separate fictional account; use **Seller dashboard** to apply and choose a demo pickup point. Staff approves it in Django Admin. Create a draft offer from the fixed 50-dish catalogue, enter seller-specific ingredients, review them and publish. Create a standard window and a pre-order window, then set portions for the offer in each window.

Expected: the dashboard checklist explains each missing requirement. A published dish with no stock is not orderable. The slot screen shows capacity, holds, commitments and remaining portions. Seeded seller accounts cannot sign in; do not change their passwords for this walkthrough.

## Scenario 3: Standard pickup and cash

As buyer, open the fictional seller's dish, choose a standard window and one portion, then add it. Calculate the free pickup estimate; inspect total and booking cutoff; choose cash on pickup and place the simulated order. As seller, confirm and record the simulated pickup/cash handoff. Return to the buyer's order.

Expected: food total plus zero delivery; cash due is distinct from seller confirmation. Completion records simulated cash collection and makes one review eligible. Seller completed-sales totals include the order only after settlement and completion.

## Scenario 4: Pre-order delivery and failed payment recovery

Choose a pre-order window before its deadline. Select delivery to another fictional Bangkok point and calculate the estimate. Show the distance/fee formula and 10-minute expiry. Use mock card and simulate failure. Inspect the explanation and start a fresh checkout for the same dish. Choose mock PromptPay, simulate success, then let the seller confirm and record the simulated delivery handoff.

Expected: failed portions are released; a finalized failed attempt is not reused. A new successful checkout produces a new order. The paid online handoff button does not mention collecting cash. There are no financial-credential fields or real courier/GPS promises.

## Scenario 5: Conflicting cart

Add one kitchen's dish. Attempt to add another kitchen's dish or a different fulfillment window. Inspect current and proposed contents. Choose **Keep my current cart**, then repeat and choose **Replace cart with this dish**.

Expected: keep leaves the original untouched; replace happens only after explicit confirmation and clears the old estimate. A cart changed in another tab must be reviewed again before replacement.

## Scenario 6: Changed recipe or price

Keep an offer in the buyer cart. As its owner, edit price or recipe, review the ingredients and republish. Reload the buyer cart. Follow **Review current ingredients and price**, read the dish page and use its confirmation button.

Expected: checkout stays blocked until current terms are confirmed. Quantity update alone does not acknowledge new ingredients. A second edit after the review page was loaded invalidates that review token; the buyer must reopen the offer. Removing an item remains possible.

## Scenario 7: Review and staff moderation

Submit a review for a completed order. Observe it is not public yet. Staff visits `/reviews/moderation/`, approves with a reason, and reloads the public reviews page. Revisit the buyer order.

Expected: pending reviews do not inflate public ratings; approval publishes it and creates an audit event. The completed order no longer offers a duplicate review form.

## Scenario 8: Closure, sell-out and demo age

Use isolated test data for date changes and concurrency demonstrations. Do not change the Windows clock or rewrite historical live order windows.

- Exact booking cutoff: catalogue filter excludes the offer; cart/checkout/payment reject it consistently.
- Two-week absence: explicit refresh rotates expired marked slots once; old order/stock associations remain unchanged.
- Sold out: reducing available portions to zero removes ordering eligibility but retains the recipe. Refreshing a current window does not replenish it.
- Paused: deactivating a window blocks new bookings. Refresh does not undo that seller choice.
- Last portion: concurrent checkout permits exactly one order, backed by PostgreSQL locking tests.
- Quote expiry: after ten minutes, recalculating is required; changing location, tariff or cart invalidates earlier quotes.
- Payment hold expiry: a success submitted after expiry is rejected; startup, explicit staff refresh, or a new cart-add POST releases overdue reservations through the existing expiry service.

Automated command:

```powershell
& .\.venv\Scripts\python.exe manage.py test --noinput
```

Tests require PostgreSQL. Browser QA should use a disposable seeded database and fictional users rather than manipulating the classroom database. Current verification evidence is in the behavior progress ledger and milestone document.
