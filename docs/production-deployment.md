# SlotBridge free deployment

## Selected services

The deployment uses only free resources:

- Render Free Web Service for the Dockerized FastAPI backend;
- Supabase Free for PostgreSQL only.

Deployed resources:

- API: <https://slotbridge-api.onrender.com>;
- Render service: `slotbridge-api`, Frankfurt, `free` plan;
- Supabase project: `slotbridge`, Frankfurt (`eu-central-1`), Free plan;
- liveness: <https://slotbridge-api.onrender.com/api/v1/health/live>;
- readiness: <https://slotbridge-api.onrender.com/api/v1/health/ready>.

Supabase Auth, PostgREST, Storage, Realtime, and Edge Functions are not part of
the application architecture. SlotBridge continues to own registration, JWT
authentication, RBAC, tenant isolation, scheduling, and transactional booking.

Koyeb was rejected because its current account validation requires a payment
method. Render documents that its free deployment requires no payment:
<https://render.com/docs/your-first-deploy>.

## Free-tier limitations

This is a portfolio deployment, not an always-warm commercial service:

- Render Free spins down after 15 minutes without inbound traffic. The next
  request wakes it and can take about a minute:
  <https://render.com/docs/free>.
- Supabase Free may pause a project after a week of low database activity. It
  can be restored from the dashboard:
  <https://supabase.com/docs/guides/platform/free-project-pausing>.
- Render Free has no persistent disk. This does not affect the booking domain,
  because all users, memberships, schedules, services, and appointments live in
  Supabase PostgreSQL. The preserved legacy SQLite demo is intentionally
  ephemeral in production.

The Android app remains independent of the laptop. A sleeping free service can
cause a cold-start delay, but neither the laptop nor local Docker is involved.
The production Flutter client allows up to 90 seconds for the first response so
the initial request can survive that wake-up delay.

## Architecture compatibility audit

```text
Android app
    │ HTTPS
    ▼
Render Free Web Service
    │ SQLAlchemy + psycopg + TLS
    ▼
Supabase Free PostgreSQL
```

The existing architecture is compatible:

- Render builds the root `Dockerfile`, supplies `PORT`, terminates public TLS,
  provides logs, and exposes a stable `*.onrender.com` HTTPS URL.
- `scripts/entrypoint.sh` waits for PostgreSQL, runs
  `alembic upgrade head`, then starts Uvicorn on `PORT`.
- SQLAlchemy uses the psycopg 3 driver and `pool_pre_ping`.
- The Supabase Shared Pooler in **Session mode** on port `5432` supports normal
  PostgreSQL sessions and is suitable for a persistent web backend. Transaction
  pooler port `6543` is not used.
- `sslmode=require` is mandatory in production configuration.
- Migration `20260911_0003` creates `btree_gist` and the GiST exclusion
  constraint for active appointment ranges.
- Deployment migration `20260915_0004` revokes all SlotBridge table privileges
  from Supabase's `anon`, `authenticated`, and `service_role` roles, plus
  `PUBLIC`, and removes automatic table grants for the migration owner.
  Supabase Data API cannot bypass FastAPI's authorization. SQLAlchemy's
  database owner retains access. No booking tables or data are changed.
  This security boundary is deliberately retained on migration rollback.
- Idempotency uses `pg_advisory_xact_lock`, so the lock remains scoped to the
  booking transaction. Transactions, unique constraints, exclusion constraints,
  RBAC queries, and tenant filters remain unchanged.

Supabase connection guidance:
<https://supabase.com/docs/guides/database/connecting-to-postgres>.
Supabase Data API grant guidance:
<https://supabase.com/docs/guides/api/securing-your-api>.

## Render Blueprint

`render.yaml` declares exactly one Docker Web Service:

- service plan: `free`;
- region: Frankfurt;
- health check: `/api/v1/health/ready`;
- generated Render-side `JWT_SECRET`;
- `DATABASE_URL` requested as a secret during first Blueprint creation;
- no disk, worker, cron job, paid database, or paid instance.

The production database is external Supabase PostgreSQL, so the Blueprint does
not create Render PostgreSQL.

## Supabase DATABASE_URL

In the Supabase project dashboard, use **Connect → Session pooler**. Keep the
provided host, username, and port `5432`; URL-encode reserved characters in the
database password; append `sslmode=require`.

Format only:

```text
postgresql://postgres.<project-ref>:<URL-encoded-password>@<pooler-host>:5432/postgres?sslmode=require
```

Store the completed URL only in Render's secret environment variable
`DATABASE_URL`. Never place it in Git, `.env.production.example`, screenshots,
logs, chat messages, or Flutter.

## Environment variables

The non-secret Render values are defined by `render.yaml`:

- `SLOTBRIDGE_ENVIRONMENT=production`
- `JWT_ALGORITHM=HS256`
- `JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30`
- `AVAILABILITY_SLOT_INTERVAL_MINUTES=15`
- `PUBLIC_DEMO_REGISTRATION_ENABLED=true`
- `PUBLIC_DEMO_ORGANIZATION_SLUG=slotbridge-demo`
- `PRODUCTION_DEMO_SEED_ENABLED=false`
- `ALLOW_UNSIGNED_DEMO_WEBHOOKS=false`
- `SLOTBRIDGE_DB_PATH=/tmp/slotbridge.db`
- `SLOTBRIDGE_DEMO_MODE=false`

Render generates `JWT_SECRET`. `DATABASE_URL` is entered as a secret. Native
Flutter does not need CORS, so `CORS_ALLOWED_ORIGINS` remains empty.

The live service stores `DATABASE_URL` and `JWT_SECRET` only as Render
environment secrets. The deployment workstation keeps its generated database,
JWT, and one-shot demo-seed credentials outside the repository in Windows
DPAPI-encrypted credential files under `%APPDATA%\SlotBridge`. They are never
written to `.env`, source files, build arguments, Flutter, or Git.

## Migrations and one-time seed

With the Supabase production URL present only in the current process:

```powershell
$env:SLOTBRIDGE_ENVIRONMENT = 'production'
$env:DATABASE_URL = '<Supabase Session pooler URL with sslmode=require>'
$env:JWT_SECRET = '<temporary generated value used only for this command>'
python -m alembic upgrade head
```

The deployed service also applies migrations on every cold start. Alembic is
idempotent and does not recreate the database.

For the one-time portfolio seed, additionally set a generated
`DEMO_PASSWORD` and `PRODUCTION_DEMO_SEED_ENABLED=true`, then run:

```powershell
python scripts/seed_production_demo.py
```

Afterward, remove `DEMO_PASSWORD` and restore
`PRODUCTION_DEMO_SEED_ENABLED=false`. Production startup never invokes a seed.

Verify the actual connection after migration:

```powershell
python scripts/check_production_database.py
```

The check reports only the driver, SSL state, Alembic revision, `btree_gist`,
exclusion-constraint state, and number of tables exposed to Data API roles
(must be zero). It does not print the database URL or password.

Run the safe two-request production concurrency check with:

```powershell
$env:SLOTBRIDGE_PRODUCTION_API_URL = 'https://slotbridge-api.onrender.com'
python scripts/check_production_concurrency.py
```

It registers two throwaway clients, sends two bookings for one slot, requires
the result to be one `201` and one `409`, and cancels the winning appointment.

## Completion gate

Deployment is complete only after recording:

- both health endpoints returning 200 over Render HTTPS;
- Supabase connection using psycopg and SSL;
- Alembic revision `20260915_0004 (head)`;
- remote registration, login, current user, catalog, availability, booking,
  appointment details, reschedule, cancel, and released-slot checks;
- one success and conflicts for simultaneous requests to the same slot;
- unchanged users, memberships, appointments, and domain data after a Render
  restart/redeploy;
- Flutter analysis/tests and a production-signed, aligned APK with its exact
  package, version, SHA-256, and path;
- successful local Windows mode and valid Docker Compose mode.
