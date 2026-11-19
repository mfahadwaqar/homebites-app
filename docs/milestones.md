# HomeBites Project Milestones

This roadmap is the execution ledger for the complete simulated HomeBites project. A milestone is complete only when its acceptance evidence is recorded and its tests pass against PostgreSQL.

| ID | Milestone | Main outcome | Status |
|---|---|---|---|
| M0 | Repository and delivery plan | Version-controlled project, approved specification, complete roadmap and local-environment strategy | Complete |
| M1 | Foundation and accounts | Django/PostgreSQL foundation, custom user, registration, login, password reset preview and admin access | Complete |
| M2 | Sellers and fixed food catalogue | Seller approval plus exactly 50 dishes—10 per country—with required seller-specific ingredients | Complete |
| M3 | Marketplace discovery | Home, catalogue, search, country/dietary/price/availability filters, food details and seller storefronts | Complete |
| M4 | Cart and fulfillment selection | Persistent single-seller cart, quantity validation, standard/pre-order slots and pickup/delivery selection | Complete |
| M5 | Simulated locations and delivery pricing | Offline Bangkok locations, distance simulation, delivery quotes and free pickup | Complete |
| M6 | Reliable checkout and inventory | Transactional stock reservation, snapshots, idempotent checkout and overselling protection | Complete |
| M7 | Simulated payments | Mock PromptPay/card/cash flows, retry/expiry and simulated refunds without real financial data | Complete |
| M8 | Order fulfillment and tracking | Valid pickup/delivery state machines, seller actions and customer status timeline | Complete |
| M9 | Reviews, dashboards and moderation | Eligible reviews, seller statistics, reports and administrator moderation | Complete |
| M10 | Experience, accessibility and security QA | Responsive branded experience, accessible interactions, permission and offline regression coverage | Complete |
| M11 | Packaging and classroom handover | Idempotent demo seed/reset, setup guide, test evidence, backup/restore and presentation walkthrough | Complete |

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

## Completion evidence

### Behavior acceptance follow-up — 2026-10-16

The earlier milestone completion established technical flows, but did not ensure an aged demo remained orderable on normal startup. The October 16 follow-up corrected that gap and audited the reasons behind visible states/actions.

- Shared read-only availability policy now supplies catalogue, details, storefronts, cart/checkout and payment cutoff checks. Standard orders close 30 minutes before fulfillment ends; pre-orders use explicit deadlines. Published, accepting-orders, sold-out, paused, closed and unscheduled states are distinct.
- Explicit preparation refreshes only expired marked demo windows, retaining live stock, intentional pauses, passwords and history. Staff refresh is CSRF-protected; browsing never rotates schedules. Concurrent-refresh and historical-confirmed-order tests passed.
- Cart replacement is reviewable and revision-checked. Changed ingredients/prices require signed confirmation from the current dish page. Cart errors retain items and describe recovery.
- Totals, quote expiry, payment holds, next actors, simulated handoffs, review moderation and settled-only seller totals are explained. Generic imagery is labelled; vegan offers do not inherit the egg-based Pad Thai fallback.
- The isolated PostgreSQL full suite passed **170/170 tests**. System and migration checks passed. Catalogue query-budget, malformed reference, token/revision race, stock concurrency and refresh concurrency checks are included.
- Chrome/Playwright exercised public pages at 1440, 390 and 320 pixels; seller application/approval, draft-to-published offer, slots/capacity, standard pickup/cash completion, preorder delivery with failed payment then a fresh successful checkout, seller handoff, buyer review and staff moderation, cart conflict cancellation, staff refresh and forbidden buyer access. The final complete journey run recorded zero unexpected console/page errors. A default favicon 404 found in QA was corrected and regression-tested.
- Focused browser checks passed success-message styling and 200% text on dish/cart/account surfaces. An enlarged-text cart overflow was corrected and rechecked. Screenshots remain outside the repository in the Codex workspace.
- Applied the verified non-destructive refresh to the existing demo: 50 published offers → 50 accepting orders; order count remained **1 → 1**; total windows **10 → 20** and stock rows **100 → 200**, retaining the original historical records.
- Current rules and walkthroughs are in [behavior-rules.md](behavior-rules.md) and [demo-scenarios.md](demo-scenarios.md). Normal startup is `scripts/start-demo.ps1`.
- Verification used one agent with an author review, per the user's cost preference. Other browser engines were not tested; existing illustrative images remain representative cuisine imagery rather than 50 exact dish photos. The work remains local and uncommitted.

### M0 — Complete on 2026-10-04

- Git repository initialized with `main` retaining the planning baseline and implementation isolated on `milestone/01-foundation`.
- Approved design, end-to-end roadmap and the first executable implementation plan are stored under `docs/`.
- Project scope records a fully simulated, Bangkok-wide C2C marketplace with exactly 50 initial dishes: 10 each from Thailand, Pakistan, Bangladesh, Nepal and India.

### M1 — Complete on 2026-10-04

- Django 5.2.17 runs against the healthy project-local PostgreSQL 17 Compose service; there is no SQLite fallback.
- The custom `accounts.User` model, Django Admin registration, signup, protected profile, login, POST-only logout and enumeration-safe local password reset are implemented.
- All 16 Django tests pass against PostgreSQL. `manage.py check`, `makemigrations --check --dry-run` and `migrate --check` pass.
- `manage.py check --deploy` reports only the expected localhost-development warnings for `DEBUG`, HTTPS/HSTS and secure cookies; public deployment is outside the approved scope.
- Playwright with local Chrome passed the complete account journey at 1440×900 plus the home page at 390×844. It found no console errors, page errors, failed responses or external requests.
- The Codex in-app browser could not initialize because its local kernel assets were unavailable, so the documented Playwright/Chrome fallback was used and screenshots were inspected manually.

### M2–M10 — Complete on 2026-10-04

- The fixed five-country, 50-dish catalogue, seller approval and ingredients, browse/filter/detail/storefront, cart, offline Bangkok quotes, transactional checkout, mock payments, fulfillment, reviews, dashboards and moderation are implemented.
- The isolated PostgreSQL suite passed 137/137 tests, including stock concurrency, permissions, CSRF, simulated payment lifecycle, seed idempotency and upload validation. `check`, `makemigrations --check --dry-run` and `migrate --check` passed.
- Playwright/Chrome exercised desktop and mobile discovery, dietary filtering, a complete buyer delivery/PromptPay journey, seller fulfillment and buyer review submission without console/page errors or external requests. Staff moderation is covered by automated tests but was not browser-verified.

### M11 — Complete on 2026-10-04

- `seed_demo` creates 50 public offers, eight fictional Bangkok locations, five distinct seller pickup points, 10 current standard/pre-order slots and 100 stock records. Its fictional buyer begins with an unusable password and is activated for local use through the interactive `changepassword` command.
- Five focused seed tests passed against PostgreSQL, including repeatability without resetting used stock, refusal to adopt an unrelated `demo_buyer` account, and rotation of an expired slot while preserving old stock.
- [The classroom handover](classroom-handover.md) contains fresh Windows setup, a seller/buyer/staff walkthrough, simulation boundaries, backup/restore commands and a requirement/test matrix.
- A binary PostgreSQL backup was copied through Windows and restored into a disposable database. The restored query returned `50|100` dish/stock rows. An exact-name listing preceded removal of that disposable database, and temporary backup copies were removed.
- The isolated PostgreSQL full suite passed 137/137 tests. Desktop and mobile browser checks covered home, catalogue, country and dietary filters, ingredients, buyer cart/quote/mock payment, seller confirmation/handoff/dashboard, and buyer submission of a pending review. Staff moderation was covered by automated tests but not browser-verified.
- A separate clean Git checkout applied all migrations to an exact-name disposable PostgreSQL database. Its first `seed_demo` run produced 50 dishes, 50 offers and 100 stock rows; rerunning the seed preserved those counts. System and migration checks passed. The disposable database and checkout (including its temporary `.env` copy) were removed afterward; the live demo database was not changed.

