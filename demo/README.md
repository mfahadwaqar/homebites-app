# Offline demo seed

After applying migrations, run `python manage.py seed_demo` to create the five fixed cuisine groups, 50 reviewed offers, eight fictional Bangkok locations, five distinct seller pickup points, and one standard plus one pre-order slot for each seller. Every offer receives 20 portions in each slot. Pickup and delivery are simulated; this command makes no external requests.

Running the command again preserves existing slots, used stock and the fictional `demo_buyer` account. Once a seeded slot has ended or its pre-order deadline has passed, a new future slot is created while the old slot and its historical stock remain available to past orders. The buyer starts with an unusable password. Set a local classroom password interactively with `python manage.py changepassword demo_buyer`; the seed never prints or resets it. If an unrelated account already uses that username, the command stops without adopting it.

See [the classroom handover](../docs/classroom-handover.md) for the setup, walkthrough, simulation boundaries, backup procedure and verified test matrix.

## Normal startup and refresh

Use `scripts/start-demo.ps1` from PowerShell after initial setup. It starts the local database, checks schema readiness, expires overdue online-payment reservations, and runs `refresh_demo_availability` before starting Django. Public browsing never refreshes schedules.

`python manage.py refresh_demo_availability` rotates only expired marked windows using their existing stock associations. It retains current used stock and intentional pauses, locks markers against concurrent refreshes, and reports incomplete original associations. New standard windows begin 30 minutes after preparation and last two hours. New pre-orders use 18:00–20:00 Bangkok time two calendar days ahead, deadline the preceding day at 18:00. Retained windows keep their actual displayed dates.

Staff can POST a refresh from `/demo/readiness/` during a long demonstration. Refresh preserves old windows, stock and order history; it is not a database reset. Seeded sellers remain unable to sign in; demonstrate seller actions using a separate fictional approved account.
