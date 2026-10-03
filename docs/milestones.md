# HomeBites Project Milestones

This roadmap is the execution ledger for the complete simulated HomeBites project. A milestone is complete only when its acceptance evidence is recorded and its tests pass against PostgreSQL.

| ID | Milestone | Main outcome | Status |
|---|---|---|---|
| M0 | Repository and delivery plan | Version-controlled project, approved specification, complete roadmap and local-environment strategy | In progress |
| M1 | Foundation and accounts | Django/PostgreSQL foundation, custom user, registration, login, password reset preview and admin access | Pending |
| M2 | Sellers and fixed food catalogue | Seller approval plus exactly 50 dishes—10 per country—with required seller-specific ingredients | Pending |
| M3 | Marketplace discovery | Home, catalogue, search, country/dietary/price/availability filters, food details and seller storefronts | Pending |
| M4 | Cart and fulfillment selection | Persistent single-seller cart, quantity validation, standard/pre-order slots and pickup/delivery selection | Pending |
| M5 | Simulated locations and delivery pricing | Offline Bangkok locations, distance simulation, delivery quotes and free pickup | Pending |
| M6 | Reliable checkout and inventory | Transactional stock reservation, snapshots, idempotent checkout and overselling protection | Pending |
| M7 | Simulated payments | Mock PromptPay/card/cash flows, retry/expiry and simulated refunds without real financial data | Pending |
| M8 | Order fulfillment and tracking | Valid pickup/delivery state machines, seller actions and customer status timeline | Pending |
| M9 | Reviews, dashboards and moderation | Eligible reviews, seller statistics, reports and administrator moderation | Pending |
| M10 | Experience, accessibility and security QA | Responsive branded experience, accessible interactions, permission and offline regression coverage | Pending |
| M11 | Packaging and classroom handover | Idempotent demo seed/reset, setup guide, test evidence, backup/restore and presentation walkthrough | Pending |

## Milestone gates

### M0 — Repository and delivery plan

- Git repository initialized without modifying presentation/report files.
- Design specification and full implementation plan stored in the repository.
- Milestones, non-goals and the first execution plan are documented.
- Development runs on a feature branch rather than directly on `main`.

### M1 — Foundation and accounts

- Django uses PostgreSQL supplied by project-local Docker Compose.
- A custom user model exists before the first migration.
- Registration, login, logout and password-reset preview work.
- Django Admin can manage users.
- Foundation tests and deployment checks pass.

### M2 — Sellers and fixed food catalogue

- Five countries and exactly 10 master dishes per country are seeded.
- Every initial seller offer has a reviewed ingredient list.
- Sellers cannot add out-of-catalogue dishes or publish without ingredients.
- Seller ownership and approval permissions are enforced.

### M3 — Marketplace discovery

- Customers can search, paginate and filter the 50-dish catalogue.
- Food details expose the seller's ingredients before purchase.
- Seller storefronts, empty states and unavailable listings behave correctly.

### M4 — Cart and fulfillment selection

- The signed-in cart persists and accepts only one seller/slot at a time.
- Quantity, deadline and availability conflicts are explained without silent data loss.
- Pickup and delivery choices are constrained correctly.

### M5 — Simulated locations and delivery pricing

- Sample Bangkok locations resolve offline.
- Delivery quotes are server-calculated, labelled simulated and expire safely.
- Pickup always costs zero; location/cart/tariff changes require a new quote.

### M6 — Reliable checkout and inventory

- Order, price, ingredient and location snapshots are immutable.
- Duplicate checkout requests create one order.
- Concurrent attempts to buy the last portion cannot oversell.
- Reservation expiry and cancellation release stock exactly once.

### M7 — Simulated payments

- All four proposed methods demonstrate valid success/failure/due states.
- The UI never requests real bank or card credentials.
- Late, repeated and invalid results cannot resurrect or duplicate an order.

### M8 — Order fulfillment and tracking

- Pickup and delivery orders follow only valid transitions.
- Seller/customer/staff permissions are enforced for every transition.
- Customers see a timestamped timeline without fake live-GPS claims.

### M9 — Reviews, dashboards and moderation

- Only an eligible buyer can review a completed order once.
- Dashboard totals reconcile with completed simulated-paid/cash-collected orders.
- Reports and moderation actions retain an audit trail.

### M10 — Experience, accessibility and security QA

- Marketplace screens match the approved HomeBites visual system on desktop and mobile.
- Keyboard navigation, labels, focus states, contrast and validation feedback pass review.
- Authorization, CSRF, upload validation, offline operation and regression suites pass.

### M11 — Packaging and classroom handover

- A clean setup and database seed are reproducible on a fresh environment.
- Exactly 50 dishes are discoverable after seeding, and reruns do not duplicate data.
- Documentation includes accounts, setup, troubleshooting and the classroom walkthrough.
- Database backup/restore and the full end-to-end demonstration are exercised successfully.

