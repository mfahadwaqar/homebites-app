# HomeBites — End-to-End Implementation Plan

Status: historical implementation proposal; the simulated application is implemented. For current behavior and verified evidence, use `docs/behavior-rules.md`, `docs/milestones.md` and the 2026-10-16 behavior execution ledger. Items below describe the original design and are not independent completion claims.

Current overrides: Python 3.13, Django 5.2, PostgreSQL 17 via Docker Desktop; server-rendered Django Templates with local custom CSS/JavaScript (Bootstrap was proposed but is not a shipped dependency); cream, forest-green and terracotta palette. Implemented discovery filters are keyword, country, seller-declared diet, price and accepting-orders. Rating/distance filters and a separate live courier/preparation state machine are not implemented. Explicit demo readiness/refresh and the documented seller handoff flow define the current simulation.

### Confirmed requirement update — 22 October 2026

Professor feedback adds **calories per dish** to the required product information. This supersedes any earlier wording that excluded all nutrition information. Place the value beside the seller-specific ingredients, show a defined serving size, and label the value **estimated kcal per serving**. A generic dish name or cuisine photo is not a nutrition source; do not invent values or calculate them from ingredient names alone.

Implementation update 9 November 2026: optional seller-specific kcal, serving size, source and review fields now have storage, seller entry, validation and customer display on details/cards. Complete reviewed sets display as estimated kcal; missing values remain explicitly distinct from zero. Recipe ingredient changes clear previous nutrition and seed reruns preserve seller entries. The additive migration preserved 50 listings and 1 existing order; 74 catalogue/seller tests passed. All 50 sourced recipe estimates remain pending, so the overall calorie-data requirement is not complete. Do not add an external nutrition integration or invent values. Track remaining work in `completion-week.md`.

Acceptance for that follow-up: all 50 initial dishes retain their established countries and ingredient lists; each seller offer can show a reviewed serving size with an estimated kcal value, or the explicit missing-information state; no unsupported nutrition or dietary claims. Verify the populated and missing states on desktop and mobile before marking the requirement complete.

Scope: a fully simulated university project, not a commercial launch. Prepared on 3 September 2026 from the HomeBites Project Proposal Report, the revised presentation, and the subsequent discussion.

## 1. What the finished project will do

Deliver a responsive, locally runnable Django website where a customer can discover food, inspect its ingredients, order it, simulate payment, follow pickup or delivery progress, and leave a review. Sellers can publish offers for predefined dishes, schedule availability, manage orders and view sales. Administrators can approve sellers and moderate the marketplace.

The food catalogue is limited to 50 distinct dishes: 10 each from Thailand, Pakistan, Bangladesh, Nepal and India. Every published food listing must display its seller-specific ingredient list. This confirmed scope refinement takes precedence over the earlier report's open-ended catalogue wording; no additional countries or dishes are included in the initial simulation.

The application and PostgreSQL records are real. Money movement, payment providers, external location services and physical delivery are simulated. Once dependencies are installed, the demonstration must work without internet access, API keys, paid services or cloud hosting.

HomeBites is a primarily C2C marketplace, with possible small-business/B2C sellers. Its overall buyer–seller relationship is many-to-many. A single order will belong to one buyer and one seller.

### Definition of done

- All customer, seller and administrator journeys work through the browser and persist in PostgreSQL.
- The catalogue contains exactly five country groups and 50 distinct dishes, with exactly 10 dishes in each group.
- All 50 dishes have seeded food offers with visible ingredient lists; sellers choose from the predefined catalogue rather than inventing additional dishes.
- Standard orders and pre-orders both work, including quantities, dates and deadlines.
- Pickup is free; simulated delivery pricing varies with seller–customer distance.
- All four proposed payment methods are demonstrated without processing money.
- Order tracking, reviews, seller dashboards and the 10% commission example reconcile with stored orders.
- The application clearly labels simulated payments, location estimates, delivery and financial figures.
- Permission, checkout, inventory and end-to-end tests pass against PostgreSQL.
- Another student can follow the setup guide, load demo data and reproduce the demonstration.

## 2. Decisions and explicit assumptions

Rows marked confirmed reflect the report and the user's subsequent scope decisions. The remaining defaults make the implementation concrete without expanding the project; they can be adjusted before their phase begins.

| Decision | Implementation choice |
|---|---|
| Project type — confirmed | Fully simulated university prototype; no live launch planned. |
| Technology — confirmed | Django/Python, HTML/CSS/Bootstrap/JavaScript and PostgreSQL. |
| Marketplace scope — confirmed | Bangkok-wide positioning; standard orders plus pre-orders; pickup plus distance-based delivery. |
| Food catalogue — confirmed | Exactly 50 distinct dishes: 10 each from Thailand, Pakistan, Bangladesh, Nepal and India; no other countries for now. |
| Ingredient visibility — confirmed | A required, readable ingredient list on every published seller listing and its food-detail page. |
| Calories per dish — confirmed 22 October 2026 | Estimated kcal, serving size, source and review storage/form/display implemented 9 November. Reviewed values for all 50 initial offers remain pending. No fabricated estimates. |
| Seller catalogue workflow | Sellers choose predefined dishes and manage their own ingredient lists, descriptions/images, prices, quantities and availability. They cannot create new master dishes or countries. |
| Checkout default | One seller and one fulfillment time slot per order; multiple food items allowed. |
| Accounts default | Every user can buy; an approved seller profile adds selling capabilities to the same account. |
| Storefront default | One storefront per seller account. |
| Language and currency | English interface first; Unicode content supported; Thai baht with two decimal places. |
| Time handling | Display Asia/Bangkok time; store timezone-aware timestamps. |
| Administration | Use Django Admin with safe workflow actions; do not build a separate custom administration application. |
| Location integration | A local catalogue of sample Bangkok locations and coordinates; no external geocoding or routing requests. |
| Commercial features | Configurable 10% food-subtotal commission; no subscriptions, featured-listing billing or seller payouts. |
| Presentation and appearance | Use the deck's cream, purple and orange brand direction in an accessible responsive website. |

Single-seller checkout does not make the marketplace one-to-one: buyers can place separate orders with different sellers, and each seller can serve many buyers.

Country identifies the dish's demo cuisine grouping, not the seller's nationality or the delivery destination. All selling and delivery scenarios remain based in Bangkok. The 50-dish limit applies to distinct catalogue dishes, not portions, orders or the number of seller offers for the same dish.

## 3. Functional scope and screens

### Customer experience

1. Home page explaining the concept and clearly identifying the project as a demo.
2. Registration, login, logout, profile editing and password reset using a local email preview.
3. Marketplace with keyword search, pagination and filters for the five country/cuisine groups, dietary category, price, seller rating, availability and demo location/distance.
4. Food details showing the predefined dish name, country/cuisine, description, image, seller-specific ingredients, price, seller, available quantity, order type, available time slots and pre-order deadlines. Ingredients must be readable before adding the item to the cart or checking out.
5. Public seller storefront showing listings, average rating, completed-order count and reviews.
6. Persistent signed-in cart with quantity editing and clear handling of seller/time-slot conflicts.
7. Checkout with pickup/delivery, location selection, transparent totals and payment choice.
8. Mock payment screen, order confirmation, order history and an order-status timeline.
9. Review form available only after an eligible completed order.
10. Report-listing or report-seller form for administrator review.

### Seller experience

1. Seller application and approval status.
2. Storefront profile, sample pickup location and fulfillment preferences.
3. Select one of the 50 predefined dishes to create/edit/archive a seller listing, upload an image and maintain the ingredients used in that seller's version. Ingredient entry is required before publication.
4. Standard-order and pre-order time slots, quantities and deadlines.
5. Incoming orders, order details and permitted status actions.
6. Current and historical orders, with quantities needed for each pre-order slot.
7. Dashboard showing completed food sales, meals sold, commission, estimated seller earnings and average rating.

### Administrator experience

1. Review/approve/reject/suspend seller profiles.
2. Manage users, dietary categories and seller listings; maintain the approved 50-dish catalogue and its default ingredient data within the five-country scope. Adding countries or expanding the dish count requires a separate scope change.
3. Inspect orders, payment simulations, reviews and reported content.
4. Resolve reports with a reason and an audit record.
5. Manage labelled demo locations and delivery-pricing settings.
6. Use a staff-only demo console for loading scenarios and simulating delivery events.

Ordinary seller actions and administrator/demo actions must use the same order and payment services so the demo cannot silently bypass business rules.

## 4. Technical architecture

Use one Django application deployment with small domain modules, server-rendered templates, and JavaScript only where it improves interaction. A separate React frontend, REST API application, microservices, Redis, Celery, WebSockets and a mobile application are not required.

```text
Browser: Django Templates + HTML/CSS + Bootstrap + JavaScript
                             |
                    Django views and forms
                             |
         Accounts | Catalog | Orders | Reviews | Dashboards
                             |
              Pricing and simulation services
                             |
                        PostgreSQL
```

### Runtime choices

- Python 3.12, latest compatible patch at project setup.
- Django 5.2 LTS, latest available security patch within that series. This is a deliberate stable baseline, not a claim that 5.2 is the newest Django version. Python 3.12 is supported. [Django release documentation](https://docs.djangoproject.com/en/5.2/releases/5.2/)
- PostgreSQL 17 with a supported patch release; use the same major version for development and testing. [PostgreSQL version support](https://www.postgresql.org/support/versioning/)
- Bootstrap 5.3 compiled CSS/JavaScript stored locally, together with local fonts and images, so the demo does not depend on CDNs. [Bootstrap download documentation](https://getbootstrap.com/docs/5.3/getting-started/download/)
- Django's test runner for unit/integration tests; browser automation for complete user journeys.
- Django's local email backend for password-reset demonstrations; no email service account.
- PostgreSQL installed locally by default. A Docker-based setup may be documented as an alternative if Docker is already available, but must not become a prerequisite without agreement.

Pin and record the exact dependency versions during setup. Do not install dependencies or start building as part of this planning task.

### Proposed project structure

```text
homebites/
  manage.py
  config/                  Settings, project routes, WSGI entry point
  accounts/                Authentication, customer profiles, addresses
  sellers/                 Seller profiles, approval and dashboard
  catalog/                 Food, categories, availability and stock
  orders/                  Cart, checkout, reservations, order workflow
  payments/                Mock payment attempts and simulated refunds
  fulfillment/             Demo locations, distance, pricing and delivery
  reviews/                 Ratings, reviews and reports
  demo/                    Seed commands, mock scenarios, demo controls
  templates/               Shared and domain-specific templates
  static/                  Local CSS, JavaScript, Bootstrap and assets
  tests/e2e/               Browser-level acceptance tests
  docs/                    Setup, design, testing and demonstration guide
```

Keep workflow calculations in explicit service functions and make views/forms call them. Do not scatter stock changes, commissions or state transitions across templates, signals and administrator callbacks.

## 5. Data model and relationships

### Core relationships

```text
User (buyer) 1 ---- many Order many ---- 1 SellerProfile
User        1 ---- 0..1 SellerProfile
Seller      1 ---- many FoodListing
Country     1 ---- 10 Dish (fixed demo catalogue)
Dish        1 ---- many FoodListing
Seller      1 ---- many FulfillmentSlot
Order       1 ---- many OrderItem
Order       1 ---- many PaymentAttempt
Order       1 ---- 0..1 Review
```

Orders are the transaction records connecting buyers and sellers. A separate buyer–seller many-to-many table is unnecessary unless a future feature, such as following sellers, requires it.

| Entity | Key responsibilities and fields |
|---|---|
| User | Custom Django user, username, email, display name, active/staff permissions. |
| SellerProfile | Unique user relation, storefront name, description, approval status, location and pickup/delivery preferences. |
| Address | Owner, label, fictional address text and selected demo location/coordinates. |
| DemoLocation | Sample location label, city, latitude/longitude and active status; no real personal address required. |
| Country | Five fixed catalogue groups: Thailand, Pakistan, Bangladesh, Nepal and India. This is cuisine grouping, not a seller/delivery address. |
| Dish | Stable catalogue identifier, country, canonical dish name, default description/image and representative default ingredients. Exactly 10 predefined dishes per country. |
| DietaryTag | Administrator-managed dietary labels; listings can have multiple tags. Country and dietary labels are separate concepts. |
| FoodListing | Seller, required Dish reference, seller description/image, price, required seller-specific ingredient list, dietary tags and published/archived status. Canonical dish name and country are derived from Dish. |
| FulfillmentSlot | Seller, standard/pre-order type, available start/end time, pre-order deadline and permitted fulfillment methods. |
| ListingStock | Listing plus slot, total capacity, held quantity and committed quantity. One record per listing/slot pair. |
| Cart / CartItem | Buyer, selected seller/slot, food stock references and quantities. Cart contents do not reserve stock. |
| DeliveryQuote | Buyer/seller/location, simulated distance, tariff version, fee and expiry. |
| Order | Buyer, seller, slot, fulfillment method, status, payment summary, totals and immutable location/pricing snapshots. |
| OrderItem | Listing reference plus snapshots of dish name, country, seller-specific ingredients, unit price, quantity and line total. |
| InventoryReservation | Order item, quantity, held/committed/released state and hold expiry. |
| PaymentAttempt | Order, method, amount, mock reference, idempotency identifier and payment state. |
| OrderStatusEvent | Previous/new state, acting user, timestamp and optional reason. |
| Review | Unique order relation, rating from 1–5, comment and moderation state; buyer/seller derived from the order. |
| ContentReport | Reporter, exactly one target listing/seller, reason, resolution and administrator. |

Order and item snapshots preserve history if a seller changes a price, ingredient list, address or listing. Archive referenced listings instead of removing historical order data. Validate that order items, slots and listings all belong to the same seller.

Keep ingredients simple: a validated JSON list of nonempty ingredient names is sufficient for this simulation. Copy a dish's default ingredient list into a new seller listing as an editable starting point; the seller must review it before publishing. Changing the master defaults must not silently alter existing seller ingredients or historical orders. Ingredient quantities and recipe instructions are not required. The October 2026 calorie requirement adds serving-size and estimated-kcal information; automated nutrition calculations remain outside scope.

Enforce the five-country/50-dish scope through a versioned seed manifest, catalogue validation and restricted administrative forms; ordinary database uniqueness constraints alone do not enforce the total count. The seed manifest must contain exactly 10 distinct catalogue identifiers per country. Seller listing count may grow only by offering existing catalogue dishes, not by expanding the master catalogue.

Create the custom user model before the first migration, and use `AUTH_USER_MODEL` in relationships. [Django custom-user guidance](https://docs.djangoproject.com/en/5.2/topics/auth/customizing/#using-a-custom-user-model-when-starting-a-project)

Add uniqueness/check constraints for duplicate reviews, stock records, checkout identifiers, positive quantities, valid ratings and nonnegative money/stock. Add indexes for catalogue filtering, seller/status order queues, deadlines and order history.

## 6. Business rules that must be implemented consistently

### 6.1 Identity and permissions

- Unauthenticated users may browse but must sign in before keeping a cart or checking out.
- A user may buy and sell with the same account, but may not order from their own storefront.
- Only approved, active sellers may publish listings or accept new orders.
- A seller can only edit their listings and process their orders; buyers only see their own private order data.
- Seller suspension stops new sales but does not delete existing orders. Staff handle outstanding orders through explicit recorded actions.
- Check ownership and permissions on the server, including asynchronous requests; hiding a button is not authorization.

### 6.2 Catalogue, quantities and pre-orders

- Restrict dish selection to the approved 50-dish catalogue. Select the exact dish names and representative ingredient lists during P2; do not add extra countries or treat the 50-dish scope as merely a minimum.
- Seed one initial seller offer for every dish. More than one seller may offer the same catalogue dish with different ingredients, prices and availability; those offers do not count as new dishes.
- Require a nonempty, human-readable ingredient list before a seller can publish a listing. Display the seller's actual demo recipe ingredients, not an unreviewed generic list based solely on the dish name.
- Show country/cuisine on food cards and the full ingredient list on food details before purchase. Keep dietary tags seller-provided; do not automatically infer them from a country or dish name.
- Store ingredient snapshots on order items. If the ingredient list changes while a buyer is checking out, show the updated list and require reconfirmation before placing the order.
- Standard orders use an active selling/fulfillment slot; pre-orders select a future slot with a deadline.
- A pre-order deadline must precede fulfillment, and checkout must reject an expired deadline even if the page was opened earlier.
- An order contains one seller, one slot and one fulfillment method. Different sellers or incompatible slots require separate checkouts.
- Adding a conflicting item explains the restriction and asks the buyer whether to replace the cart; never silently discard their cart.
- Recheck seller approval, catalogue membership, listing publication, ingredient version, price, stock and timing during checkout.
- Do not permit capacity to fall below already held/committed quantities or change committed order snapshots.
- Display deadlines and pickup/delivery windows in Bangkok time.

### 6.3 Inventory and duplicate submissions

- A cart does not hold stock. Creating an online-payment order creates a temporary reservation; a successful simulated payment commits that reservation.
- For cash methods, stock is committed when the order is submitted, while payment remains due.
- Use a configurable 15-minute payment hold as an initial demo default, capped by the relevant pre-order deadline or standard selling-window end.
- A failed, abandoned or expired attempt releases held stock once. A cancelled/rejected eligible order releases committed stock once.
- Unaccepted orders cannot remain pending beyond their fulfillment window; closing them releases stock and simulates a refund if necessary.
- Lazy expiry checks before relevant stock/checkout operations plus an explicit cleanup command are sufficient for the local demo. No always-on task queue is required.
- Make checkout, payment results and cancellation idempotent: repeating a request must not create a second order, charge or inventory change.
- Perform stock changes in a database transaction with row locking in a consistent order; test simultaneous attempts to buy the last portion. [Django transactions](https://docs.djangoproject.com/en/5.2/topics/db/transactions/), [Django row-locking reference](https://docs.djangoproject.com/en/5.2/ref/models/querysets/#select-for-update)

### 6.4 Simulated location and delivery pricing

The report describes location conversion and approximate travel distance. The fully simulated implementation will demonstrate that interface without claiming to calculate an actual road route.

1. The local location service resolves a selected sample Bangkok address to stored coordinates.
2. A distance service calculates straight-line distance from the coordinates.
3. A clearly labelled simulation applies a configurable route multiplier to produce an estimated demo travel distance. A default multiplier of 1.3 is a project assumption, not a measured Bangkok road factor.
4. The pricing service applies the configured demo tariff.
5. Checkout displays the distance, delivery fee and the label “Simulated distance and delivery charge.”

Demo defaults, explicitly not market rates:

```text
simulated_distance_km = straight_line_km × 1.3
pickup_fee = 0
delivery_fee = ฿30 + (฿5 × simulated_distance_km)
```

Round the displayed distance to two decimals and use that same quoted distance for fee calculation; round money to two decimals. Test zero distance, fractional distance and invalid coordinates. If location resolution fails, ask the customer to select a supported demo location; do not silently quote zero delivery cost.

The initial catalogue contains examples across Bangkok, not five operational zones. Staff can add more demo locations. Do not impose a campus boundary or an arbitrary maximum delivery radius. These sample locations demonstrate functionality, not verified citywide logistics coverage.

Use an address selector and seller/customer location summary first. A locally bundled illustrative map may enhance the interface, but accurate live basemaps, geocoding and routing are not acceptance requirements. No public mapping API should be called by default.

Quotes are stored server-side and expire after a configurable 10-minute demo interval. A location, cart, seller or tariff change requires a new quote. Expiry or a changed total must be shown to the user for reconfirmation before an order is created.

### 6.5 Totals and commission

Calculate all money on the server with decimal arithmetic, two decimal places and a consistent rounding rule.

```text
food_subtotal = sum(unit_price × quantity)
commission = round(food_subtotal × 0.10, 2)
seller_food_earnings = food_subtotal − commission
customer_total = food_subtotal + delivery_fee
```

Example: ฿500 food + ฿50 simulated delivery = ฿550 customer total; ฿50 platform commission and ฿450 seller food earnings. The delivery fee is separate and is not commission revenue or seller food revenue.

The 10% rate is configurable and stored on each order. Count commission and earnings only for completed, simulated-paid/cash-collected orders. Exclude failed, cancelled, rejected and refunded orders. Dashboard amounts are illustrative records, not payouts, cash balances or escrow.

### 6.6 Simulated payments

| Method | Demo behavior |
|---|---|
| PromptPay | Display an unmistakably fake payment reference/QR illustration with success, failure and pending scenarios; no real bank identifier. |
| Credit/debit card | Display a mock gateway with scenario controls; never request a real card number, expiry date or security code. |
| Cash on delivery | Available only for delivery orders; seller/staff records simulated collection at delivery. |
| Cash on pickup | Available only for pickup orders; seller/staff records simulated collection at collection. |

Payment states: pending, succeeded, failed, cash-due, cash-collected and simulated-refunded. Keep these separate from order-fulfillment states. Payment success does not itself mean the seller has confirmed or completed the order.

Mock result actions must verify the current user owns the attempt, the expected amount matches the order, the order is still payable and the result has not already been applied. A late success after reservation expiry must not resurrect the order or oversell stock. Retrying a failed payment requires fresh stock/timing validation.

No real payment gateway, webhook endpoint, payment account, escrow, settlement or refund transaction is in scope.

### 6.7 Order lifecycle

Preserve the report's two main workflows:

```text
Delivery:
Pending → Confirmed → Preparing → Ready → Out for Delivery → Delivered → Completed

Pickup:
Pending → Confirmed → Preparing → Ready for Pickup → Completed
```

- Seller confirmation requires either a successful simulated online payment or a valid cash-due selection.
- Sellers handle confirmation, preparation and readiness; the owning seller or staff can record clearly labelled simulated delivery events.
- Buyers confirm receipt/collection only at the eligible final stage; staff may complete a demo order with an audit reason.
- Completion requires simulated payment success or recorded simulated cash collection.
- Buyer cancellation is allowed while Pending. Sellers can reject/cancel Pending or Confirmed orders before preparation, with a reason. Staff follow the same allowed transitions.
- Cancelled, Rejected and Expired are terminal exception states. No arbitrary backward transitions or status skipping.
- Simulate refunds for prepaid orders cancelled/rejected before preparation. Advanced post-completion refunds and disputes are outside the prototype.
- Append a timestamped status event for every valid transition. Show the customer a timeline; do not imply live rider GPS tracking.

### 6.8 Reviews and dashboards

- Only the buyer of a Completed order can review its seller, once per order.
- Reject out-of-range ratings, duplicate reviews and reviews by other users.
- Moderated/hidden reviews do not contribute to the public rating; show review count and a clear “No reviews yet” state.
- Seller sales are completed food subtotals, meals sold are completed item quantities, and seller earnings subtract the recorded commission.
- Display pending orders/pre-order commitments separately from completed sales.
- Aggregation filters must avoid double-counting when joining orders, items and reviews.

## 7. Implementation phases and completion gates

Each phase includes working UI, backend logic and its relevant tests. Do not postpone all integration or testing until the end.

| Phase | Work package | Evidence required before completion |
|---|---|---|
| P0 — Project setup | Confirm application directory, inspect any existing code, record assumptions, pin dependencies and document local PostgreSQL setup. | Reproducible environment; no existing files overwritten; scope checklist recorded. |
| P1 — Foundation and accounts | Scaffold Django, configure PostgreSQL, create the custom user before migrations, add authentication/profile screens and base Bootstrap layout. | Fresh migrations pass; registration/login/logout/profile/password-reset preview work; protected views reject anonymous access. |
| P2 — Sellers and catalogue | Seller application/approval, storefronts, the five-country/50-dish seed manifest, default and seller-specific ingredients, listings/images, fulfillment slots and quantities. | Exactly 10 dishes per country; all 50 have initial offers and ingredients; no out-of-catalogue dishes; unapproved seller cannot publish; seller A cannot edit seller B; both order types work. |
| P3 — Discovery and cart | Search, five-country filters, dietary/price/availability filters, pagination, ingredient-visible food/storefront details and signed-in cart. | Country filters use the correct catalogue group; ingredients are readable before purchase; cart persists; seller/slot conflicts are explained; quantities are validated. |
| P4 — Locations and prices | Local location service, simulated distance, delivery quotes, free pickup and pricing summaries. | Offline quotes work; changed locations change delivery prices; pickup stays zero; expired/invalid quotes are handled. |
| P5 — Reliable checkout | Order/item and ingredient snapshots, transactional stock reservations, deadline checks, duplicate-submit protection and confirmation page. | One order per submission; simultaneous last-item purchases cannot oversell; changed ingredients/price/stock/deadline require review or correction. |
| P6 — Payment and fulfillment | All mock payment methods, retry/expiry, cash collection, seller order queue, pickup/delivery lifecycle and customer timeline. | Standard pickup and pre-order delivery journeys complete; invalid transitions fail; cancellation/refund simulations release stock once. |
| P7 — Reviews and administration | Eligible reviews, seller statistics, category/user/listing management, report handling and audit events. | One review per completed order; aggregates reconcile; report resolution and moderation are recorded. |
| P8 — Demo experience and quality | Demo scenarios, responsive polish, accessibility, validation messages, local assets and security/concurrency regression testing. | Every scenario works without internet; no third-party requests; key screens usable on mobile and desktop; all critical tests pass. |
| P9 — Packaging and handover | Local start/seed/check instructions, demo accounts, database backup/restore exercise, diagrams, test evidence and presentation walkthrough. | Clean setup on a second environment or fresh database; complete demonstration reproducible from documentation. |

Order of execution: P0 → P1 → P2 → P3 → P4 → P5 → P6 → P7 → P8 → P9. Tests grow with every phase. Do not implement future monetization or live integrations during these phases.

### Suggested implementation task boundaries

Work in focused increments such as “seller approval and permission tests,” “pre-order slot validation,” or “checkout concurrency.” Avoid a single uncontrolled request to implement every feature at once. After each increment, record what changed, how it was checked and any remaining limitation.

No deadline has been supplied, so this plan intentionally uses completion gates rather than a promised calendar schedule.

## 8. Test and acceptance plan

### Automated checks

- Model and service tests: five-country/50-dish catalogue validation, ingredients, fees, commission, money rounding, deadlines, stock constraints and state transitions.
- View/form tests: login requirements, ownership, seller approval, mandatory ingredient entry, restricted dish selection, country filtering and valid/invalid forms.
- PostgreSQL transaction tests: two customers buying the last portion, duplicate checkout, repeated payment results, simultaneous cancellation/confirmation and expiry cleanup.
- Browser tests: customer purchase, seller fulfillment, administrator approval/moderation, review submission and responsive navigation.
- Migration tests: a clean database builds successfully; no missing migrations remain.
- Offline check: required screens and assets make no requests to payment, mapping, email, font or CDN services.

### Required acceptance scenarios

1. One seller sells to two different buyers; one buyer orders from two different sellers in separate orders.
2. A seller account also purchases from another seller, but cannot purchase its own food.
3. Standard order, free pickup, cash-on-pickup simulation, completion and review.
4. Pre-order, delivery quote, PromptPay simulation, seller fulfillment and completion.
5. Mock card success, failure, retry, pending state and reservation expiry.
6. Cash-on-delivery unavailable for pickup; cash-on-pickup unavailable for delivery.
7. Pre-order just before/at/after the deadline, using a controllable test clock.
8. Two customers request the last portion; exactly one succeeds.
9. Double-clicking checkout and repeating a payment result do not duplicate money or stock changes.
10. Buyer modifies a submitted price/fee/owner identifier; the server ignores/rejects the tampering.
11. Wrong buyer/seller attempts to access an order, address or listing; access is denied.
12. Seller updates a listing price/ingredients/address after purchase; the existing order retains its original snapshots.
13. Cancellation/rejection refunds simulated payments and restores inventory once, without creating commission revenue.
14. Out-of-stock food, missing images, empty search results and invalid demo locations show usable feedback.
15. Review before completion, a duplicate review or a review by another buyer is rejected.
16. The ฿500 food-order example produces ฿50 commission and ฿450 seller earnings, with delivery separate.
17. Dashboard totals reconcile with completed orders without including cancelled or pending sales.
18. Seeded pre-orders use dates relative to the seed command, so the demonstration does not become stale.
19. The seed manifest and database contain exactly 50 distinct dishes: 10 each for Thailand, Pakistan, Bangladesh, Nepal and India, with no sixth country.
20. Every seeded dish has an initial seller offer and a readable ingredient list on its detail page; publication without ingredients is rejected.
21. A seller cannot submit an unknown dish identifier or change the dish's canonical country/name to introduce an out-of-scope dish.
22. Two sellers offer the same dish with different ingredients; each listing shows its own ingredients and the master catalogue still contains 50 dishes.
23. An ingredient change during checkout prompts reconfirmation; a subsequent change does not rewrite a placed order's ingredient snapshot.
24. Rerunning the seed command does not duplicate countries, dishes or initial seller listings, or overwrite seller-edited ingredients.

### Security and privacy baseline, even for a demo

Use Django password hashing, CSRF protection, template escaping, server-side validation and object ownership checks. Add reasonable login throttling and safe image-upload size/type validation. Use fictional identities and addresses in seed data, avoid logging passwords or sensitive form contents, and exclude secrets and uploaded data from version control.

Bind the default development server to localhost; do not enable a public tunnel or public hosting. These measures do not certify the project for production. A future public deployment would require a separate review against the [Django deployment checklist](https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/).

## 9. Demo data and final presentation walkthrough

Seed several fictional customer accounts, approved and pending sellers, multiple Bangkok sample locations, standard/pre-order slots, and orders in different states. Suggested account volume remains 5 sellers and 8 buyers. The required food dataset is exactly 50 distinct dishes and 50 initial seller listings, one per dish, distributed among approved sellers. These are demonstration fixtures, not market-size claims.

| Country/cuisine group | Required distinct dishes |
|---|---:|
| Thailand | 10 |
| Pakistan | 10 |
| Bangladesh | 10 |
| Nepal | 10 |
| India | 10 |
| Total | 50 |

During P2, prepare a versioned catalogue manifest with stable dish identifiers, country, dish name, description, local image reference, representative ingredients and initial seller/price assignments. Use representative simulated recipes rather than claiming a single universal recipe for a dish. Every initial listing must have reviewed ingredients, and the final seed dataset must make all 50 dishes discoverable. Ingredient quantities and automated nutritional analysis are unnecessary. The October 2026 requirement separately calls for reviewed estimated kcal with serving size; see the pending follow-up above.

Use additional seller offers for existing dishes only when a test or demo scenario needs them; such offers must not expand the 50 distinct dishes. Seed operations must not overwrite user-edited listings or ingredient lists. Additional countries and unrestricted seller-created dishes are deferred unless the user changes the scope.

Include an idempotent seed command and a separately guarded reset command. Reset must require explicit confirmation and refuse any database not positively identified as the HomeBites demo database. It must never delete unrelated files or databases. Back up any user-entered demo records before a destructive reset.

The final classroom walkthrough should demonstrate:

1. Administrator approves a new seller.
2. Seller selects dishes from the predefined catalogue, reviews/edits ingredients, and publishes a standard offer and a pre-order offer with quantities and a deadline.
3. Customer browses the five country/cuisine groups, filters food and reads the selected seller's ingredient list before ordering.
4. Customer selects a sample location and sees the delivery fee; switches to pickup and sees the fee become zero.
5. Customer completes a mock payment and receives an order number.
6. Seller advances the order through the correct pickup or delivery stages.
7. Customer completes the order and leaves a review.
8. Seller dashboard shows the sale, meals sold and commission split.
9. A second buyer/seller transaction demonstrates the many-to-many marketplace relationship.
10. One failure scenario demonstrates a declined payment, expired pre-order or out-of-stock item without corrupting data.

## 10. Handover deliverables

- Complete Django source code with dependency versions and database migrations.
- Responsive customer/seller interfaces and configured administrator screens.
- Working PostgreSQL schema and a readable relationship diagram.
- Locally bundled static assets with provenance/licensing notes where relevant.
- Seeded demo accounts, scenario data and safe seed/reset commands.
- A versioned 50-dish/five-country catalogue manifest, with representative ingredients and seller-specific ingredient data for every initial listing.
- Unit, integration, concurrency and browser tests with recorded results.
- README covering Windows-friendly setup, PostgreSQL configuration, local startup and common errors.
- Architecture/business-rules document, simulation limitations and requirement-to-test checklist.
- Short administrator/seller/customer instructions and a classroom demonstration script.
- Database backup/restore instructions tested against the demo database.

Deployment for this project means reproducible local installation and classroom demonstration. It does not include creating a domain, hosting account, public endpoint, payment account or delivery-provider contract.

## 11. Report traceability

| Report requirement | Where implemented |
|---|---|
| 4.1 — Customer, seller and administrator roles | P1, P2, P6, P7 |
| 4.2 — Listings, categories, quantities and filtering | P2, P3 |
| Subsequent user scope — five countries, 10 dishes each, visible ingredients | P2, P3, P5, P8, P9; 50 distinct dishes, predefined seller selection, ingredient display and order snapshots |
| Professor feedback — calories per dish (22 October 2026) | Nutrition storage, seller entry/validation and customer display implemented 9 November. All 50 reviewed sourced estimates remain pending. |
| 4.3 — Pre-orders and deadlines | P2, P5, P6 |
| 4.4–4.5 — Locations, distance, pickup and delivery | P4, P6; external location/physical delivery explicitly simulated |
| 4.6 — Order processing and tracking | P3, P5, P6 |
| 4.7 — PromptPay, cards and cash options | P6; all financial transactions simulated |
| 4.8 — Ratings and reviews | P7 |
| 4.9 — Seller dashboard | P6, P7 |
| 5.2 — Commission and separate delivery charges | P4, P5, P7 |
| 6 — Django, web frontend and PostgreSQL | P0, P1 and all subsequent phases |
| 7 — Complete functional prototype | P8, P9 and the end-to-end acceptance scenarios |

## 12. Explicitly excluded

Real payments/refunds/payouts, escrow, courier integrations, live rider GPS, real geocoding/routing APIs, production hosting, customer email/SMS delivery, multi-seller checkout, coupons, wallets, subscription billing, paid featured listings, recommendation AI, chat, a native mobile app, commercial demand forecasts and a campus-to-city expansion roadmap. Also excluded: additional countries, master dishes beyond the agreed 50, unrestricted seller-created dishes, ingredient stock/procurement tracking, recipe instructions and nutrition calculations.

Do not add these merely because the architecture could support them. The completion target is the report-aligned simulated prototype.

## 13. How to execute this plan in Codex

1. When implementation is requested, confirm the application folder and inspect it before creating files. This current workspace contains presentation work, not an existing HomeBites application.
2. Begin with P0/P1; preserve the report and presentation outputs.
3. Keep a phase checklist with pending/in-progress/verified status and the actual verification evidence. Do not mark a feature complete solely because code exists.
4. Make the smallest coherent change for the current phase and run its tests before continuing.
5. If a requirement is unclear, follow the explicit defaults above or ask before a material scope change. Never silently substitute SQLite, live payments or live mapping services.
6. Request approval before installing system software, exposing the app externally, deleting demo data or using any paid/external service.
7. Finish with P9's clean-setup test, full classroom walkthrough and handover documentation.

Immediate next implementation step, once requested: create the Django/PostgreSQL project foundation and account system in the agreed application directory. No application code, dependencies, database or external account has been created by this plan.
