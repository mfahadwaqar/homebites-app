# Ordering walkthrough: from browsing to payment

Run this once, top to bottom. Tick each step when the screen matches "You should see".

## Before you start

1. Open http://127.0.0.1:8001 (if it does not load, follow section 0 of `docs/testing-guide.md`).
2. Press **Ctrl+F5** so the newest files load.
3. Log in details are in `.demo-credentials.txt` in the project folder. Use `demo_buyer`.

## A. Sign in

| Step | Do | You should see |
|---|---|---|
| A1 | Click **Sign in**, enter `demo_buyer` and its password | You land on **Explore food**. The header shows "Hi, demo_buyer", Cart, Orders |

## B. Find a dish

| Step | Do | You should see |
|---|---|---|
| B1 | Type "biryani" in the search box, click **Show food** | Biryani dishes with photo, rating, calories, price |
| B2 | Click **Chicken Biryani** | Dish page: ingredients, calorie box, order windows, customer reviews |

## C. Add to cart

| Step | Do | You should see |
|---|---|---|
| C1 | Under **Choose a fulfillment window** pick a window that shows portions left | The window is selected |
| C2 | Set **Portions** to 2, click **Add to cart** | Green message "Added to your cart" and the cart page with steps: 1 Cart, 2 Payment, 3 Confirmation |
| C3 | Change portions to 3, click **Update** | Order summary on the right changes |

## D. Pickup or delivery

| Step | Do | You should see |
|---|---|---|
| D1 | Under **Pickup or delivery** choose **Pickup, free** | Summary shows "Pickup: Free" and the total |
| D2 | Choose **Bangkok delivery** and leave the area empty | A hint asks you to choose your delivery area |
| D3 | Choose an area, for example Asok | Delivery price and distance appear by themselves, total updates |
| D4 | Choose a different area | The delivery price changes |

## E. Pay: PromptPay

| Step | Do | You should see |
|---|---|---|
| E1 | In Order summary select **PromptPay**, click **Place order** | Payment page "Payment for order #…" with a QR picture, a reference like `HB-ORDER-…`, the amount and a countdown |
| E2 | Check the buttons | One green button "I've paid ฿…" and a small "Cancel payment and order" link. No decline or pay-later buttons |
| E3 | Click **I've paid** | "Payment received" with **Track your order** and **View receipt** |

## F. After payment

| Step | Do | You should see |
|---|---|---|
| F1 | Click **Track your order** | Order page with a progress line (Order placed, Payment received, Seller confirms, …) and a timeline entry "Payment received" |
| F2 | Click **View receipt** | Receipt with date, kitchen, items, ingredients, food and delivery totals, payment status "Paid" |
| F3 | Click **Orders** in the header | The order appears in your list |

## G. Pay: card (repeat C and D first)

| Step | Do | You should see |
|---|---|---|
| G1 | Add a dish again, choose **Card**, click **Place order** | A card picture with no input fields and a note that no card details are requested |
| G2 | Click **Pay ฿…** | "Payment received" |

## H. Pay: cash

| Step | Do | You should see |
|---|---|---|
| H1 | Add a dish again, choose **Cash on pickup** (or **Cash on delivery** if you picked delivery), click **Place order** | Order page straight away, status "Cash due", no payment screen |

## I. Cancel and edge cases

| Step | Do | You should see |
|---|---|---|
| I1 | Place a PromptPay order, then click **Cancel payment and order** | Order cancelled, portions released |
| I2 | Place an order and click **Place order** twice quickly | Only one order is created |
| I3 | Add more portions than are left | Refused with an explanation |
| I4 | Leave a payment page open for 15 minutes, then press pay | "Payment window closed" with a way to find food |

## J. Seller side (optional, to see the order move)

1. Sign out, sign in as the seller of the dish (for example `demo_seller_pakistan`, password in `.demo-credentials.txt`).
2. Open **Manage orders**, open your order, click **Confirm order**.
3. Click **Start preparing**, then **Mark ready for pickup** (or **Mark ready for delivery**).
4. Pickup: click **Complete pickup**. Delivery: **Send out for delivery**, **Mark delivered**, **Complete order**.
5. Sign back in as the buyer. The progress line should show each step.

## If something is wrong

```
Step:
Page address:
What I did:
What I expected:
What happened:
```
