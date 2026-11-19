# HomeBites local testing guide

This guide tests the **simulated** HomeBites marketplace on your own Windows computer. It does not require payment, maps, courier, or email accounts. Use fictional names and addresses only; do not enter real card or bank details.

## 1. Prepare the app (first run only)

Open PowerShell in the `homebites-app` folder. You need Python 3.13, Docker Desktop, and Git. Start Docker Desktop before running the commands.

```powershell
Copy-Item .env.example .env
```

Edit `.env`: replace `DJANGO_SECRET_KEY` and `POSTGRES_PASSWORD` with your own local-only values. Leave the localhost host and port values as shown. Never commit `.env`.

```powershell
py -3.13 -m venv .venv
& .\.venv\Scripts\python.exe -m pip install -r requirements.txt
docker compose up -d --wait db
& .\.venv\Scripts\python.exe manage.py migrate
& .\.venv\Scripts\python.exe manage.py createsuperuser
& .\.venv\Scripts\python.exe manage.py seed_demo
& .\.venv\Scripts\python.exe manage.py changepassword demo_buyer
```

The last two account commands are interactive. Choose classroom-only passwords. The seed creates 50 dishes and 50 offers (10 dishes each from Thailand, Pakistan, Bangladesh, Nepal, and India), sample Bangkok locations, and order slots. Seeded seller accounts intentionally have unusable passwords; create a separate seller account for seller-flow testing.

## 2. Start and stop each testing session

```powershell
& .\scripts\start-demo.ps1
```

Open <http://127.0.0.1:8000/>. Keep the PowerShell window open while testing. Press `Ctrl+C` to stop Django. When finished, run `docker compose stop db` in PowerShell. **Do not use `docker compose down --volumes`** unless you deliberately want to delete the demo database.

The startup script checks migrations, releases overdue payment holds and refreshes expired marked demo windows. Current sold-out portions, intentional pauses, passwords and historical orders are preserved. Plain `runserver` skips this preparation. Staff can inspect `/demo/readiness/` and refresh during a long session. See [demo scenarios](demo-scenarios.md) and [behavior rules](behavior-rules.md).

## 3. Manual browser checklist

Use separate normal/incognito windows for buyer, seller, and staff when possible. This avoids repeatedly logging out. Record a pass/fail and any unexpected message for each step.

| Journey | Steps | Expected result |
|---|---|---|
| Browse and ingredients | Open `/food/`; search, filter by country, dietary label, price and availability; open a dish. | Results respond to filters. The detail page shows that seller's ingredients before purchase. The five-country master catalogue remains fixed at 50 dishes. Dietary labels are seller-declared; inspect ingredients yourself. |
| Buyer cart | Sign in as `demo_buyer`; add an available offer; change quantity; try adding a different seller's offer. | The cart persists for the signed-in buyer, checks stock and slot timing, and prevents mixing sellers/slots in one order. |
| Pickup checkout | Choose pickup, request a quote, and place a cash-on-pickup order. | Pickup fee is ฿0. The order page shows the food subtotal, 10% platform commission calculation where applicable, snapshots, and a status timeline. No real payment occurs. |
| Bangkok delivery | Start a separate cart/order; choose a sample Bangkok location, request a quote, and choose mock PromptPay or mock card. | Distance/fee are labelled simulated and calculated locally. The mock payment page asks for **no** real payment credentials. Select “Simulate success” and confirm the order changes state. |
| Pre-order | Choose a future pre-order slot for an available offer and complete checkout. | The slot/deadline is visible and honored. Expired or unavailable slots cannot be checked out. |
| Seller workflow | Register a fictional account at `/account/signup/`; apply at `/sellers/apply/`; approve it in `/admin/`. Sign in as the seller, set a pickup location at `/sellers/profile/edit/`, add an offer from the fixed dishes at `/sellers/offers/new/`, set a slot and stock at `/sellers/slots/`. Buy that offer from the buyer window, then use `/seller-orders/`. | Seller can manage only their own offer and order. Accept and record the simulated pickup/delivery handoff; the buyer's timeline updates. Rejected/cancelled orders release stock according to the workflow. |
| Reviews and moderation | After a completed order, submit one review from its buyer order page. As staff, open `/reviews/moderation/` and approve/reject it. Submit a seller/listing report and resolve it with a reason. | Review is pending until approved, appears publicly only after approval, and cannot be submitted twice for the same order. Moderation records an audit event. |
| Mobile/accessibility | Repeat browse, detail, cart, checkout and order view at a narrow browser width; navigate using Tab/Shift+Tab and keyboard activation. | Text and controls remain usable, focus is visible, labels and errors are understandable, and no horizontal clipping blocks the flow. |

There is no live courier tracking, escrow, external payment gateway, or real sales revenue. The seller dashboard and delivery/payment states are demonstration data.

## 4. Automated regression checks

With PostgreSQL running, use a **new PowerShell window** in the project root (the server may stay running in the first):

```powershell
& .\.venv\Scripts\python.exe manage.py test --verbosity 1
& .\.venv\Scripts\python.exe manage.py check
& .\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
& .\.venv\Scripts\python.exe manage.py migrate --check
```

Expected: all tests pass, system check reports no issues, migration generation reports `No changes detected`, and the migration check exits successfully. Django uses a separate PostgreSQL **test database** for the test suite, not the demo database. The last verified full run (2026-10-04) passed 137 tests; the count may change as tests are added.

To check only demo seeding:

```powershell
& .\.venv\Scripts\python.exe manage.py test demo.tests.test_seed_demo --verbosity 1
```

For overdue simulated payment holds in the local demo database, run:

```powershell
& .\.venv\Scripts\python.exe manage.py expire_demo_holds
```

This expires only overdue holds and releases their reservations; it is not a database reset. Running `seed_demo` again also does **not** reset existing orders or used stock.

## 5. If something fails

- **Docker connection/permission error:** Start Docker Desktop, wait for its engine, then run `docker version` and `docker compose up -d --wait db` again.
- **Database connection error:** Check `.env`, `docker compose ps`, and whether host port `54329` is available. Django has no SQLite fallback.
- **`demo_buyer` cannot sign in:** Run `manage.py changepassword demo_buyer` interactively. The seed never sets a usable password.
- **Seller cannot publish or handle orders:** Confirm the seller was approved in Admin, has a pickup location, and has an offer with reviewed ingredients, a future slot, and stock.
- **No offer/slot is available:** Run `manage.py seed_demo` to rotate expired seeded slots. It preserves historical orders and stock usage.
- **Password reset email did not arrive:** Development email is printed in the Django server terminal, not sent externally.

For a deeper classroom walkthrough and database backup/restore drill, see [classroom-handover.md](classroom-handover.md). For environment details, see [development.md](development.md).
