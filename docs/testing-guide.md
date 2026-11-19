# HomeBites testing guide

Work through the sections in order. Tick a box when the result matches "Expect". If it does not, write down the page address and what you saw (template at the end).

## 0. Start the app

The site runs at **http://127.0.0.1:8001**. Port 8000 may be used by another project on this PC.

If the site does not load after a restart, open PowerShell in the project folder and run these three commands. The last one stays running, so leave that window open.

```powershell
Start-Process "C:\Program Files\PostgreSQL\18\bin\pg_ctl.exe" -ArgumentList "-D",".pgdata","-o","-p 54330 -c listen_addresses=127.0.0.1","start" -WindowStyle Hidden
```
```powershell
.venv\Scripts\python.exe manage.py refresh_demo_availability
```
```powershell
.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8001
```

After any update press **Ctrl+F5** in the browser so it loads the new files.

**Accounts.** Logins are in `.demo-credentials.txt` in the project folder (a hidden-style file name that starts with a dot): `demo_buyer` is the customer, `demo_admin` is staff and admin. For the seller tests make a new account (section 4), ideally in a private window so you stay signed in as the buyer in the normal window.

The footer on every page says the project is a university project with simulated data. That is expected.

## 1. Visitor (not signed in)

| # | Do | Expect |
|---|---|---|
| 1.1 | Open `/` | Headline "A taste of home, from kitchens across Bangkok.", search box, a photo mosaic, then five full-width cuisine bands (Thailand, Pakistan, Bangladesh, Nepal, India) |
| 1.2 | Type "biryani" in the hero search, press Find food | Catalogue with biryani dishes |
| 1.3 | Click "See Nepal dishes" on the Nepal band | 10 Nepal dishes |
| 1.4 | Open `/food/` | 50 offers. Each card has a photo, a rating line (such as "4.6 out of 5 · 5 reviews"), calorie chip, serving size, diet tags and an availability dot |
| 1.5 | Use the **Category** menu, choose Desserts | 6 desserts (Mango Sticky Rice, Kheer, Mishti Doi, Yomari, Juju Dhau, Gulab Jamun) |
| 1.6 | Open **Refine results**, choose diet **Halal** | 26 offers. Pakistani and Bangladeshi dishes plus a few Nepali and Indian ones |
| 1.7 | Refine: diet Vegetarian, then add max price 120 | The list shrinks. "Reset filters" restores all 50 |
| 1.8 | Refine: set **Rating** to 4.5 and up, then **Pickup area** to one area | Only dishes from kitchens at that pickup point |
| 1.9 | Use **Sort by**: Top rated, then Price low to high, then Price high to low | The order changes each time and matches the sort |
| 1.10 | Search for "zzzz" | A friendly "No food matched" message |
| 1.11 | Open any dish | AI-generated illustration with a note, ingredients, calorie box with serving size and source, order windows, and a **Customer reviews** section with an average and 4 or 5 reviews |
| 1.12 | Click the seller name | Kitchen page with average rating, review count, completed orders, the menu and "What customers say" |
| 1.13 | On a dish, try Add to cart while signed out | You are sent to sign in, not shown an error |
| 1.14 | Narrow the browser to about 390 px (or use device mode) | Menu button appears, cards stack, no sideways scroll |

## 2. Account

| # | Do | Expect |
|---|---|---|
| 2.1 | `/account/signup/` create a new account (use a made-up name) | You are signed in at once. A green message says welcome. The header shows **"Hi, username"** |
| 2.2 | Sign out, then sign in at `/accounts/login/` | You land on **Explore food**, not the profile. The header shows "Hi, username", Cart, Orders and Seller dashboard |
| 2.3 | Try a wrong password | A clear error, no crash |
| 2.4 | Click "Hi, username" | Your account page: username, account type, a form for name and email, a Change password link, and a seller link |
| 2.5 | Change your name and email, Save changes | "Your details were saved." and the new values show |
| 2.6 | Click Change your password and set a new one | "Password changed" page. Sign out and back in with the new password |
| 2.7 | `/accounts/password_reset/` with an email | A "check your email" page (the email text appears in the server window) |

## 3. Customer: cart, delivery, checkout, payment

Sign in as `demo_buyer`.

| # | Do | Expect |
|---|---|---|
| 3.1 | Open a dish, choose a window, quantity 2, Add to cart | Green message and the cart page with a steps bar (Cart, Payment, Confirmation) |
| 3.2 | In the cart change portions to 3, Update | The order summary on the right changes |
| 3.3 | Add a dish from a **different** kitchen | Both kitchens appear in the cart as separate groups. The button says "Place 2 orders". With PromptPay or card you pay once for both and the payment is split between the kitchens |
| 3.4 | Under **Pickup or delivery** choose Pickup | Summary shows "Pickup: Free" and a total |
| 3.5 | Choose **Bangkok delivery**, then an area | The delivery price and distance appear in the summary **by themselves**, no extra click. Try a second area: the price changes |
| 3.6 | Choose Delivery but no area yet | A hint says to choose your delivery area |
| 3.7 | Pick **Cash on pickup** (or on delivery), Place order | Order page with a progress line, the status, totals and a View receipt button |
| 3.8 | Place an order with **PromptPay** | Payment page: a QR picture, a reference like `HB-ORDER-…`, the amount, a countdown, one green button "I've paid ฿…" and a small "Cancel payment and order" link. **No Decline or Pay later buttons** |
| 3.9 | Click "I've paid" | "Payment received" with Track your order and View receipt |
| 3.10 | Place an order with **Card** | A card picture with no input fields, the text that no card details are requested, a "Pay ฿…" button and the cancel link |
| 3.11 | On a payment page click "Cancel payment and order" | The order is cancelled and the portions are released |
| 3.12 | Open `/orders/` and an order | A progress line, a timeline with times, and what happens next |
| 3.13 | Open the **receipt** from an order | Receipt with date, kitchen, items and ingredients, totals and payment status. The Print button opens the print view |
| 3.14 | Double-click Place order quickly | Only one order is created |
| 3.15 | Add more portions than are left | Refused with an explanation |
| 3.16 | Wait for a payment hold to run out (15 minutes) or reload after expiry | "Payment window closed" with a way to find food |

Payments always succeed when you press the pay button, because they are simulated. The order only fails to pay if the 15-minute hold runs out.

## 4. Seller

Use a private window and a new account.

| # | Do | Expect |
|---|---|---|
| 4.1 | Sign up a new account, then `/sellers/apply/` | Application submitted, waiting for approval |
| 4.2 | As `demo_admin` open `/admin/`, Sellers, approve that seller | Seller approved |
| 4.3 | As the seller, `/sellers/profile/edit/`: storefront name, description, pickup location | Saved |
| 4.4 | `/sellers/offers/new/` | Only the approved dishes can be chosen. Saving without ingredients is refused |
| 4.5 | Add an offer with ingredients. Optionally add calories, serving size and a source | Offer saved. Editing the ingredients later clears the calorie values |
| 4.6 | Upload a photo (also try a non-image file) | The image replaces the illustration. A non-image is rejected |
| 4.7 | Tick the **Halal** label on an offer | The card and dish page show a Halal tag and the filter finds it |
| 4.8 | `/sellers/slots/`: create a standard slot and a pre-order slot, set portions | Slots listed with stock |
| 4.9 | As `demo_buyer`, order that seller's dish | The order appears for the seller at `/seller-orders/` |
| 4.10 | As the seller open the order and press **Confirm order** | Status Confirmed |
| 4.11 | Press the next-step button each time: **Start preparing**, then **Mark ready for pickup** (or **Mark ready for delivery**) | One button per step. The buyer's progress line moves and the timeline adds a line each time |
| 4.12 | Pickup order: press **Complete pickup** (with "and record cash" for cash orders) | Status Completed |
| 4.13 | Delivery order: after Ready press **Send out for delivery**, then **Mark delivered**, then **Complete order** | Out for delivery, Delivered, Completed in that order |
| 4.14 | Try to skip a step by opening the buttons in another order | Not possible. Only the next button is offered |
| 4.15 | Reject an order with a reason | The order is rejected and the portions are released |
| 4.16 | `/sellers/dashboard/` | Completed orders, portions sold, food subtotal, earnings and the 10% commission |
| 4.17 | Click Delete on an offer with no orders | A confirmation page. After confirming the offer is gone |
| 4.18 | Click Delete on an offer that has orders | The page says it will be unpublished instead. After confirming it is a draft and past orders are intact |
| 4.19 | Open your own kitchen page | Average rating, review count, completed orders and your menu |

## 5. Pre-orders

| # | Do | Expect |
|---|---|---|
| 5.1 | Pick a **Pre-order** window on a dish | It shows its order-by deadline |
| 5.2 | Order it with delivery | Works before the deadline. Standard orders close 30 minutes before the window ends |

## 6. Reviews and reports

| # | Do | Expect |
|---|---|---|
| 6.1 | As the buyer open a **completed** order | A "Review this completed order" link |
| 6.2 | Submit a review | It says pending moderation |
| 6.3 | Try to review the same order again | Refused (once per order) |
| 6.4 | On a dish click Report this offer and submit | Report received page |
| 6.5 | As `demo_admin` open `/reviews/moderation/`, approve the review and resolve the report with a reason | The approved review appears on that dish page and the kitchen page, and the averages update |

Each dish already has 4 or 5 sample reviews from made-up customers. They appear on dish pages and cards.

## 7. Staff and admin

| # | Do | Expect |
|---|---|---|
| 7.1 | `/admin/` | Manage users, sellers, dishes (with category), listings and orders |
| 7.2 | `/demo/readiness/` | Demo status page. Refresh button works |
| 7.3 | Open `/demo/readiness/` as `demo_buyer` | Forbidden |

## 8. Safety and edge cases

| # | Do | Expect |
|---|---|---|
| 8.1 | As the buyer open `/sellers/dashboard/` or `/seller-orders/` | Redirected or forbidden |
| 8.2 | Open another user's order or receipt address | Not found |
| 8.3 | Open `/nothing-here/` | A normal "Page not found" |
| 8.4 | A sold-out or paused dish | Clear message, cannot be added |
| 8.5 | As a seller try to delete another seller's offer | Not found |

## 9. Look and feel

| # | Check |
|---|---|
| 9.1 | Fonts: Gloock headings, Instrument Sans text |
| 9.2 | Palette: cream page, green buttons, turmeric highlights, red prices and logo |
| 9.3 | Raised buttons (Cart, Create account, Find food, Add to cart, Place order, Pay) press down when clicked |
| 9.4 | Images look consistent within each cuisine: marble (Thailand), slate (Pakistan), wood and red cloth (Bangladesh), weathered wood and brass (Nepal), light stone (India) |
| 9.5 | Cart, payment, order, receipt and seller pages at phone width: readable, no sideways scroll |
| 9.6 | Press Tab through a page: a visible outline moves through links and buttons |

## 10. Known limits (say these in the demo)

- Payments, delivery prices and locations are simulated. No real money moves and no courier is involved.
- Calories are estimates from reference recipes; portions vary.
- Dish images are AI-generated illustrations, not photos of real dishes.
- Sample reviews and the seeded kitchens are made up.
- Halal and vegetarian labels are the seller's own declarations, not certificates.

## Report template

```
Section / step:
Page address:
What I did:
What I expected:
What happened:
```
