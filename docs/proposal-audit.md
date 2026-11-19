# Site vs proposal audit (18 November 2026)

Source: HomeBites Project Proposal Report (sections 2, 4, 5, 7) and the course brief. Checked against the code and the running site.

## Met

| Proposal item | Where it is |
|---|---|
| Customer and seller registration | `/account/signup/`, `/sellers/apply/`, admin approval |
| Seller storefronts and listings: name, description, price, quantity, image, cuisine, availability | `/sellers/offers/`, `/sellers/slots/`, storefront pages |
| Browse, search, filter by cuisine, price, dietary, availability | `/food/` |
| Dietary categories: vegetarian, vegan, halal | Refine results |
| Normal orders and pre-orders with deadlines | Slots: standard and pre-order |
| Cart and checkout | `/orders/cart/` |
| Pickup (free) or delivery | Cart |
| Distance between seller and customer, automatic delivery fee | Delivery price from seller pickup point to the chosen Bangkok area |
| Payment options: PromptPay, card, cash on delivery, cash on pickup | Checkout and payment screens |
| Seller dashboard: incoming orders, total sales, meals sold, average rating | `/sellers/dashboard/`, `/seller-orders/` |
| Customers monitor order status | Order page with progress and timeline |
| Ratings and written reviews after a completed order | Review form, moderation, dish and seller review pages |
| 10% commission revenue model | Order totals, seller dashboard |
| Admin: manage users and sellers, review registrations, monitor listings and orders, handle reports | `/admin/`, `/reviews/moderation/` |
| Django, PostgreSQL | Yes |

## Gaps (gaps 1 to 5 fixed on 19 November 2026)

| # | Proposal says | Site today | Size |
|---|---|---|---|
| 1 | Order statuses: Pending, Confirmed, Preparing, Ready, Out for Delivery, Delivered, Completed (delivery); Pending, Confirmed, Preparing, Ready for Pickup, Completed (pickup) | Awaiting seller, Confirmed, Completed. No Preparing, Ready, Out for delivery or Delivered steps | Medium |
| 2 | Seller profile shows average rating, number of completed orders and customer reviews | Storefront only links to a separate reviews page. No rating or completed-order count on the storefront | Small |
| 3 | Filter by seller rating and location. Dietary and cuisine categories include desserts | No rating filter, no location filter, no sorting, no dessert category | Medium |
| 4 | Customers and sellers manage their accounts | Profile page is read-only and still shows the placeholder "will be added in later milestones" | Small |
| 5 | Sellers can add, edit and delete food items | Add and edit exist; offers can be unpublished but not deleted | Small |
| 6 | Customer enters or selects a delivery address | Customer selects from the Bangkok areas. No free-text address | Optional |
| 7 | Frontend uses Bootstrap | Custom CSS, no Bootstrap. Mention in the report as a design choice | Report only |
| 8 | Chinese cuisine listed as an example | Five cuisines (Thai, Pakistani, Bangladeshi, Nepali, Indian). The proposal says "and others" | Report only |

## Simulated, as the proposal allows

Payments, delivery and map locations are simulated (proposal 4.7 and section 7).

## Fixes applied

1. Order status chain: Confirmed, Preparing, Ready (Ready for pickup), Out for delivery, Delivered, Completed. Seller gets one next-step button per order; buyers see the full progress line.
2. Storefront: average rating, review count, completed orders and the latest reviews.
3. Catalogue: Category (main dishes, snacks, desserts), rating filter, pickup area filter and sorting (name, top rated, price).
4. Profile: edit name and email, change password, link to seller dashboard or application.
5. Sellers can delete offers; offers with order history are unpublished instead so past orders stay intact.
