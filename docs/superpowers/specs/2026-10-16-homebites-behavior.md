# HomeBites behavior and explainability specification

Prepared 2026-10-16 and approved for implementation by the user's subsequent request. Implemented and verified on 2026-10-16; see the behavior execution ledger and milestone evidence. This supplements the original scope and supersedes contradictory presentation wording.

## Evidence and goal

Read-only inspection of the running database on October 16 found 50 public offers, 100 stock records, 10 active flags, but zero orderable stock rows. All five standard windows ended October 5 and all five pre-order windows ended October 7; pre-order deadlines passed October 6. Active is a seller switch, not proof that a window is still bookable. `seed_demo` can rotate expired windows, but normal `runserver` does not call it. Its current standard-order seed is tomorrow at noon, which needs explanation rather than a promise of immediate food.

The goal is a coherent demonstration where a buyer, seller, or examiner can understand what each screen means, why each action is allowed or blocked, and what happens next. Passing technical tests alone does not establish that the experience is understandable.

## Confirmed scope

- Fully simulated, local Django/PostgreSQL marketplace; no real payment, delivery, GPS, payout, or external account integration.
- Five cuisine groups, exactly 50 master dishes, 10 each from Thailand, Pakistan, Bangladesh, Nepal and India. Cuisine does not identify a seller's nationality or delivery zone.
- Bangkok-wide positioning with a limited set of labelled fictional locations for offline delivery examples.
- Standard orders and pre-orders, pickup and distance-based simulated delivery, required seller-specific ingredients.
- Many buyers and many sellers overall; one seller and one fulfillment window per cart/order.
- Existing cream, forest-green and terracotta design, accessible navigation and local image assets remain the visual baseline.

## Proposed decisions for this pass

These design defaults were approved and implemented in this behavior pass. `docs/behavior-rules.md` connects them to the current implementation and tests.

### 1. Time and availability

- All customer dates and cutoffs show Bangkok time, date, and start/end times. Use timezone-aware timestamps; tests inject a fixed `at` value rather than changing the machine clock.
- A standard order is placed without an advance-day deadline, for a displayed fulfillment window. It does not mean instant preparation. Its booking cutoff is window end minus a 30-minute preparation buffer.
- A pre-order reserves a displayed future batch and must be placed before its explicit deadline, which precedes fulfillment start. No additional standard-order buffer applies to that deadline.
- A slot is bookable only when the listing is public, seller approved and active, slot belongs to that seller and is active, cutoff is strictly later than now, fulfillment has not ended, and remaining portions cover the requested quantity. Equality with the cutoff is closed.
- Remaining portions equal capacity minus held minus committed. Adding to cart does not reserve stock; successful checkout reserves it. Stock is per dish and per window, never pooled across windows.
- One shared availability policy feeds list/detail/storefront, cart and checkout. Payment success also respects the order's hold expiry and relevant cutoff. Checkout remains authoritative and transactional.
- Show states with truthful messages: `Orderable`, `Pre-order only`, `Sold out for this window`, `Pre-order deadline passed`, `Ordering closed for this window`, `Kitchen paused`, or `No schedule published`. An unavailable listing remains browsable with ingredients and an alternative-food link.
- Where multiple windows exist, show the next eligible window and its own quantity. Do not claim ready-now, same-day or a remaining quantity unless the selected window supports it.

### 2. Demo continuity

- Refresh marked demo windows at an explicit local startup/preparation step and through a staff-only POST action. Public GET requests never create windows, replenish stock or change orders.
- Reuse an existing bookable window without extending its dates or changing used stock. Rotate only expired marked windows. Intentionally paused windows remain paused. Sold-out windows remain sold out until expiry or an explicit capacity adjustment.
- For newly created demo standard windows, start 30 minutes after refresh and end two hours after that start. For pre-orders, use 18:00–20:00 Bangkok time two calendar days ahead, with a deadline at 18:00 the preceding day. These are labelled demonstration schedules, not promises of actual kitchen hours.
- Refresh is confined to `DemoSlot` identities and their existing marked stock associations. It must not adopt arbitrary accounts or replenish user-created offers. Incomplete markers/stock cause an actionable readiness warning, not silent adoption.
- Preserve historical windows, stock, orders, snapshots and account passwords. A refresh does not cancel or move orders. Old held reservations expire through the existing expiry service, releasing inventory exactly once.
- A long-running demo can become closed after time passes. Staff sees readiness and a refresh action; buyers see truthful availability. No scheduler, Celery, frozen browser clock, or background writes are needed.

### 3. Each screen answers a question

| Surface | What it must explain | Meaningful next action |
|---|---|---|
| Home | What HomeBites offers, five cuisines, demonstration scope | Browse food or visit a kitchen |
| Catalogue | Published food versus food accepting orders | Filter `Accepting orders`, select a dish, or clear filters |
| Dish | Seller's version, ingredients, image provenance, price, availability, window and deadline | Choose an eligible window and quantity, or explore alternatives |
| Storefront | Who sells, review status, pickup point, and each offer's availability | Select food or read reviews |
| Cart | One kitchen/window, portions, no stock hold yet, pickup/delivery eligibility | Adjust items, confirm a proposed replacement, or request an estimate |
| Checkout | Exact total, selected window, fee basis, payment compatibility, pending seller decision | Place one simulated order or recover from a specific conflict |
| Payment | Explicit simulation, outcome controls, remaining hold time | Simulate success/failure or retry only while eligible |
| Order | Payment status separately from fulfillment status, timestamps and next actor | Buyer cancellation when allowed, seller decision, or eligible review |
| Seller | Approval, publication, ingredients, schedule and capacity are separate requirements | Resolve the specific missing requirement |
| Staff | Moderation, demo readiness and explicit simulation controls | Approve, resolve, or refresh with visible results |

### 4. Cart, fees and payments

- Explain the single-kitchen/window rule before a conflict. An explicit replacement control must be usable; never clear a cart merely because a different dish was clicked.
- Stale carts retain their items and explain whether a deadline, quantity, ingredient version, price or seller status changed. Require review; do not silently switch windows or accept changed ingredients.
- Pickup is free. Delivery is a local example between selected fictional Bangkok points: straight-line Haversine distance multiplied by the configured route multiplier, then base fee plus per-kilometre fee. Show the active configuration and formula in a concise explanation. It is not a real route or ETA.
- Delivery quotes last 10 minutes and must be refreshed after relevant cart/location/tariff changes. Display the expiry and a refresh action.
- Customer total is food subtotal plus delivery fee. Platform commission is 10% of food subtotal, deducted from seller food earnings rather than added as a second customer charge. Example: food ฿200 + delivery ฿40 = buyer ฿240; commission ฿20; seller food earnings ฿180. Do not call delivery a seller payout or platform profit.
- Mock PromptPay/card work for pickup and delivery. Cash on pickup is only offered for pickup; cash on delivery only for delivery. Never request actual financial details.
- Online payment holds last at most 15 minutes, capped at the booking cutoff. Cash commitment, seller approval, completion, rejection and simulated refund remain distinct events.

### 5. People, images and trust

- Every user can buy; approved sellers gain selling controls. Distinguish approval from storefront/listing readiness. Do not imply seeded seller accounts can sign in: they currently have unusable passwords. Use a separate fictional approved seller for demonstrations.
- Ingredient labels are seller declarations, not allergy guarantees. Keep seller-specific ingredients visible before ordering, and require acknowledgement when they change.
- Generic cuisine photos must not be presented as exact dish photos. Identify fallback imagery explicitly next to it; exact seller uploads take priority. Audit vegetarian/vegan fallbacks against visible contents and never use an egg-containing fallback for a vegan declaration.
- Show pending versus published reviews correctly; only eligible completed-order buyers can review. Empty ratings say `No published reviews yet`, not a fabricated rating or quality claim.
- Buyer timeline and seller actions must correspond to the existing state machine. Do not imply GPS tracking, courier assignment or preparation events that do not exist in records.
- For each blocked action provide a reason and a recovery action; do not expose internal IDs, code terminology or stack traces as explanations.

## Acceptance

1. Starting a prepared demo after a two-week absence restores eligible marked demo schedules without rewriting history or replenishing sold-out live windows.
2. A clean demo has 50 published offers with standard and pre-order choices; all remaining-stock quantities come from the database.
3. A deliberately closed, paused or sold-out scenario remains truthful and distinguishable across catalogue, dish, cart and checkout.
4. One buyer pickup journey and one delivery/pre-order journey can be demonstrated from discovery through payment, seller decision, completion and review, including one recovery case each.
5. An examiner can trace every displayed state, calculation and permitted action to a documented rule and a meaningful test or browser demonstration.
6. Existing orders, stock safety, ownership, review eligibility and checkout idempotency remain intact. No additional product features or integrations are introduced merely to make the demo look complete.
