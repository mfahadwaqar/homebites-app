# HomeBites Development Guide

## Runtime architecture

The browser connects to one server-rendered Django application. Django owns authentication, forms, templates and marketplace workflows. PostgreSQL stores all persistent project data and runs in the `homebites-db` Docker container.

The repository deliberately does not use SQLite, React, a separate REST API, Redis, Celery or live third-party services.

## Environment variables

Copy `.env.example` to `.env`. Django reads the local file without overriding variables already provided by the process. Docker Compose reads the same file for PostgreSQL.

Required values:

- `DJANGO_SECRET_KEY`
- `DJANGO_DEBUG`
- `DJANGO_ALLOWED_HOSTS`
- `POSTGRES_DB`
- `POSTGRES_USER`
- `POSTGRES_PASSWORD`
- `POSTGRES_HOST`
- `POSTGRES_PORT`
- `DJANGO_EMAIL_BACKEND`

The committed example values are placeholders. `.env` is ignored by Git.

## Database lifecycle

Start PostgreSQL:

```powershell
docker compose up -d --wait db
docker compose ps
```

Apply migrations:

```powershell
& .\.venv\Scripts\python.exe manage.py migrate
```

Stop PostgreSQL without deleting data:

```powershell
docker compose stop db
```

The named volume `homebites_postgres_data` persists database content. Removing that volume is destructive and is not part of normal development.

## Accounts and local email

Create an administrator with `manage.py createsuperuser`. Ordinary users register at `/account/signup/`; their protected profile is at `/account/profile/`.

Run `manage.py seed_demo` after migrations to create a fictional `demo_buyer` account, the fixed catalogue, Bangkok sample points, and seller slots/stock. The buyer starts with an unusable password. Set a local password interactively with `manage.py changepassword demo_buyer`; rerunning the seed preserves it. A pre-existing unmarked account named `demo_buyer` makes the command stop without adopting or modifying that account.

Password reset uses Django's console email backend in development. Submitting the reset form prints the message and local reset link in the server terminal. Tests use Django's in-memory email backend. No external email is sent.

## Tests

The normal project gate is:

```powershell
docker compose up -d --wait db
& .\.venv\Scripts\python.exe manage.py test --verbosity 1
& .\.venv\Scripts\python.exe manage.py check
& .\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
```

Django creates and removes a PostgreSQL test database. A test result is not accepted if PostgreSQL is unavailable or if the settings silently fall back to another database engine.

For a focused demo-seed check, run `& .\.venv\Scripts\python.exe manage.py test demo.tests.test_seed_demo --noinput`. The [classroom handover](classroom-handover.md) has the walkthrough, requirement matrix and a restore drill that keeps the live database untouched.

`manage.py check --deploy` is also run during milestone verification. Because this is a localhost development configuration with `DEBUG=true`, it is expected to warn about deployment-only HTTPS, secure-cookie and HSTS settings. Those warnings are recorded rather than suppressed; public deployment is explicitly out of scope.

## TDD workflow

For behavior changes:

1. Write one test describing the observable behavior.
2. Run it and confirm it fails for the missing behavior.
3. Implement the smallest change that makes it pass.
4. Run the focused test and the complete suite.
5. Commit only after the checks are green.

## Milestone workflow

Work happens on milestone branches. Update [milestones.md](milestones.md) only after the milestone's acceptance gates have fresh evidence. Do not begin live integration work or add countries/dishes beyond the confirmed scope without an approved plan change.

## Troubleshooting

### Port 54329 is already in use

Stop the conflicting local process or select another unused host port in `.env`. The container always listens on port 5432 internally.

### Docker reports permission or daemon errors

Start Docker Desktop and wait for its engine to become ready, then run `docker version` and retry `docker compose up -d --wait db`.

### Django reports a missing environment variable

Confirm `.env` exists in the project root and contains every variable listed above. Do not commit `.env`.

### Python cannot create the virtual environment

Confirm the project directory is writable. On managed environments that restrict the system temporary directory, set `TEMP` and `TMP` to a writable project-local temporary directory only for the environment-creation command.

