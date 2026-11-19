# How to recreate the 19 slide screenshots

Site: http://127.0.0.1:8001 (start it with section 0 of `docs/testing-guide.md` if it does not load). Press Ctrl+F5 first.
Logins are in `.demo-credentials.txt`: `demo_buyer` (customer), `demo_admin` (staff), `demo_seller_pakistan` (seller, any `demo_seller_<country>` works).
Tip: use two browser windows, one normal (buyer) and one private (seller or admin), so you do not keep signing out.
For each shot, zoom the browser to about 90% and keep the whole page section in view.

## Buyer shots (sign in as `demo_buyer`)

| # | Screenshot | How to get it |
|---|---|---|
| 01 | Homepage | Open `/`. Capture the top: headline, search box, photo mosaic |
| 02 | Catalogue | Click **Explore food** (`/food/`). Capture the cards with rating, calories and availability |
| 03 | Dietary filters | On `/food/` open **Refine results**, set diet to **Halal**, click **Show food**. Capture the open filter and the results |
| 04 | Dish details | Open **Chicken Biryani** (`/food/11/`). Scroll so ingredients, calorie box, order windows and **Customer reviews** show |
| 05 | Delivery fee | Add a dish to the cart. Under **Pickup or delivery** choose **Bangkok delivery**, then pick an area. Capture the cart once the delivery price and distance show in the summary |
| 06 | Checkout and order placed | Pick **Cash on pickup** (set Method back to Pickup first), click **Place order**. Capture the order page with status "Cash due" |
| 07 | PromptPay | Add a dish, choose **PromptPay**, click **Place order**. Capture the payment page with the QR, reference and the green "I've paid" button |
| 08 | Payment received | On that page click **I've paid**. Capture "Payment received" with Track your order and View receipt |
| 09 | Card payment | Add a dish, choose **Card**, click **Place order**. Capture the card picture page (no input fields) |
| 10 | Order tracking | Click **Track your order** (or open the order from **Orders**). Capture the progress line and timeline. Best after the seller has confirmed or moved the order (see seller shots) |
| 11 | Receipt | On an order click **View receipt**. Capture the full receipt |
| 12 | Pre-order | Open a dish and look at **Choose a fulfillment window**. Capture the **Pre-order** window with its "Order by" deadline |

## Seller and staff shots

| # | Screenshot | How to get it |
|---|---|---|
| 13 | Seller approval | Create a new account, go to `/sellers/apply/`, submit. Sign in as `demo_admin`, open `/admin/sellers/sellerprofile/`, tick the new seller, choose **Approve selected sellers** and click **Go**. Capture the list showing "Approved" |
| 14 | Seller halal label | Sign in as an approved seller. Open `/sellers/offers/new/`, tick **Halal**, add ingredients, save. Open the dish's public page or catalogue card and capture the **Halal** tag |
| 15 | Seller status steps | Place an order with `demo_buyer` from that seller's dish. As the seller open **Manage orders**, open the order, click **Confirm order**, then **Start preparing**. Capture the order page showing the single next-step button ("Mark ready for pickup") |
| 16 | Delivery chain | Place a **delivery** order. As the seller: **Confirm order**, **Start preparing**, **Mark ready for delivery**, **Send out for delivery**, **Mark delivered**, **Complete order**. Capture the page at the last step (status Delivered or Completed) |
| 17 | Seller dashboard | After at least one completed order, open `/sellers/dashboard/`. Scroll to **Completed sales**: orders, portions, food subtotal, earnings and commission |
| 18 | Review awaiting moderation | As the buyer open a **completed** order, click **Review this completed order**, give a rating and comment, submit. Open the order again and capture "Your review: Pending moderation" |
| 19 | Moderation | As `demo_admin` open `/reviews/moderation/`. Capture the pending review and open reports before you approve them |

## Order to do them in (saves time)

1. Shots 01 to 05 (no orders needed).
2. As a seller account: shot 14, then add a time slot and portions at `/sellers/slots/` (a standard slot for tomorrow, then **Set capacity**).
3. Shots 07, 08, 09, 06, 11 (buyer orders from the seller).
4. Shot 13 (admin approves a fresh seller).
5. Shots 15, 16, 10, 17 (seller completes orders).
6. Shots 18 and 19 (review, then moderation, then approve it).
7. Shot 12 on any dish with a pre-order window.

## Checking yourself

Each shot should look like the file of the same number in `docs/slide-screenshots/`. If a screen differs, note the page address and what you saw.
