# HomeBites Design Specification

## Purpose

HomeBites is a locally runnable university demonstration of a Bangkok-wide food marketplace. It must demonstrate realistic customer, seller and administrator journeys while making clear that payments, delivery progress, distance calculations and commercial figures are simulated.

The implementation must not require paid services, live payment accounts, courier integrations, cloud hosting or internet access after project dependencies and container images have been installed.

## Marketplace model

- HomeBites is primarily C2C, while allowing small-scale B2C-style sellers.
- The marketplace relationship is many-to-many: one buyer may order from many sellers and one seller may serve many buyers.
- Each individual order belongs to one buyer, one seller and one fulfillment slot.
- A user may buy and may also gain seller capabilities after seller approval.
- A user may not purchase their own listing.

## Catalogue scope

The master catalogue contains exactly 50 distinct dishes:

- Thailand: 10 dishes
- Pakistan: 10 dishes
- Bangladesh: 10 dishes
- Nepal: 10 dishes
- India: 10 dishes

Sellers choose a predefined master dish rather than create arbitrary dishes. Each seller offer has its own required ingredient list, description, image, price, quantity and availability. Customers can read ingredients before ordering. An order item stores an ingredient snapshot so later edits do not rewrite order history.

Country is a cuisine grouping, not the seller's nationality or delivery address. All simulated selling and delivery remains Bangkok-based.

## User journeys

### Customer

Register and sign in, browse and filter dishes, inspect seller and ingredient information, add compatible items to a cart, select pickup or simulated delivery, complete a mock payment, track fulfillment, view history and review an eligible completed order.

### Seller

Apply for approval, maintain a storefront, create offers from the master catalogue, review/edit ingredients, manage quantities and standard/pre-order slots, process orders through valid states and view simulated sales statistics.

### Administrator

Approve or suspend sellers, maintain the fixed catalogue and dietary labels, moderate listings/reviews/reports, inspect orders and use guarded demo controls.

## Fulfillment and commercial rules

- Support standard orders and pre-orders.
- Pickup is free.
- Delivery uses a clearly labelled local simulation based on stored sample Bangkok coordinates.
- Payment methods are mock PromptPay, mock card, cash on delivery and cash on pickup.
- The platform commission is configurable and initially 10% of the food subtotal.
- Delivery fees are separate from the commission and seller food earnings.
- Cart contents do not reserve stock. Checkout and payment flows must prevent overselling and duplicate submissions.
- Reviews are limited to the buyer of a completed order, one review per order.

## Architecture

Use a Django monolith with server-rendered HTML, local Bootstrap assets, minimal JavaScript and PostgreSQL. Split responsibilities into accounts, sellers, catalogue, cart/orders, payments, fulfillment and reviews. Keep calculations and state changes in explicit service functions rather than templates or scattered signals.

Development uses Python 3.13, Django 5.2 LTS and PostgreSQL 17. PostgreSQL runs in a project-local Docker container. Tests run against PostgreSQL, not SQLite.

## Interface direction

Use the HomeBites presentation's cream, deep purple and orange visual identity. The first milestone only establishes an accessible functional shell and account screens. Detailed marketplace visual concepting and browser-fidelity work belongs to the marketplace-interface milestone.

## Quality and safety

- Develop behavior test-first and verify complete milestone suites before marking milestones complete.
- Enforce authorization server-side.
- Use CSRF protection, template escaping and Django password hashing.
- Use fictional demo identities and addresses.
- Keep secrets, generated media and local environment files out of Git.
- Bind the development server to localhost and do not publish or tunnel it.
- Keep the implementation intentionally narrow: no live APIs, multi-seller checkout, subscriptions, coupons, chat, recommendation AI, native mobile app or production deployment.

## Completion definition

The project is complete when the full seeded demonstration works locally, all required acceptance tests pass against PostgreSQL, all 50 dishes and ingredient lists are present, and another student can reproduce the environment and classroom walkthrough from the documentation.

