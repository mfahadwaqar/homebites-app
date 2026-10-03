# HomeBites Foundation and Accounts Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Establish a reproducible Django/PostgreSQL development foundation with a custom user model and complete local account flow.

**Architecture:** A Django monolith connects only to PostgreSQL. The accounts app owns the custom user, signup form and account routes; Django's authentication views own login/logout/password-reset behavior. Server-rendered templates provide an accessible functional shell while detailed marketplace visual design remains deferred.

**Tech Stack:** Python 3.13, Django 5.2 LTS, PostgreSQL 17 via Docker Compose, psycopg 3, HTML/CSS/Bootstrap-compatible markup, Django test runner.

**Spec:** `docs/superpowers/specs/2026-10-04-homebites-design.md`

## Global Constraints

- Run application and tests against PostgreSQL, never SQLite.
- Create and configure `accounts.User` before the first migration.
- Keep payment, mapping, email delivery and hosting external integrations out of M1.
- Bind development only to localhost and keep `.env` out of Git.
- Follow test-first RED → GREEN development for behavior.
- Preserve the exact five-country/50-dish scope for later milestones without implementing catalogue behavior in M1.

## Review Focus

- Duplicate username or invalid signup data must redisplay the form without creating a user.
- Authenticated users visiting signup/login must not accidentally create duplicate sessions or accounts.
- Password-reset requests must not reveal whether an address exists.
- Anonymous users must not access the account profile.
- Production-like checks must reject missing critical configuration rather than silently using insecure defaults.

---

### Task 1: Reproducible Django/PostgreSQL scaffold

**Files:**
- Create: `requirements.in`
- Create: `requirements.txt`
- Create: `.env.example`
- Create: `compose.yaml`
- Create: `manage.py`
- Create: `config/__init__.py`
- Create: `config/settings.py`
- Create: `config/urls.py`
- Create: `config/wsgi.py`
- Create: `core/__init__.py`
- Create: `core/apps.py`
- Create: `core/views.py`
- Create: `core/tests/test_health.py`
- Create: `templates/base.html`
- Create: `templates/core/home.html`
- Create: `static/css/homebites.css`

**Interfaces:**
- Consumes: environment variables from `.env.example`: `DJANGO_SECRET_KEY`, `DJANGO_DEBUG`, `DJANGO_ALLOWED_HOSTS`, `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST`, `POSTGRES_PORT`.
- Produces: route name `home`; PostgreSQL-backed Django settings; test command `.venv\\Scripts\\python.exe manage.py test`.

- [ ] Install pinned Django/psycopg dependencies into `.venv` and record resolved versions.
- [ ] Add the minimum Django configuration and local PostgreSQL Compose service.
- [ ] Write `core.tests.test_health.HomePageTests.test_home_page_identifies_simulated_marketplace` asserting HTTP 200 and the visible phrases `HomeBites` and `university demonstration`.
- [ ] Run the test and verify RED because the `home` route/view is absent.
- [ ] Implement `core.views.HomeView` and the `home` route/template.
- [ ] Run the focused test and verify GREEN.
- [ ] Run `manage.py check` and the complete test suite.
- [ ] Commit `chore: scaffold Django PostgreSQL foundation`.

### Task 2: Custom user model and administrator registration

**Files:**
- Create: `accounts/__init__.py`
- Create: `accounts/apps.py`
- Create: `accounts/models.py`
- Create: `accounts/admin.py`
- Create: `accounts/tests/__init__.py`
- Create: `accounts/tests/test_user_model.py`
- Modify: `config/settings.py`

**Interfaces:**
- Consumes: Django auth and the PostgreSQL scaffold from Task 1.
- Produces: `accounts.User(AbstractUser)` with `display_name: str`; `AUTH_USER_MODEL = "accounts.User"`; User registered with Django Admin.

- [ ] Write tests asserting the configured user model is `accounts.User`, `display_name` persists and the model is registered with Admin.
- [ ] Run the focused tests and verify RED because the accounts app/model does not exist.
- [ ] Implement the minimal custom user and admin registration, then create initial migrations.
- [ ] Run migrations, focused tests and the full suite; verify GREEN.
- [ ] Commit `feat: add custom HomeBites user`.

### Task 3: Signup and protected profile

**Files:**
- Create: `accounts/forms.py`
- Create: `accounts/views.py`
- Create: `accounts/urls.py`
- Create: `accounts/tests/test_signup.py`
- Create: `accounts/tests/test_profile.py`
- Create: `templates/accounts/signup.html`
- Create: `templates/accounts/profile.html`
- Modify: `config/urls.py`
- Modify: `templates/base.html`

**Interfaces:**
- Consumes: `accounts.User` from Task 2.
- Produces: `accounts.forms.SignUpForm`; route names `accounts:signup` and `accounts:profile`; successful signup redirects to `login`.

- [ ] Write signup tests for GET, valid creation and invalid duplicate username without user creation.
- [ ] Write profile tests proving anonymous redirect and authenticated access.
- [ ] Run focused tests and verify RED because routes/forms/views are absent.
- [ ] Implement the minimal form, class-based views, routes and accessible templates.
- [ ] Run focused tests and the full suite; verify GREEN.
- [ ] Commit `feat: add signup and account profile`.

### Task 4: Login, logout and local password-reset preview

**Files:**
- Create: `accounts/tests/test_authentication.py`
- Create: `templates/registration/login.html`
- Create: `templates/registration/logged_out.html`
- Create: `templates/registration/password_reset_form.html`
- Create: `templates/registration/password_reset_done.html`
- Create: `templates/registration/password_reset_email.html`
- Create: `templates/registration/password_reset_subject.txt`
- Create: `templates/registration/password_reset_confirm.html`
- Create: `templates/registration/password_reset_complete.html`
- Modify: `config/settings.py`
- Modify: `config/urls.py`
- Modify: `templates/base.html`

**Interfaces:**
- Consumes: Django auth views and `accounts.User`.
- Produces: Django route names `login`, `logout`, `password_reset`, `password_reset_done`, `password_reset_confirm`, `password_reset_complete`; console email in development and in-memory email in tests.

- [ ] Write tests for valid login, POST-only logout behavior, generic password-reset response for existing/unknown emails and reset-email generation.
- [ ] Run focused tests and verify RED because auth routes/templates are absent.
- [ ] Add Django auth routes, settings and templates with localhost-safe redirects.
- [ ] Run focused tests and the full suite; verify GREEN.
- [ ] Commit `feat: complete local account authentication`.

### Task 5: Foundation verification and handover

**Files:**
- Create: `README.md`
- Create: `docs/development.md`
- Modify: `docs/milestones.md`
- Modify: `.env.example`

**Interfaces:**
- Consumes: complete M1 runtime and tests.
- Produces: reproducible Windows setup/start/test instructions and M0/M1 evidence in `docs/milestones.md`.

- [ ] Document Docker/PostgreSQL startup, virtual environment setup, migrations, superuser creation, server startup and tests.
- [ ] Run all tests, `manage.py check`, `manage.py check --deploy` with documented expected local-development warnings, and migration consistency checks.
- [ ] Start the localhost app and exercise home, signup, login, profile, logout and password-reset pages in a browser at desktop and mobile widths.
- [ ] Record actual evidence and update M0/M1 status only if every gate is met.
- [ ] Commit `docs: record foundation setup and verification`.

## Plan self-review

- Spec coverage: M1 foundation, PostgreSQL, custom user, accounts, local-only operation and testing are covered; catalogue and marketplace behavior remain explicitly deferred.
- Shared interfaces: Task 1 supplies settings and test command; Task 2 supplies the user model; Tasks 3–4 consume it; Task 5 verifies the assembled system.
- Review-focus coverage: duplicate signup, authenticated/anonymous routing, enumeration-safe password reset and configuration checks are assigned to Tasks 3–5.
- Proportion: tasks specify interfaces and observable assertions without transcribing implementation bodies.

