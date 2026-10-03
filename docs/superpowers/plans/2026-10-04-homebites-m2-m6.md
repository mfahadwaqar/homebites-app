# HomeBites M2–M6 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver the simulated marketplace from approved seller offers through browsing, cart, distance quotes and reliable checkout.

**Architecture:** Keep Django server-rendered. `sellers` and `catalog` own identity and food offers; `fulfillment` owns offline Bangkok locations and pricing; `orders` owns slots, cart, inventory and transactional checkout. Views call service functions for cross-model rules. PostgreSQL is the only database.

**Tech Stack:** Python 3.13, Django 5.2, PostgreSQL 17, local HTML/CSS/JavaScript.

**Spec:** `docs/superpowers/specs/2026-10-04-homebites-design.md`; detailed rules in `docs/homebites-implementation-plan.md` sections 5–6.

## Global Constraints

- Exactly five countries and ten distinct master dishes per country; seller offers reuse those dishes.
- Every published seller offer has a reviewed, seller-specific nonempty ingredient list visible before cart and checkout.
- A buyer may also be a seller but cannot buy their own offer.
- One seller, one fulfillment slot and one method per cart/order. No silent cart replacement.
- Standard orders and pre-orders; pre-order deadline precedes fulfillment and is enforced at checkout.
- Pickup is free. Delivery is a local Bangkok coordinate simulation with no external request.
- Quote and checkout totals are calculated on the server. Commission begins at 10% of food subtotal and delivery is separate.
- M6 must prevent duplicate orders and overselling with PostgreSQL row locks and idempotency. Online payment stays pending for M7; cash orders are committed as due.
- Preserve real historical snapshots. No live provider integration, multi-seller checkout, public hosting or extra countries.

## File ownership and interfaces

- Agent 1 owns `sellers/`, `catalog/`, their templates and tests, and `catalog/data/dishes.json`. It does not edit `config/`, `orders/`, `fulfillment/` or shared templates.
- Agent 2 owns `fulfillment/`, its templates and tests. It does not edit `config/`, `orders/`, `sellers/`, `catalog/` or shared templates.
- Root owns shared configuration/templates, `orders/`, marketplace discovery integration, roadmap evidence and browser QA.
- `SellerProfile.user` is unique; `status` is pending/approved/rejected/suspended; `pickup_location` is added after both agents' apps exist.
- `Dish` references `Country`; `FoodListing` references `SellerProfile` and `Dish`, has `ingredients` JSON list, `ingredient_version`, `price`, `status`. Catalog may expose an `available` manager/queryset but checkout always rechecks.
- `DemoLocation` has stable code, label, Bangkok coordinates and active state. Pricing service accepts location records and food subtotal, returns distance/fee/tariff version, and does not depend on cart/order models.
- `FulfillmentSlot` belongs to seller, has standard/preorder type, time window, optional deadline and method flags. `ListingStock` is unique by listing/slot with capacity, held and committed counts.
- `Cart` belongs to buyer and pins seller, slot, method and location; `CartItem` stores listing, quantity, acknowledged ingredient version. `Order` and `OrderItem` snapshot all prices/ingredients/locations.

## Review focus

- Unapproved/suspended sellers cannot publish or receive a new checkout.
- Editing seller ingredients requires a buyer's explicit reconfirmation before checkout.
- Expired pre-order or incompatible slot does not silently replace the cart.
- A stale quote cannot be reused after cart, location or tariff changes.
- Concurrent checkout for the last portion yields one order and no negative stock.

---

### Task 1: Seller approval, fixed catalogue and listing ingredients (Agent 1)

**Files:** Create `sellers/`, `catalog/`, `catalog/data/dishes.json`, domain migrations, forms/views/URLs/admin/templates/tests. Do not edit shared files.

**Interfaces:** Produce `SellerProfile`, `Country`, `Dish`, `FoodListing`; `seed_catalogue` management command; seller application/listing routes under app URL namespaces.

- [ ] Write failing PostgreSQL tests for seller application/approval, ownership, fixed catalogue count, repeatable seed, distinct seller ingredients, rejected empty ingredients and seller publishing permissions.
- [ ] Run focused tests and observe RED for missing behavior.
- [ ] Implement models, initial migrations, validated fixed manifest, idempotent seed command, admin approval and seller listing forms/views/templates.
- [ ] Run focused tests, then the complete suite; record results.

### Task 2: Offline Bangkok locations and pricing (Agent 2)

**Files:** Create `fulfillment/`, migrations, services, command, tests. Do not edit shared files.

**Interfaces:** Produce `DemoLocation`, `DeliveryTariff`, `seed_locations`, `calculate_distance_km(origin, destination)`, `quote_delivery(origin, destination, food_subtotal)`, and `pickup_fee()`.

- [ ] Write failing PostgreSQL tests for stable location seed, deterministic distance, positive delivery fee, free pickup, inactive/out-of-Bangkok locations and tariff versioning.
- [ ] Run focused tests and observe RED for missing behavior.
- [ ] Implement models, seed command and pure pricing services; clearly label estimates simulated.
- [ ] Run focused tests, then the complete suite; record results.

### Task 3: Integrate apps and marketplace discovery (Root)

**Files:** Modify `config/settings.py`, `config/urls.py`, shared navigation/home; create catalogue public views/templates/tests and seller public storefront integration.

**Interfaces:** Consume Task 1/2 models; produce home catalogue link, paginated `catalog:list`, `catalog:detail`, `sellers:storefront`, country/search/price/availability filters.

- [ ] Write failing browser-oriented Django tests for 50 discoverable offers, filters, pagination, seller-specific ingredient detail, storefront and unpublished visibility.
- [ ] Run RED, implement minimal views/templates, run GREEN and complete suite.

### Task 4: Slots, stock and persistent single-seller cart (Root)

**Files:** Create `orders/` models/forms/services/views/templates/tests and migrations; add seller slot/stock management integration.

**Interfaces:** Produce `FulfillmentSlot`, `ListingStock`, `Cart`, `CartItem`, `add_to_cart`, `update_cart`, `select_fulfillment`; consume listing/seller records.

- [ ] Write failing tests for standard/preorder timing, seller/slot conflict response, quantity/stock limits, own-listing rejection, persistent cart and location/method selection.
- [ ] Run RED, implement, run GREEN and complete suite.

### Task 5: Server quote and checkout (Root)

**Files:** Extend `orders/`; integrate `fulfillment` services; migrations/tests/templates.

**Interfaces:** Produce `DeliveryQuote`, `Order`, `OrderItem`, `InventoryReservation`, `create_quote`, `checkout`, `expire_reservations`, `cancel_order`.

- [ ] Write failing tests for quote invalidation, zero pickup, 10% commission, ingredient/price snapshots, idempotency, deadline checks, stock reservation/commit/release and concurrent last-portion checkout.
- [ ] Run RED, implement transactional service with ordered row locks, run GREEN and complete suite.
- [ ] Expose review/confirmation pages; do not take real payment credentials.

### Task 6: Milestone verification and handover (Root)

**Files:** Update `README.md`, `docs/development.md`, `docs/milestones.md`; browser QA artifacts outside repository.

- [ ] Run all PostgreSQL tests, Django checks, migration consistency and repeatable seed checks.
- [ ] Exercise seller approval → seeded catalogue → detail/ingredients → cart → pickup/delivery quote → checkout in desktop/mobile browser.
- [ ] Record evidence for each M2–M6 gate and mark only gates with passing evidence complete.
- [ ] Commit reviewed implementation on `milestone/02-06-marketplace`.

## Plan self-review

Tasks 1–2 have independent file ownership and stable interfaces. Tasks 3–5 consume those interfaces sequentially. Task 6 proves end-to-end behavior. The plan excludes M7 payment result processing and later order state transitions; M6 creates the safe pending/due order foundation those milestones consume.
