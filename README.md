# HomeBites

HomeBites is a locally runnable university demonstration of a Bangkok-wide marketplace for homemade and independent food. It uses real Django and PostgreSQL records while clearly simulating payments, delivery progress and location pricing.

The fixed catalogue contains 50 dishes: 10 each from Thailand, Pakistan, Bangladesh, Nepal and India. Each seller offer has its own reviewed ingredient list.

## Current status

The repository includes the following local demonstration flows:

- Django 5.2 LTS and PostgreSQL 17.
- Customer accounts, food discovery, a single-seller cart, simulated checkout and order tracking.
- Seller approval, offers, slots, stock, order handling and simulated sales statistics.
- Mock payments, eligible reviews, content reports and staff moderation.
- An idempotent offline demo seed with 50 offers, five pickup points and 100 initial stock records.

The [milestone roadmap](docs/milestones.md) records what has actually been verified. See the [classroom handover](docs/classroom-handover.md) for the walkthrough, evidence matrix and backup procedure.

## Requirements

- Windows with Python 3.13 available through `py -3.13`.
- Docker Desktop running.
- Git.

No payment, mapping, courier, email-delivery or hosting account is required.

## First-time setup

Run these commands from the project directory in PowerShell:

```powershell
Copy-Item .env.example .env
```

Replace the development secret and database password in `.env`, then run:

```powershell
py -3.13 -m venv .venv
& .\.venv\Scripts\python.exe -m pip install -r requirements.txt
docker compose up -d --wait db
& .\.venv\Scripts\python.exe manage.py migrate
& .\.venv\Scripts\python.exe manage.py createsuperuser
& .\.venv\Scripts\python.exe manage.py seed_demo
& .\.venv\Scripts\python.exe manage.py changepassword demo_buyer
```

`seed_demo` creates a fictional buyer with an unusable password. `changepassword` prompts for a local password without placing it in the command or repository. Re-running the seed preserves that password, stock usage and current slot IDs. Do not use a personal password for classroom accounts.

## Run locally

```powershell
docker compose up -d --wait db
& .\.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000
```

Open <http://127.0.0.1:8000/>. Keep the site on localhost; this prototype is not approved for public hosting.

## Run checks

```powershell
& .\.venv\Scripts\python.exe manage.py test
& .\.venv\Scripts\python.exe manage.py check
& .\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
```

Detailed setup and troubleshooting are in [docs/development.md](docs/development.md). The [classroom handover](docs/classroom-handover.md) explains the full scenario and its current verification limits.

## Stop the database

```powershell
docker compose stop db
```

Use `docker compose down` only when you intend to remove the container and network. Do not add `--volumes` unless you explicitly want to erase the HomeBites demonstration database.

