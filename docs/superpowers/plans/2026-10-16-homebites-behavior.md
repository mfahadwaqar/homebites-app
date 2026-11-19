# HomeBites Behavior and Demo Reliability Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. Work inline with one agent, following the user's established cost preference.

**Goal:** Make availability reliable in the demo and make every customer, seller and staff decision understandable and defensible.

**Architecture:** Keep the existing Django/PostgreSQL modules. Introduce a shared read-only availability policy and a separate explicit demo-refresh service; reuse the current cart, pricing, payment and fulfillment services. Screens derive status and recovery actions from those policies rather than inventing independent rules.

**Tech Stack:** Existing Python 3.13, Django 5.2, PostgreSQL 17, server-rendered HTML/CSS/JavaScript; no new runtime dependencies.

**Spec:** `docs/superpowers/specs/2026-10-16-homebites-behavior.md`.

**Execution status:** Implemented and verified 2026-10-16. See `2026-10-16-homebites-progress.md` and `docs/milestones.md` for actual commands, results, rulings and browser evidence. The checklist below preserves the original planned steps; commit steps were deferred to preserve the existing uncommitted redesign and keep the complete local diff reviewable.

## Global Constraints

- Exactly five cuisine groups and 50 master dishes; maintain seller-specific ingredients.
- Local simulation, Bangkok time, Thai baht, free pickup, distance-based simulated delivery, 10% food-subtotal commission.
- Preserve the approved cream/forest-green/terracotta visual system and accessible interaction behavior.
- Public GET requests are read-only. Demo refresh is explicit and limited to marked records.
- Preserve historical orders, stock, account passwords and existing unrelated worktree edits.
- Plans/specification are the only files changed in this planning phase. Changes below require implementation approval.

## Review Focus

- A cutoff reached between page load and checkout: reject with an actionable message, preserve cart; Tasks 1 and 4.
- Two refreshes run concurrently or the server is restarted repeatedly: one replacement per expired marker, no duplicate stock or replenishment; Task 2.
- A seller pauses an offer/window or stock sells out: refresh must not override intent; Tasks 1–3.
- Midnight/date transitions and pre-order deadline equality: one Bangkok-time policy across browsing and purchasing; Tasks 1–2 and 7.
- Photos, mock payment labels or dashboards imply facts the records do not support: show provenance/status and reconcile arithmetic; Tasks 5–7.

## File map

| Area | Files | Responsibility |
|---|---|---|
| Availability | Create `orders/availability.py`, `orders/tests/test_availability.py`; modify `catalog/public_views.py`, `orders/services/cart.py`, `orders/services/checkout.py`, `payments/services.py` | Shared cutoff, eligibility and reason policy |
| Demo lifecycle | Create `demo/services.py`, `demo/management/commands/refresh_demo_availability.py`, `demo/tests/test_refresh.py`, `scripts/start-demo.ps1`; modify `demo/management/commands/seed_demo.py` | Explicit repeatable availability refresh and startup |
| Buyer discovery | Modify `core/views.py`, `catalog/public_views.py`, `sellers/views.py`, `templates/core/home.html`, `templates/catalog/list.html`, `templates/catalog/detail.html`, `sellers/templates/sellers/storefront.html`, related CSS/tests | Honest state, window and ingredient presentation |
| Cart recovery | Modify `orders/views.py`, `templates/orders/cart.html`, `templates/catalog/detail.html`, `orders/tests/test_cart.py`, `orders/tests/test_views.py` | Cart conflict confirmation, stale-data recovery and payment eligibility |
| Financial/order explanations | Modify `orders/pricing.py`, `orders/services/quotes.py`, `templates/orders/cart.html`, `templates/orders/detail.html`, `payments/templates/payments/pay.html`, seller dashboard and order-workflow templates | Reconciled totals, quote expiry and payment/fulfillment meaning |
| Seller/staff readiness | Create `demo/views.py`, `demo/urls.py`, `demo/templates/demo/readiness.html`, `demo/tests/test_readiness.py`; modify `config/urls.py`, seller dashboard/slot views/templates, `catalog/models.py` | Staff refresh control, seller checklist and photo provenance |
| Evidence | Create `docs/behavior-rules.md`, `docs/demo-scenarios.md`; modify `docs/local-testing.md`, `docs/classroom-handover.md`, `docs/milestones.md`, `docs/homebites-implementation-plan.md` | Decision register, coherent documentation and reproducible demonstrations |

## Phase A — Restore coherent availability first

### Task 1: One availability policy

**Interfaces:** `booking_cutoff(slot: FulfillmentSlot) -> datetime`; `bookable_stocks(*, at: datetime) -> QuerySet[ListingStock]`; `evaluate_offer(listing: FoodListing, *, at: datetime) -> OfferAvailability`. The frozen result carries `state`, `reason`, `message`, `next_action` and eligible window entries, each with slot, cutoff and remaining quantity. Evaluation never writes. Keep validation errors specific to the selected slot/quantity, rather than treating another open slot as permission to proceed.

- [ ] Add `test_availability.py` cases for standard cutoff = end minus 30 minutes, preorder deadline, exact equality, ended/inactive/wrong-seller slots, zero/missing stock, held stock and public-listing/seller gates. Assert standard versus preorder-only states and per-window quantities, not aggregated availability.
- [ ] Run `.venv\Scripts\python.exe manage.py test orders.tests.test_availability --noinput`; confirm failures identify missing policy.
- [ ] Implement the interfaces in `orders/availability.py`; use the shared eligibility/cutoff functions in catalogue detail/filter, cart checks, checkout and online-payment cutoff validation. Preserve database row locks and retry semantics.
- [ ] Run availability, catalogue, cart, checkout, concurrency and payment suites against isolated PostgreSQL; require all pass. Assert a stale selected slot is rejected even if another slot is orderable.
- [ ] Commit only Task 1 changes with `fix: unify order window availability rules`.

### Task 2: Explicit, safe demo preparation

**Interfaces:** `refresh_demo_availability(*, at: datetime) -> RefreshSummary`, with created/retained/paused/problem counts. A staff POST and `refresh_demo_availability` management command call this same service. Initial seeding creates identities/stock; refresh does not rerun catalogue seeding or overwrite seller terms. `scripts/start-demo.ps1` runs migration checks, refresh, then the normal dev server, stopping on errors.

- [ ] Add refresh tests: two-week time advance; retained current IDs/capacity/held/committed; preserved old order/stock associations and passwords; preserved intentional pauses and sold-out slots; malformed marker warning; and concurrent calls producing a single replacement. Use existing `DemoSlot` rows and their source stock associations, never username prefixes as ownership proof.
- [ ] Run `.venv\Scripts\python.exe manage.py test demo.tests.test_refresh --noinput`; confirm intended failures.
- [ ] Implement marker locking, cutoff-based rotation and spec schedule defaults: standard begins `at + 30 minutes`, lasts two hours; preorder is 18:00–20:00 Bangkok two calendar days ahead, deadline previous day at 18:00. Do not extend current windows or reset used stock. Reuse the service from `seed_demo` after initial identities exist. Add command and startup script with visible summaries and failure guidance.
- [ ] Run demo tests plus checkout/concurrency tests. Simulate an old confirmed order referencing an expired slot and prove refresh leaves its history and fulfillment capability intact. No live database refresh during verification without separate execution authorization.
- [ ] Commit with `fix: refresh marked demo schedules during preparation`.

### Task 3: Tell the truth before the buyer clicks

**Interfaces:** Home, catalogue and storefront consume `OfferAvailability` in bulk; dish detail uses eligible window entries. A shared template include `templates/catalog/_availability.html` renders status/reason/next action. Keep database queries bounded per page; do not evaluate every listing with individual repeated queries.

- [ ] Extend discovery/home tests: published-but-unorderable food must not be headed `Available offers`; `Accepting orders` filters only eligible stock; sold-out, closed-deadline, paused and unscheduled states differ. Assert start/end date, cutoff, Bangkok label and remaining portions appear on detail.
- [ ] Run `.venv\Scripts\python.exe manage.py test core.tests.test_health catalog.tests.test_discovery --noinput`; confirm new copy/state cases fail.
- [ ] Change heading to `Food offers`; replace `Open slot` with `Accepting orders`; show concise badges on cards and explicit reasons on detail. Rename `Choose a collection window` to `Choose a fulfillment window` so delivery is included. Show both standard/preorder semantics and actual dates; keep browsing and ingredients available for closed listings, with an alternatives link.
- [ ] Verify backend tests plus browser screenshots at 1440px and 390px. Check one orderable dish and each unavailable state. No purchase control may promise instant preparation or invent the next opening. Check query counts stay bounded as the page fills.
- [ ] Commit with `feat: explain food availability throughout discovery`.

## Phase B — Make the entire purchase understandable

### Task 4: Cart conflicts and stale selections have a recovery path

**Interfaces:** Keep `add_to_cart(..., replace=False)`; use its existing explicit replacement mechanism through a CSRF-protected confirmation form. Extend `cart_detail` with validation issues generated by the policy/services, not copied template checks. Preserve items when blocked.

- [ ] Add tests for different seller/window confirmation, cancel-without-change, affirmative replacement, expired selected window, insufficient portions and changed ingredients/price. Assert no silent replacement and no checkout with stale acknowledgement.
- [ ] Run `.venv\Scripts\python.exe manage.py test orders.tests.test_cart orders.tests.test_views --noinput`; confirm missing recovery behavior fails.
- [ ] Implement a reviewable proposed replacement state and form, actionable stale-cart messages and clear one-kitchen/window copy. Display selected window and booking deadline; explain cart contents are not reserved. Show only compatible fulfillment/payment choices. Ingredient changes require revisiting the seller's current ingredient list before acknowledgement.
- [ ] Exercise buyer sign-in → dish → cart, conflicting kitchen → cancel/replace, then time/stock change → recover. Run checkout/concurrency tests to preserve authoritative validation and idempotency.
- [ ] Commit with `feat: add explicit cart conflict and expiry recovery`.

### Task 5: Explain totals, payment and order progress

**Interfaces:** Use existing `calculate_totals`, `DeliveryEstimate`, `DeliveryQuote.expires_at`, payment methods and `OrderStatusEvent`; keep payment and fulfillment display separate. Add `orders/presentation.py` for shared labels/next-actor copy if multiple views need it; no invented state transitions.

- [ ] Add assertions for the exact ฿200 food + ฿40 delivery example: customer ฿240, commission ฿20, seller food earnings ฿180. Test compatible payment choices, 10-minute quote expiry, 15-minute-or-cutoff hold, failed-payment retry eligibility, seller rejection/refund and post-completion review links.
- [ ] Run pricing/quote/payment/workflow suites; confirm any new missing presentation assertions fail.
- [ ] Present fees and selected fictional locations with the configured calculation, a concise estimate explanation and quote expiry/recalculate action. Show online hold expiry and expected next actor. Use existing accept/reject/complete states truthfully; do not label them live courier tracking. Reconcile seller figures with completed settled orders; retain reasons for rejection/cancellation/refund.
- [ ] Browser-test standard pickup + cash and preorder delivery + mock payment through seller acceptance/completion. Include payment failure/retry and expired-quote recovery. Verify buyer, seller and staff permissions remain enforced by the existing services.
- [ ] Commit with `feat: explain checkout totals and order responsibilities`.

## Phase C — Make the demo defendable and repeatable

### Task 6: Seller readiness, staff controls and honest content

**Interfaces:** Staff-only `/demo/readiness/` GET displays a read-only report; POST refresh calls Task 2's service with CSRF checks and summarizes actual changes. Seller readiness is derived from approval, published/ingredient-reviewed offers, schedule and capacity. Seeded account limitations remain explicit.

- [ ] Add readiness tests for anonymous/nonstaff rejection, GET with no writes, CSRF-protected POST refresh, incomplete demo associations and paused/sold-out preservation. Add ingredient/photo tests for seller-image priority and vegetarian versus vegan fallbacks; assert no egg-based image is selected for a vegan offer.
- [ ] Run `.venv\Scripts\python.exe manage.py test demo.tests sellers.tests catalog.tests --noinput`; confirm the new readiness/provenance assertions fail where applicable.
- [ ] Add a seller checklist linking to the exact missing setup step, empty-state explanations and staff refresh report. Audit photo labels on home/cards/detail/storefront; label generic imagery explicitly instead of suggesting exact food. Update neutral review labels and role navigation. Keep actual seeded sellers' unusable passwords; document a separate fictional seller walkthrough.
- [ ] Browser-test seller draft → ingredients review → publish → slot → stock, plus staff refresh and unauthorized access. Confirm each intentionally incomplete state has a reason and an actionable link; audit all visible controls against a real route and permitted action.
- [ ] Commit with `feat: add demo readiness and seller setup guidance`.

### Task 7: Product reasoning audit and end-to-end acceptance

**Interfaces:** `docs/behavior-rules.md` is the decision register: rule ID, user question, rationale, source-of-truth service, screens and test/scenario. `docs/demo-scenarios.md` gives reproducible setup, actors, actions, expected result and recovery for each journey. These describe implemented behavior, not aspiration.

- [ ] Record the current defects and proposed rules from the spec; audit every navigation item, form, status, empty state and monetary label. Mark unverified areas explicitly. Correct outdated original-plan claims such as `implementation has not started`, superseded palette/runtime assumptions and any unsupported capabilities.
- [ ] Cover clean setup, repeated restart, two-week absence, Bangkok midnight, exact cutoff, concurrent last-portion checkout, price/ingredient change, sold out, deliberate pause, invalid fulfillment/payment pairing, seller rejection, cash collection and review moderation. Use frozen/injected time and isolated PostgreSQL fixtures, not changes to the live system clock or user database.
- [ ] Run `manage.py test --noinput`, `manage.py check`, `manage.py makemigrations --check --dry-run` and `git diff --check`. Require passing relevant tests and no pending schema drift; record actual counts and dates rather than copying old evidence.
- [ ] Run desktop/mobile browser journeys with screenshots, keyboard/200% text checks and console/network checks. Demonstrate one complete standard pickup and one complete preorder delivery journey plus the recovery cases. Keep screenshots outside source; staff moderation must now be browser-verified, not only inferred from tests.
- [ ] Update startup/testing/handover instructions and the milestone ledger to distinguish the earlier technical completion from this behavior-acceptance pass. Commit with `docs: record verified marketplace rules and demo scenarios`.

## Completion gate and order of work

Implement Tasks 1 → 2 → 3 first: this resolves the present inability to order and the misleading availability copy. Then Tasks 4 → 5 → 6 connect the buying, selling and administration journeys. Task 7 is the final gate. Keep the existing dev server available during planning; restart after implementation so model/service changes are loaded.

Done means every spec acceptance criterion is backed by the rule register, tests and browser evidence. A green homepage or 50 published offers is insufficient. Any unfinished area stays named in the handover rather than being marked complete.

## Plan self-review

- Spec coverage: availability and time → Tasks 1–3; continuity → Task 2; screen meaning → Tasks 3–6; cart/fees/payment → Tasks 4–5; roles/images/trust → Task 6; acceptance/evidence → Task 7.
- Interface consistency: `booking_cutoff`, `bookable_stocks`, `evaluate_offer`, `OfferAvailability`, `refresh_demo_availability` and `RefreshSummary` are the shared interfaces. Later tasks consume them rather than redefine eligibility.
- Review-focus cases each have an owning test step. Scope stays within the simulation and existing state machine; no new courier/payment integrations or broad architecture migration.
- Diagnosis was read-only. Subsequent approved implementation restored demo availability through the tested explicit refresh; the execution ledger records the before/after counts and verification.
