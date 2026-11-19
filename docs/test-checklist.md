# HomeBites local test checklist

Server: http://127.0.0.1:8000 · Logins in `.demo-credentials.txt` (`demo_buyer`, `demo_admin`).
Tick each box as you go. Note anything that fails with the page URL.

## A. Visitor (not signed in)
- [ ] `/` Home: hero, search box, trust chips, 5 cuisine tiles with photos, kitchens and dishes grids load
- [ ] Hero search "biryani" → lands on `/food/?q=biryani` with matching dishes
- [ ] Cuisine tile (e.g. Nepal) → catalogue filtered to 10 Nepal dishes
- [ ] `/food/` shows 50 offers (check pagination if present), real photos with credit line
- [ ] Each card: calorie chip, serving size, diet tag (veg/vegan), availability pill, price
- [ ] Filters: country, "Refine results" (diet, min/max price, Accepting orders), Reset
- [ ] Empty search (e.g. "zzzz") shows friendly empty state
- [ ] Dish page: photo + credit/licence links, ingredients, calorie box with serving and source, order windows, seller + reviews + report links
- [ ] Add to cart while signed out → sent to sign in (not an error page)
- [ ] Seller storefront (`/sellers/<id>/`) lists that kitchen's dishes
- [ ] Mobile width (Chrome DevTools, 390px): header menu button, hero, cards, filters all usable, no sideways scroll

## B. Customer (`demo_buyer`)
- [ ] Sign in at `/accounts/login/`; header shows Cart, Orders, Profile
- [ ] Dish page → pick slot + quantity → Add to cart
- [ ] `/orders/cart/` shows item, totals; change quantity; remove item
- [ ] Add a dish from a different kitchen → cart asks to replace (one kitchen per cart)
- [ ] Choose **Pickup** → quote is ฿0 delivery
- [ ] Choose **Delivery** + a Bangkok location → distance-based fee, marked simulated
- [ ] Place order (checkout) → order page with price and ingredient snapshot
- [ ] Pay: PromptPay / card / cash-on-pickup simulated screens; no real card data asked
- [ ] Try a failed payment, then retry; order does not duplicate
- [ ] Order timeline updates after the seller acts (section C)
- [ ] Cancel an unpaid order → stock released
- [ ] Pre-order slot: shows deadline, can be ordered before it
- [ ] After order is completed: leave a review (once only)
- [ ] Report a seller / listing from its page
- [ ] `/account/profile/` shows your details; sign out works

## C. Seller
- [ ] Sign up a new account `/account/signup/`, apply `/sellers/apply/`
- [ ] Approve it in `/admin/` (as `demo_admin`): Sellers → set approved
- [ ] `/sellers/profile/edit/`: storefront name, description, pickup location
- [ ] `/sellers/offers/new/`: only the fixed 50-dish catalogue is choosable; cannot publish without ingredients
- [ ] Optional kcal fields: all four set together; editing ingredients clears them
- [ ] Upload a photo (wrong file type is rejected; seller photo beats catalogue photo)
- [ ] `/sellers/slots/`: create standard and pre-order slot, set stock per dish
- [ ] `/sellers/dashboard/`: counts and totals; 10% commission shown, labelled simulated
- [ ] `/seller-orders/`: accept customer order → mark ready/handed off → completed
- [ ] Customer's timeline reflects each step; delivery vs pickup states differ

## D. Admin / staff (`demo_admin`)
- [ ] `/admin/` manages users, sellers, dishes, listings, orders
- [ ] `/demo/readiness/` shows demo status; Refresh works
- [ ] `/reviews/moderation/`: approve/reject a review, resolve a report with a reason

## E. Edge / failure states
- [ ] Sold-out or paused dish shows clear message, cannot be added
- [ ] Quantity larger than stock is refused with explanation
- [ ] Buyer cannot open seller pages or other users' orders (forbidden/redirect)
- [ ] Double-click Place order → only one order
- [ ] Unknown URL gives a normal 404 page

## F. Promised in proposal: quick tick
- [ ] 5 countries × 10 dishes = 50 (Thailand, Pakistan, Bangladesh, Nepal, India)
- [ ] Search and filters · seller ingredients shown before buying · calorie info
- [ ] Standard orders and pre-orders · pickup and distance-based delivery
- [ ] Payment options incl. cash · order tracking · reviews · seller dashboard · admin moderation
- [ ] Real food photos with credits (`docs/food-photo-credits.md`)

## Known limits (say these in the demo)
- Payments, delivery and locations are simulated; no real money or courier.
- Calories are reference-recipe estimates; portions vary.
- A few photos are the nearest regional variant (labelled "representative").
