# HomeBites classroom handover

HomeBites is a localhost-only Django/PostgreSQL demonstration. Orders, payments, delivery distances, courier progress and sales figures are simulated. Do not enter real card, bank, address or customer information. No external payment, mapping or courier service is called.

## Fresh Windows setup

Use PowerShell from the repository root with Python 3.13, Docker Desktop and Git installed. Start Docker Desktop first. Keep the project and its `.env` file local.

```powershell
Copy-Item .env.example .env
```

Edit `.env` to set a fresh `DJANGO_SECRET_KEY` and `POSTGRES_PASSWORD`. Keep `POSTGRES_HOST=127.0.0.1` and `DJANGO_ALLOWED_HOSTS=127.0.0.1,localhost` for the local run. Then:

```powershell
py -3.13 -m venv .venv
& .\.venv\Scripts\python.exe -m pip install -r requirements.txt
docker compose up -d --wait db
& .\.venv\Scripts\python.exe manage.py migrate
& .\.venv\Scripts\python.exe manage.py createsuperuser
& .\.venv\Scripts\python.exe manage.py seed_demo
& .\.venv\Scripts\python.exe manage.py changepassword demo_buyer
& .\scripts\start-demo.ps1
```

`changepassword` prompts twice; choose a unique classroom-only password. The seed creates `demo_buyer` with an unusable password, never prints a usable one, and preserves a password set later. Seeded seller accounts have unusable passwords. Do not use personal passwords for this demo. The seed refuses to adopt an unrelated account already named `demo_buyer`.

The seed creates five countries, 50 master dishes and 50 public offers with seller-specific ingredients. Eight fictional Bangkok locations support quotes. Five seller pickup points are assigned at Ari, Asok, Silom, Chatuchak and Bang Na. Each seeded seller receives one standard and one pre-order slot; all 50 offers receive 20 portions in each slot. Running the command again preserves used stock and current slot IDs. An expired slot rotates to a new future slot while its old stock remains for historical orders.

## Classroom walkthrough

For the current behavior pass, follow [demo-scenarios.md](demo-scenarios.md) and [behavior-rules.md](behavior-rules.md). Demo dates are time-sensitive: normal startup refreshes expired marked windows, and staff can refresh them at `/demo/readiness/`. Standard booking ends 30 minutes before fulfillment ends; pre-orders use an explicit deadline. Published offers and offers accepting orders are distinct.

1. Open <http://127.0.0.1:8000/food/>. Search for a dish, filter by country and price, and show the open-slot filter. Open a food detail page to inspect that seller's ingredients and price. The 50 seeded offers span the five cuisine groups.
2. Sign in as `demo_buyer`. Add an offer to the cart, select pickup, calculate the zero-fee quote, and place a cash-on-pickup simulated order. The order detail page shows price and ingredient snapshots. Repeat with a different seller as a separate order to demonstrate the many-to-many marketplace.
3. For a delivery quote, choose one of the eight demo Bangkok locations in the cart. The fee and distance are local estimates, not real routing or delivery commitments. Try mock PromptPay or mock card with the on-page outcome controls; no payment credentials are requested and no money moves.
4. For a seller-managed completion journey, register a separate fictional seller account at `/account/signup/`, apply at `/sellers/apply/`, and approve it in Django Admin. As that seller, set a pickup location at `/sellers/profile/edit/`, create an offer from the fixed catalogue at `/sellers/offers/new/`, then create a future slot and portions at `/sellers/slots/`. Place an order for this offer as `demo_buyer`. The seller can accept and record the simulated handoff at `/seller-orders/`.
5. After the order is completed, the buyer can open its detail page and submit one review. A staff user can approve it at `/reviews/moderation/`; the approved review and average then appear at `/reviews/sellers/<seller-id>/`. Submit a seller or listing report through its public page and record a reasoned staff resolution in the same moderation queue. The review and report decisions create audit events.
6. Show the seller dashboard, order timeline and mock totals. Platform commission starts at 10% of the food subtotal; delivery charges are separate. Do not describe these figures as real revenue.

The seeded seller identities cannot sign in. The separate seller account in step 4 is the safe way to demonstrate seller actions while keeping `seed_demo` repeatable. Additional seller offers do not expand the fixed 50-dish master catalogue.

## Backup and restore drill

Store backups **outside the repository** because they contain account records and password hashes. The commands below copy a PostgreSQL custom-format backup without piping binary data through PowerShell text redirection. The restore goes to a new scratch database and leaves the live `POSTGRES_DB` untouched.

```powershell
$backupDir = Join-Path $env:USERPROFILE 'HomeBitesBackups'
New-Item -ItemType Directory -Path $backupDir -Force
$backupFile = Join-Path $backupDir ('homebites-' + (Get-Date -Format 'yyyyMMdd-HHmmss') + '.backup')
docker compose exec -T db sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc -f /tmp/homebites-demo.backup'
docker cp homebites-db:/tmp/homebites-demo.backup $backupFile
Get-Item -LiteralPath $backupFile
```

To verify restoration, use an explicit scratch database name. `createdb` fails if that name already exists, so the procedure does not overwrite an earlier restore:

```powershell
docker cp $backupFile homebites-db:/tmp/homebites-restore.backup
docker compose exec -T db sh -c 'createdb -U "$POSTGRES_USER" homebites_restore_check'
docker compose exec -T db sh -c 'pg_restore -U "$POSTGRES_USER" -d homebites_restore_check --no-owner --no-acl /tmp/homebites-restore.backup'
docker compose exec -T db sh -c 'psql -U "$POSTGRES_USER" -d homebites_restore_check -tAc "SELECT (SELECT count(*) FROM catalog_dish), (SELECT count(*) FROM orders_listingstock)"'
```

After a seeded backup, the final query should return `50|100` before any orders use stock. If the scratch database exists, choose a new scratch name consistently in both commands rather than dropping or replacing it. Keep and protect the local backup according to your institution's data handling rules. Confirm the exact scratch database name with `docker compose exec -T db sh -c 'psql -U "$POSTGRES_USER" -d postgres -lqt'` before removing it; never drop the live `POSTGRES_DB`.

On 2026-10-04, a binary `pg_dump` of the local demo database was copied to a temporary ignored file on Windows, copied back into the container, and restored with `pg_restore` to disposable database `homebites_restore_check_codex_20261004b`. The read-only restored query returned `50|100`. An exact-name database listing preceded removal of that disposable database. Temporary proof backups were removed after verification; the live `homebites` database was not modified by this drill.

## Requirement and test evidence

| Requirement | Check | Evidence as of 2026-10-04 |
|---|---|---|
| Five countries, 50 dishes/offers and ingredient-visible discovery | `python manage.py test catalog.tests.test_discovery` | 11 focused PostgreSQL tests passed earlier in this implementation session. |
| Repeatable demo seed, five pickup points, 10 current slots and 100 stock rows | `python manage.py test demo.tests.test_seed_demo --noinput` | 5/5 PostgreSQL tests passed, including buyer password preservation, collision refusal and expired-slot rotation. |
| Eligible reviews and audited moderation | `python manage.py test reviews.tests --noinput` | 11/11 PostgreSQL tests passed in this implementation session. |
| Schema and configuration | `python manage.py check`; `python manage.py makemigrations --check --dry-run` | System check reported no issues; migration check reported no changes. The latter warned that the isolated base database name used for tests did not exist; the PostgreSQL test databases were created successfully. |
| Complete regression suite | `python manage.py test --noinput` | Latest completed isolated PostgreSQL run passed 137/137 tests on 2026-10-04. |
| Backup and restore | Binary `pg_dump`, Windows `docker cp`, isolated `pg_restore`, row-count query | Passed on 2026-10-04: disposable restore returned `50|100`; exact-name check preceded scratch database removal. Temporary proof copies were removed. |
| Browser walkthrough | Playwright/Chrome at 1440×900 and 390×844 | Home, catalogue, country filter and ingredient detail passed with zero console/page errors or external requests. Mobile buyer signup → cart → delivery quote → mock PromptPay success passed. Seller confirmation → simulated delivery handoff → dashboard passed; buyer review submission reached pending moderation. Screenshots were saved outside the repository in the Codex workspace. Staff moderation was not browser-verified. |
| Fresh Windows checkout | Local clean Git checkout and disposable PostgreSQL database | Applied all migrations, seeded 50 dishes/50 offers/100 stock rows, reran the seed with unchanged counts, and passed system and migration checks on 2026-10-04. The exact disposable database and checkout were removed afterward. |

For normal development commands and troubleshooting, see [development.md](development.md). The [milestone ledger](milestones.md) remains the authority for completion status.
