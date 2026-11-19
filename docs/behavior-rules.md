# HomeBites behavior rules

Implementation pass: 16 October 2026. These rules describe the local simulation. They are distinct from the historical implementation proposal.

| ID | User question and decision | Why | Source of truth | Verification |
|---|---|---|---|---|
| HB01 | Why can I see food that I cannot order? Published food remains browsable; availability is a separate state. | Buyers can inspect recipes without a false promise of stock. | `orders/availability.py`, `catalog/public_views.py` | Discovery tests; public browser flow |
| HB02 | When can I place a standard order? Before window end minus 30 minutes. | Leaves preparation time without pretending food is instantly ready. | `booking_cutoff`, `window_problem` | Cutoff equality and cart/checkout tests |
| HB03 | What is a pre-order? A future batch with an explicit booking deadline before fulfillment. | Sellers can plan quantities before preparing a batch. | `booking_cutoff`, `FulfillmentSlot.clean` | Preorder deadline/calendar tests; delivery browser flow |
| HB04 | How many portions remain? Capacity minus payment holds minus committed portions, for this dish/window. | A portion cannot be sold to two buyers. | `ListingStock.available`, transactional checkout | Availability, last-portion concurrency and reservation tests |
| HB05 | Does adding to cart hold food? No; checkout does. | Browsing carts must not consume all marketplace inventory. | `add_to_cart`, `checkout` | Cart no-reservation and checkout tests |
| HB06 | Why can my cart contain only one kitchen/window? One handoff, preparation schedule and fee calculation per order. | Avoids implying a courier can combine unrelated kitchens. | `add_to_cart`, replacement confirmation | Browser cancel/replace flow; revision-race test |
| HB07 | Why must I review a changed recipe or price? Prior consent applies to the old offer. | Ingredients and cost are material purchase decisions. | Signed detail-page review, version/price snapshot checks | Stale-cart, signed-token and second-change tests |
| HB08 | What does unavailable mean? No schedule, paused kitchen/window, deadline/cutoff passed, or no portions remain. | Each cause needs a different next action. | `evaluate_offer` | Availability-state tests and buyer alternatives |
| HB09 | Why did old demo windows disappear from ordering? Real dates still pass in a simulation. | An expired window cannot promise future fulfillment. | Explicit `refresh_demo_availability` | Two-week absence, repeated refresh and concurrency tests |
| HB10 | Does refreshing reset the demo? No; only expired marked windows rotate. Current sold-out stock and intentional pauses stay unchanged. | Refresh must preserve user intent and historical orders. | `DemoSlot`, `demo/services.py` | Preservation, malformed associations and refresh tests |
| HB11 | How do I start a usable demo? Run `scripts/start-demo.ps1` after first-time setup. | It starts PostgreSQL, checks migrations, releases expired holds and explicitly refreshes schedules before Django starts. | Startup script and management commands | Clean setup instructions; idempotent seed/refresh tests |
| HB12 | Why is pickup free? No delivery service is being simulated for pickup. | Clear comparison with the delivery choice. | `pickup_fee`, quote service | Quote and pickup browser journey |
| HB13 | How is delivery calculated? Haversine straight-line distance × configured route multiplier, then base fee + rate × rounded example distance. | A repeatable offline pricing demonstration without external routing claims. | `fulfillment/services.py`, `DeliveryTariff` | Pricing/quote tests; delivery quote explanation |
| HB14 | Why did the delivery estimate expire? Quotes last 10 minutes and depend on cart revision, locations and tariff. | The quoted total must describe the current selection. | `valid_quote_for_cart` | Quote change/expiry tests |
| HB15 | What do I pay? Food subtotal + delivery fee. | Commission must not be charged twice. | `calculate_totals` | Pricing tests; cart/order totals |
| HB16 | Where does the 10% go? Deducted from seller food earnings. Food ฿200 + delivery ฿40 gives customer ฿240, commission ฿20, seller food earnings ฿180. | Separates marketplace revenue examples from seller food earnings and delivery charges. | `orders/pricing.py` | Decimal arithmetic tests |
| HB17 | Which payments can I choose? Mock card/PromptPay for either method; cash only for the matching handoff type. | Cash on delivery cannot describe pickup. | `_payment_is_compatible` | Checkout compatibility tests |
| HB18 | How long is payment held? Up to 15 minutes, capped at the booking cutoff. | Payment cannot revive a closed booking or consume inventory forever. | `checkout`, `_active_hold`, `expire_reservations` | Hold cutoff, late-result and release-once tests |
| HB19 | What happens if payment fails? Portions are released; choose food again and start a fresh checkout. | A finalized failed attempt is not silently turned into success. | Mock payment service and order presentation | Failed payment/new-checkout browser journey |
| HB20 | Is paid the same as confirmed? No; the seller still accepts or rejects. | Payment readiness and kitchen acceptance are separate decisions. | Order workflow and `order_presentation` | Seller/buyer browser journeys; workflow permissions |
| HB21 | What does delivery tracking show? Stored order events and a seller-recorded simulated handoff. | There is no real courier, GPS or preparation sensor. | `OrderStatusEvent`, workflow service | Timeline and completion tests |
| HB22 | Why can't a seller publish/order yet? Approval, reviewed ingredients, published offer, eligible window and portions are separate gates. | Sellers need an actionable setup checklist. | Seller dashboard and slot UI | Seller readiness test and browser setup |
| HB23 | What counts as seller sales? Completed orders with a matching successful mock payment or recorded cash collection. | A status flag alone must not inflate sales. | Dashboard settled-payment query | Unsettled-completion and completed-sales tests |
| HB24 | Who can review? The buyer of a completed order, once; public display requires moderation. | Avoids duplicate or unverified public ratings. | Review services and order review eligibility | Review permission tests and staff moderation browser flow |
| HB25 | Are these exact food photos? Seller uploads take priority; fallback cuisine images are explicitly illustrative. | Reused cuisine imagery cannot promise an exact seller recipe. | Model image selection and photo labels | Seller-image/vegetarian/vegan fallback tests |
| HB26 | Who can refresh demo availability? Staff via a CSRF-protected POST, or the explicit local preparation command. | Browsing food must not mutate inventory or schedules. | `demo/views.py` | Read-only GET, staff permissions and CSRF tests |
| HB27 | What does Bangkok-wide mean with eight locations? Marketplace positioning is city-wide; offline examples use eight fictional points. | A finite simulation dataset is not a delivery-zone restriction. | Demo location catalogue and interface copy | Quote validation and classroom handover |

## State and action audit

- Home/cuisine links go to real catalogue filters; kitchen cards go to public storefronts. Featured offers display their current booking state rather than implying popularity or stock.
- Catalogue filters search published offers. `Accepting orders` additionally requires eligible windows and positive remaining stock. Empty results offer clear-filter or alternative-food actions.
- Dish pages expose ingredients, provenance, current price, actual windows, deadlines, quantities, pickup/delivery eligibility and the single-kitchen/window rule before adding.
- Cart updates do not silently accept changed recipes/prices. Zero removes an item. A different kitchen/window presents current/proposed contents and explicit keep/replace actions. A stale confirmation cannot overwrite another tab's changes.
- Checkout rejects stale availability, inadequate stock, incompatible payment, changed ingredients/prices and expired delivery quotes. Its disabled button is guidance; server validation is authoritative.
- Payment controls exist only while the hold and booking window are valid. Successful payment still awaits the seller. Cash collection is shown only for cash orders.
- Completed orders expose the review form only until a review exists; the order then reports its moderation state. Public empty ratings say no published reviews exist.
- Seller pages show approval/readiness separately from publication and stock. Slot screens show actual capacity, held, committed and remaining portions plus booking cutoffs.
- Staff readiness explains refresh scope/results and links moderation/admin. Missing original demo associations are reported instead of adopting arbitrary records.

## Boundaries

No real money, financial credentials, payouts, live GPS, courier integration, live delivery promise or email service is introduced. Cuisine is a dish category, not seller nationality or delivery geography. Seeded seller identities have unusable passwords; a separate fictional approved seller demonstrates actions.

This pass executes with one agent. Verification results and any remaining limitations are recorded in `docs/superpowers/plans/2026-10-16-homebites-progress.md` and `docs/milestones.md`.
