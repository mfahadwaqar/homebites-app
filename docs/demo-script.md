# Live demo script (about 8 minutes)

Three tabs, one per role. Keep them open side by side.

| Tab | Address | Login |
|---|---|---|
| A. Customer | http://localhost:8001 | `demo_buyer` (password in `.demo-credentials.txt`) |
| B. Seller | http://127.0.0.1:8002 | `demo_seller_pakistan` (the password you set in the setup step) |
| C. Admin | http://127.0.0.2:8003 | `demo_admin` (password in `.demo-credentials.txt`) |

## Before the demo (2 minutes)

1. Database and three servers running (see the earlier start commands).
2. Run `.venv\Scripts\python.exe manage.py refresh_demo_availability` so order windows are open.
3. Sign in on all three tabs and press **Ctrl+F5** once on each.
4. On tab A, empty the cart. Open the home page.
5. Zoom each tab to 90%.
6. Practise the whole run once, then place one extra order beforehand so the seller queue is not empty if something goes wrong.

## The run

**Part 1. Customer: find food (tab A, 2 min)**

| Step | Do | Say |
|---|---|---|
| 1 | Show the home page | Five cuisines, search, kitchens |
| 2 | Click **Explore food**, open **Refine results**, pick **Halal**, then **Show food** | Filters for diet, price, rating, pickup area, plus sorting |
| 3 | Clear the filter, search "biryani" | Search across all kitchens |
| 4 | Open **Chicken Biryani** | Ingredients, calories, order windows, customer reviews |
| 5 | Point at a **Pre-order** window | Pre-orders have an order-by deadline |

**Part 2. Customer: order and pay (tab A, 2 min)**

| Step | Do | Say |
|---|---|---|
| 6 | Pick a window, quantity 2, **Add to cart** | Dishes from other kitchens can be added too; each kitchen becomes its own order |
| 7 | Choose **Bangkok delivery**, then an area | Delivery price updates by itself, distance based |
| 8 | Select **PromptPay**, click **Place order** | Payment page with QR and reference |
| 9 | Click **I've paid** | Payment confirmation, simulated |
| 10 | Click **Track your order** | Progress line and timeline |

**Part 3. Seller: handle the order (tab B, 2 min)**

| Step | Do | Say |
|---|---|---|
| 11 | Open **Manage orders** (`/seller-orders/`), open the new order | The order appears for the right kitchen |
| 12 | Click **Confirm order** | |
| 13 | Click **Start preparing**, **Mark ready for delivery**, **Send out for delivery**, **Mark delivered**, **Complete order and record cash** if shown or **Complete order** | One button per step, steps cannot be skipped |
| 14 | Open **Seller dashboard**, scroll to **Completed sales** | Earnings after the 10% commission |

Go back to tab A and refresh the order page to show the progress line now complete.

**Part 4. Review and admin (tabs A and C, 1.5 min)**

| Step | Do | Say |
|---|---|---|
| 15 | Tab A: on the completed order click **Review this completed order**, give 5 stars and a comment, submit | One review per completed order, held for moderation |
| 16 | Tab C: open `/reviews/moderation/`, set **Approve**, add a reason, save | Staff moderate reviews and reports |
| 17 | Tab A: open the dish page and scroll to **Customer reviews** | The approved review is now public |
| 18 | Tab C: open `/admin/` | Users, sellers, dishes, listings, orders |

## Closing line

"Payments, delivery and locations are simulated, as the proposal allows. Everything else, from search to moderation, is working."

## If something goes wrong

| Problem | Fix |
|---|---|
| "Window closed" or no windows | Run `refresh_demo_availability`, reload the dish page |
| A tab shows a login page | Sign in again with the table above |
| Page looks unstyled or old | Ctrl+F5 |
| Server tab stopped | Re-run its `runserver` command in its PowerShell window |
| Payment page expired | Click **Cancel payment and order**, add the dish again |
| Order missing in seller queue | Check you ordered from the Pakistani Home Kitchen |

## If the professor asks to see more

- Signup and login: `/account/signup/`, then sign out and in.
- Cash order: choose **Cash on pickup**, no payment screen.
- Receipt: **View receipt** on any order.
- Seller application: `/sellers/apply/`, approve it in `/admin/sellers/sellerprofile/`.
- Phone view: narrow the browser to about 390 px.
