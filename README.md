# HomeBites

HomeBites is a locally runnable university demonstration of a Bangkok-wide marketplace for homemade and independent food. It uses real Django and PostgreSQL records while clearly simulating payments, delivery progress and location pricing.

The confirmed catalogue scope is 50 dishes: 10 each from Thailand, Pakistan, Bangladesh, Nepal and India. Ingredient lists are required on seller offers and will be added in Milestone M2.

## Current status

Milestones M0 and M1 are complete. The next implementation slice is M2: Sellers and fixed food catalogue. The current implementation includes:

- Django 5.2 LTS and PostgreSQL 17.
- A custom HomeBites user model.
- Registration, login, POST-only logout and a protected profile.
- Local password-reset email preview.
- Django Admin user management.
- Automated tests running against PostgreSQL.

See [the milestone roadmap](docs/milestones.md) and [the complete implementation plan](docs/homebites-implementation-plan.md).

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
```

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

Detailed setup, troubleshooting and development decisions are in [docs/development.md](docs/development.md).

## Stop the database

```powershell
docker compose stop db
```

Use `docker compose down` only when you intend to remove the container and network. Do not add `--volumes` unless you explicitly want to erase the HomeBites demonstration database.

